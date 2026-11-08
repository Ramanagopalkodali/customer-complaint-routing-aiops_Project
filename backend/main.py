"""REST inference service, independent of the frontend.

Load the selected MLflow model once at startup. Never record complaint text
in application logs. Apply the validation-selected category review thresholds.
"""
import hashlib
import json
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

import mlflow
import mlflow.sklearn
import numpy as np
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, StringConstraints

ROOT = Path(__file__).resolve().parents[1]
TEAMS = {
    "bank_account": "Bank Accounts Support",
    "credit_card": "Credit Card Support",
    "credit_reporting": "Credit Reporting Support",
    "debt_collection": "Debt Collection Support",
    "mortgage": "Mortgage Support",
}
ComplaintText = Annotated[
    str, StringConstraints(
        strict=True, strip_whitespace=True, min_length=10, max_length=10000
    )
]


class SingleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: ComplaintText


class BatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    texts: list[ComplaintText] = Field(min_length=1, max_length=100)


class Prediction(BaseModel):
    product: str
    confidence: float = Field(ge=0, le=1)
    threshold: float | None = Field(default=None, ge=0, le=1)
    recommended_team: str
    assigned_team: str
    human_review: bool
    review_reason: str | None
    model_version: str


class BatchResponse(BaseModel):
    results: list[Prediction]


class RoutingService:
    """Own model inference and policy application without HTTP dependencies."""

    def __init__(self):
        from backend.model_loader import load_bundle

        directory = Path(os.environ.get(
            "SERVING_DIR", str(ROOT / "artifacts/serving")
        ))
        self.model, self.policy = load_bundle(directory)
        if set(self.model.classes_) != set(TEAMS):
            raise ValueError("Unexpected model categories")
        self.thresholds = self.policy["thresholds"]
        self.version = self.policy["training_run_id"]

    def predict(self, texts):
        """Return recommendations; unrecognized text always requires review."""
        cleaned = [" ".join(text.split()) for text in texts]
        features = self.model.named_steps["tfidf"].transform(cleaned)
        probabilities = self.model.named_steps[
            "classifier"
        ].predict_proba(features)
        if (
            probabilities.shape != (len(texts), len(self.model.classes_))
            or not np.isfinite(probabilities).all()
            or ((probabilities < 0) | (probabilities > 1)).any()
            or not np.allclose(probabilities.sum(axis=1), 1, atol=1e-5)
        ):
            raise ValueError("Invalid model probability output")

        results = []
        for index, scores in enumerate(probabilities):
            product = str(self.model.classes_[int(scores.argmax())])
            confidence = float(scores.max())
            threshold = self.thresholds.get(product)
            if features[index].nnz == 0:
                reason = "unrecognized_text"
            elif threshold is None:
                reason = "category_requires_review"
            elif confidence < threshold:
                reason = "low_confidence"
            else:
                reason = None
            review = reason is not None
            results.append(Prediction(
                product=product,
                confidence=confidence,
                threshold=threshold,
                recommended_team=TEAMS[product],
                assigned_team="Human review" if review else TEAMS[product],
                human_review=review,
                review_reason=reason,
                model_version=self.version,
            ))
        return results


@asynccontextmanager
async def lifespan(app):
    """Load once, save the API specification and release resources on exit."""
    (ROOT / "logs").mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(ROOT / "logs/backend.log"),
        ],
    )
    app.state.service = RoutingService()
    (ROOT / "reports").mkdir(exist_ok=True)
    (ROOT / "reports/backend_openapi.json").write_text(
        json.dumps(app.openapi(), indent=2) + "\n"
    )
    logging.info("Backend ready; training run=%s", app.state.service.version)
    yield
    del app.state.service


app = FastAPI(
    title="Customer Complaint Routing API",
    version="1.0",
    lifespan=lifespan,
)


@app.exception_handler(Exception)
async def unexpected_error(request: Request, exc: Exception):
    logging.error("Request failed: %s", request.url.path,
                  exc_info=(type(exc), exc, exc.__traceback__))
    return JSONResponse(
        status_code=500, content={"detail": "Prediction service error"}
    )



def save_results(results):
    """Save prediction responses without storing submitted complaint text."""
    from datetime import datetime, timezone
    from uuid import uuid4

    request_id = uuid4().hex
    folder = ROOT / "reports" / "app_results"
    folder.mkdir(parents=True, exist_ok=True)
    record = {
        "request_id": request_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "results": [result.model_dump() for result in results],
    }
    (folder / f"{request_id}.json").write_text(
        json.dumps(record, indent=2) + "\n"
    )
    logging.info("Saved prediction response: %s; count=%s",
                 request_id, len(results))

@app.get("/healthz")
def health(request: Request):
    return {
        "status": "ok",
        "model_version": request.app.state.service.version,
    }


@app.post("/predict", response_model=Prediction)
def predict(payload: SingleRequest, request: Request):
    results = request.app.state.service.predict([payload.text])
    save_results(results)
    return results[0]


@app.post("/predict-batch", response_model=BatchResponse)
def predict_batch(payload: BatchRequest, request: Request):
    results = request.app.state.service.predict(payload.texts)
    save_results(results)
    return BatchResponse(results=results)


@app.get("/pipeline")
def pipeline():
    """Return workflow visualization and recorded execution evidence."""
    from backend.pipeline import pipeline_snapshot
    return pipeline_snapshot()
