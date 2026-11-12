# Low-level design and I/O specification

## Components and configuration

FastAPI uses `RoutingService`, Pydantic schemas and instrumentation from
`backend/metrics.py`. `backend/model_loader.py` verifies the portable manifest
before loading sklearn through MLflow. `backend/pipeline.py` reads DVC/evidence.
The Streamlit UI communicates through `requests` only.

| Variable | Meaning/default |
|---|---|
| `API_BASE_URL` | Frontend backend URL; standalone default `http://127.0.0.1:8000`; Compose uses `http://backend:8000` |
| `SERVING_DIR` | Model bundle inside backend; default project `artifacts/serving`; Compose `/app/artifacts/serving` |
| `PIPELINE_ROOT` | Evidence/DVC root; project root by default, `/workspace/project` in Compose |
| `SERVING_BUNDLE_PATH` | Host bind source selected in `compose.override.yaml`; defaults to original `./artifacts/serving` |
| `LOCAL_UID` / `LOCAL_GID` | Application container identity matching host directory ownership |
| `GRAFANA_ADMIN_PASSWORD` | Required private Compose value; set in ignored `.env` using README commands |
| `PYTHON_BASE` | Python Docker base-image reference; digest supplied in `.env.example` |

Changing the host bundle setting requires backend recreation; there is no
in-process hot reload. The Docker build also needs the original serving bundle
because the backend Dockerfile copies it before the runtime bind mount is applied.

## API endpoint summary

| Method/path | Request | Success response | Failure |
|---|---|---|---|
| `GET /healthz` | None | 200, status and loaded training run ID | Startup failure prevents readiness |
| `POST /predict` | JSON `{"text": "..."}` | 200, one Prediction | 422 validation; generic 500 unexpected error |
| `POST /predict-batch` | JSON `{"texts": ["...", "..."]}` | 200, `{"results": [...]}` in input order | Any invalid item rejects whole batch with 422 |
| `GET /pipeline` | None | 200, evidence/DVC snapshot | 500 if snapshot assembly fails |
| `GET /metrics` | None | 200, Prometheus exposition | Exporter failure may produce 500 |
| `GET /docs` | None | Interactive API documentation | FastAPI-provided |
| `GET /openapi.json` | None | Generated OpenAPI schema | FastAPI-provided |

`/metrics` is deliberately excluded from the OpenAPI schema. A CSV upload is
parsed in the frontend and converted to JSON for `/predict-batch`; there is no
backend CSV/multipart upload endpoint.

## Prediction request validation

`SingleRequest.text` is a strict string, trimmed at its outer whitespace, with
10–10,000 characters. Numeric/null/missing values are invalid; unknown object
fields are forbidden. Internal whitespace is subsequently collapsed for model
inference. The character validation is performed before that internal collapse.

`BatchRequest.texts` has 1–100 items, each using the same text constraints.
Unexpected request properties are forbidden. API text/count bounds are distinct
from the frontend's 1 MiB CSV limit; a general HTTP request-byte limit is not
implemented here.

~~~bash
curl -fsS http://127.0.0.1:8000/predict \
  -H 'Content-Type: application/json' \
  -d '{"text":"My credit card was charged twice for the same purchase."}'
~~~

## Prediction response

| Field | Type and semantics |
|---|---|
| `product` | One of `bank_account`, `credit_card`, `credit_reporting`, `debt_collection`, `mortgage` |
| `confidence` | Finite estimated probability between 0 and 1 for the argmax class |
| `threshold` | Selected threshold for that predicted category; float 0–1 or null |
| `recommended_team` | Static product-to-team mapping below |
| `assigned_team` | Recommended team when accepted; otherwise `Human review` |
| `human_review` | Boolean review decision |
| `review_reason` | `unrecognized_text`, `category_requires_review`, `low_confidence`, or null |
| `model_version` | MLflow **training run ID**; not a numeric registry version |

| Product | Recommended team |
|---|---|
| `bank_account` | Bank Accounts Support |
| `credit_card` | Credit Card Support |
| `credit_reporting` | Credit Reporting Support |
| `debt_collection` | Debt Collection Support |
| `mortgage` | Mortgage Support |

Decision order: a zero-feature TF-IDF row requires `unrecognized_text` review;
a missing/null category threshold requires `category_requires_review`; otherwise
confidence below the threshold requires `low_confidence`. Equality is accepted.
Automatic routing requires recognized vocabulary and a usable threshold.

The probability matrix must have shape `(batch_size, number_of_classes)`,
finite values in [0,1], and each row must sum approximately to one
(`atol=1e-5`). The loaded model's category set must match the five configured
teams. These conditions are checked before returning results.

The JSON below is an actual saved synthetic response from the latest candidate
redeployment, in `reports/lifecycle/deployment_verification.json`:

~~~json
{
  "product": "credit_card",
  "confidence": 0.8659684513643687,
  "threshold": 0.89,
  "recommended_team": "Credit Card Support",
  "assigned_team": "Human review",
  "human_review": true,
  "review_reason": "low_confidence",
  "model_version": "caa8bd53da5f4fb1871725b08a80ec70"
}
~~~

422 responses use FastAPI/Pydantic's `detail` validation array. Unexpected
exceptions return `{"detail": "Prediction service error"}` with HTTP 500 and a
server-side stack trace. The application intentionally avoids logging submitted
complaint text; responses and request IDs are persisted without that text.

