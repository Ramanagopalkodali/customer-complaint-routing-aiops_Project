# Low-level design

The frontend and backend are independent processes. The frontend uses a
configurable backend REST URL and does not import or load the model.

## Current backend API

GET /healthz
- Returns 200 with status and model_version after successful startup.
- Failed model or policy loading prevents application startup.

POST /predict
- JSON input: {"text": "Complaint narrative"}
- Text: string, 10–10,000 characters after trimming surrounding whitespace.
- Unknown input fields and invalid text produce HTTP 422.

POST /predict-batch
- JSON input: {"texts": ["Complaint narrative", "..."]}
- Accepts 1–100 complaints, each subject to the same text rules.
- Invalid input rejects the entire batch with HTTP 422.
- Output: {"results": [...]} preserving input order.

Prediction fields:
- product: predicted category
- confidence: estimated probability, between 0 and 1
- threshold: frozen threshold for the predicted category
- recommended_team: team corresponding to the predicted product
- assigned_team: recommended team, or Human review
- human_review: whether manual review is required
- review_reason: low_confidence, category_requires_review,
  unrecognized_text, or null
- model_version: training MLflow run ID

Unexpected inference failures return HTTP 500 with a generic error message.
Detailed errors go to logs/backend.log without logging complaint text.

The portable MLflow model loads once at startup. Bundle file hashes,
policy provenance and manifest identity are checked. Text with no recognized vocabulary requires review.
A recognized vocabulary does not prove a complaint belongs to the supported
domain; confidence and routing precision are not guarantees.

The backend saves its OpenAPI specification to reports/backend_openapi.json.

## Pipeline endpoint

GET /pipeline
- No request body.
- Returns HTTP 200 with a JSON evidence snapshot.
- generated_at: snapshot timestamp.
- workspace_status: up_to_date, changes_detected or unavailable.
- workspace_changes: DVC change details, or null if unavailable.
- stages: pipeline stage names.
- diagram_png_base64: PNG diagram encoded as base64.
- ingestion: saved ingestion counts, splits and throughput.
- models and selected_model: saved validation comparison.
- test: saved held-out evaluation.
- tests: saved XML report summaries.
- recorded_failures: available failure entries from pipeline logs.
- missing_logs: names of unavailable pipeline logs.
- note: explanation that evidence is saved rather than live task progress.

The endpoint runs a fixed, read-only DVC status command with a timeout.
It does not accept shell commands or start training.
Unexpected snapshot failures return HTTP 500.
