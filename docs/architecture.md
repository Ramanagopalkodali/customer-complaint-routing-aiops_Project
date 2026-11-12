# Architecture and block explanations

## Scope and deployment boundary

The system is a local, CPU-based financial-product complaint router. Its online
path predicts a product and applies a frozen human-review policy. Its offline
path constructs chronological datasets, compares models and replays a historical
monitoring/retraining scenario. Local Docker Compose supplies six services.

## Application and observability

~~~mermaid
flowchart TD
    Agent["Support agent"] --> UI["Streamlit frontend"]
    UI -->|"Configurable REST"| API["FastAPI backend"]
    API --> Bundle["MLflow model and routing policy"]
    API --> Evidence["Saved reports and DVC status"]
    API --> Results["Responses without complaint text"]
    API -->|"Metrics"| Prom["Prometheus"]
    UI -.-> Probe["Blackbox health probes"]
    API -.-> Probe
    Probe --> Prom
    VM["Ubuntu VM"] --> Node["node-exporter"]
    Node --> Prom
    Prom --> Graf["Grafana"]
~~~

| Block | Responsibility and interface |
|---|---|
| Support agent | Enters one complaint or selects a CSV; decides the final destination for review cases. |
| Streamlit | Validates user input, calls REST, formats product/team/confidence results and downloads batch results. It never imports or loads the model. |
| FastAPI | Validates JSON using Pydantic, calls `RoutingService`, saves response records, exports metrics and serves the pipeline snapshot. |
| Portable serving bundle | Contains the MLflow sklearn package, routing policy and SHA-256 file manifest. Loaded once per backend process. |
| Evidence adapter | Reads saved JSON/XML/log evidence and the real DVC configuration. Its console is read-only. |
| Response store | Unique request-response JSON under ignored `reports/app_results/`; excludes submitted complaint text. |
| Prometheus | Scrapes every 10 seconds, evaluates six alert rules, and stores local time-series data. |
| Blackbox exporter | Probes the frontend/backend HTTP health endpoints from the Compose network. |
| node-exporter | Exposes VM resource metrics. It is infrastructure instrumentation, separate from model metrics. |
| Grafana | Uses provisioned Prometheus datasource `complaint-prom` and refreshes the dashboard every 5 seconds. |

Ports published on VM loopback: API 8000, frontend 8501, Prometheus 9090,
Grafana 3000. Exporters use internal ports 9115 and 9100. The optional MLflow
tracking UI is a separate operator process on 5000, not a Compose service.

## Offline data and model lifecycle

~~~mermaid
flowchart TD
    ZIP["Three pinned CFPB archives"] --> Ray["Ray ingestion: two CPU workers"]
    Ray --> Splits["Chronological deduplicated CSVs"]
    Splits --> Train["TF-IDF model comparison"]
    Train --> Policy["Validation-selected routing thresholds"]
    Policy --> Original["Original portable serving bundle"]
    Splits --> Monitor["November monitoring"]
    Original --> Monitor
    Monitor --> Candidate["Triggered or explicit rehearsal training"]
    Candidate --> Acceptance["Separate November acceptance"]
    Acceptance -->|"Pass every gate"| Package["Package selected candidate"]
    Acceptance -->|"Reject"| Retain["Retain original"]
    Package --> Deploy["Deployment and rollback drill"]
    Deploy --> Final["Reserved December evaluation"]
~~~

The arrow from monitoring to candidate is conditional. In the recorded batch
there was no trigger; an explicitly requested rehearsal trained the candidate.
That distinction is preserved in the reports.

Git versions source, configurations, reports and ordinary screenshots. DVC versions working datasets, training assets,
serving bundles and stage dependencies. MLflow records run parameters, metrics,
models and provenance in local SQLite/artifact storage. These have distinct
roles; a training run ID is not a Git commit or a model registry alias.

## Storage and handoff

| Location | Role |
|---|---|
| `data/raw/`, `data/processed/` | Pinned input ZIPs and four processed datasets; DVC working assets |
| `artifacts/training/`, `artifacts/policy.json` | Original model comparison outputs and selected policy |
| `artifacts/serving/` | Validated original model for rollback and Docker build |
| `artifacts/lifecycle/` | Drift reference, candidate model/policy and portable candidate bundle |
| `mlflow.db`, `mlruns/` | Local tracking history; separately backed up |
| `reports/` | Versioned results, tests, predictions, diagrams and provenance |
| `logs/reproduction/` | Two fixed replay transcripts retained in Git |
| Local DVC store | Recovery objects outside the checkout; same-VM until copied externally |

The README restores canonical DVC assets from the separately supplied local
store before Docker builds. Git alone does not include the model/data bytes.
The existing backend loader verifies the bundle payload before deserialising
the trusted package. Startup does not require the original tracking database.

## Trust and failure boundaries

Frontend/backend communication uses configurable HTTP REST on the local network.
Manifest checks detect changed payload bytes; they provide integrity checks for
trusted project packages, not encryption or signatures against an attacker.
The backend runs with the host user's UID/GID, and public ports bind to loopback.
The metrics contain bounded labels rather than complaint text/request IDs.

Input failures return 422; inference failures return a generic 500 and are logged.
Missing/corrupt serving assets prevent startup. Failed stage commands stop the
reproduction controller. Failed candidate acceptance retains the original;
the deployment drill attempts original-model recovery when its own checks fail.
Failures in later evaluation or observability checks do not universally trigger
an automatic model rollback. See [deployment](deployment.md).