## Frontend CSV I/O

Input: UTF-8/UTF-8-BOM CSV, exactly one column `text`, 1–100 parsed records,
maximum 1,048,576 bytes. Each text is outer-trimmed and length-checked.
Wrong columns, malformed encoding/CSV, empty data, invalid lengths or excess
records are shown as user errors. CSV row references are logical record indices
including the header, not physical line positions for quoted multiline records.

Output columns: `csv_row`, `product`, `threshold`, `recommended_team`,
`assigned_team`, `human_review`, `review_reason`, `model_version`,
`confidence_percent`. Product names are human-readable and confidence is
multiplied by 100 and rounded to two decimals. Input text is not included.

## Pipeline snapshot schema

The endpoint is read-only and takes no job names or shell commands.

| Field | Type/meaning |
|---|---|
| `active_model_version` | Current backend training run ID |
| `generated_at` | ISO UTC snapshot timestamp |
| `workspace_status` | `up_to_date`, `changes_detected` or `unavailable` |
| `workspace_changes` | DVC JSON change mapping or null |
| `stages` | Stage-name list including synthetic source-data node |
| `diagram_png_base64` | PNG encoded as base64, constructed from DVC dependencies |
| `ingestion` | Saved source/split counts and throughput, or null |
| `models` / `selected_model` | Saved original comparison and selected model type |
| `test` | Historical original-model October evaluation, or null |
| `lifecycle` | Monitoring, acceptance, deployment, final and runner records |
| `final_evaluation_matches_active_model` | Whether saved December run ID equals current loaded run |
| `tests` | XML-derived report status/count records |
| `recorded_failures` | Up to 20 available error/failure log entries |
| `missing_logs` | Missing baseline log filenames |
| `note` | Explanation of saved evidence versus live progress |

The DVC status subprocess has a 15-second timeout. The frontend pipeline request
uses a 30-second timeout and a 15-second Streamlit cache, cleared by Refresh.
Missing/malformed optional JSON becomes null. Invalid XML/YAML, missing tools or
other assembly failures can still cause the endpoint to return a generic 500;
per-field error isolation is incomplete.

## Filesystem I/O

| Producer | Input | Output |
|---|---|---|
| `src/ingest.py` | Three raw ZIPs, each one UTF-8 CSV | `data/processed/{train,validation,test,future}.csv` and ingestion summary |
| `src/train.py` | Train/validation CSVs | Two joblib pipelines, validation predictions/plots and MLflow runs |
| `src/select_threshold.py` | Validation predictions and chosen model | Policy, per-category threshold curves and routing tables |
| `src/evaluate.py` | Frozen original model/policy and October CSV | Test predictions, metrics, routing tables and confusion matrix |
| `src/export_model.py` | Original joblib/policy | Portable original bundle and equivalence report |
| Historical lifecycle modules | Frozen periods/config, original bundle and future CSV | Monitoring, candidate, acceptance, package, deployment and December records |
| `save_results` | Prediction objects | `reports/app_results/<request_id>.json` with UTC time and results |

Raw CSV columns required by ingestion: `Complaint ID`, `Date received`,
`Product` and `Consumer complaint narrative`. Processed columns:
`complaint_id`, `date_received` (ISO date), `text` and `label`.
Dates/IDs are audit fields, labels are targets, and only text is a model feature.

A serving bundle contains `manifest.json`, `policy.json` and `model/`.
The manifest maps relative payload paths to SHA-256 values, records the training
run/model type and original source-model hash. The loader rejects payload paths
outside the bundle. The policy uses `mode=per_predicted_category`, category
thresholds, training identity and source hash. Manifest/policy identities and
payload bytes are validated before MLflow loads the local sklearn package.

## Instrumentation contract

| Metric family | Labels / meaning |
|---|---|
| `complaint_http_requests_total` | method, bounded route, status; excludes scrapes |
| `complaint_http_duration_seconds` | route; response-header preparation latency histogram |
| `complaint_predictions_total` | product, automatic/human-review decision |
| `complaint_prediction_confidence` | product; estimated-confidence histogram |
| `complaint_request_items` | Successful request batch-size histogram |
| `complaint_model_loaded` | training_run_id gauge |
| `complaint_saved_report_*` | Saved ingestion/October evidence availability and timestamp |
| `complaint_ingestion_*` / `complaint_dataset_rows` | Last saved ingestion throughput/duration and split sizes |
| `complaint_reference_test_macro_f1` | Historical October F1 labelled by original run ID |
| `complaint_lifecycle_*` | Historical monitoring, acceptance and December metrics with run identity |

The default Python client also exposes process/Python metrics. Node-exporter
supplies VM metrics; blackbox `probe_success` supplies application health.
No complaint text, complaint ID or request UUID is used as a metric label.
The latency histogram is not a client/network end-to-end latency measurement.

The host root policy/original bundle remain the original model. The active
candidate policy resides in the candidate serving folder; the container bind
mount presents that folder at the common internal serving path.

The console's saved-test list contains selected current/historical subsets;
the full 77-case report is available in the repository but is not currently a
separate row in that UI table. Report-age gauges use filesystem modification
time, which can change on checkout/copy; use embedded run timestamps and IDs
for experiment chronology.
