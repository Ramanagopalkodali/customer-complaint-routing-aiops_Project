# End-to-end workflow and file responsibilities

This guide follows the actual repository from raw complaint data to the running
application. It distinguishes **starting the existing model**, **testing it**
and **deliberately rebuilding it**. Executable commands are collected in the
[root README](../README.md); reading or applying these documents runs no stages.

## Three operating paths

| Goal | Entry point | What happens |
|---|---|---|
| Use the existing application | Restore DVC assets, prepare `.env`, `docker compose up` | Load the existing selected package and serve predictions; no model fit |
| Check the implementation | `scripts/run_final_checks.py`, `scripts/smoke_containers.py` | Run the suite and real HTTP smoke; no retraining or December reevaluation |
| Replay the whole project | `scripts/reproduce_baseline.py`, identity checkpoint, `scripts/reproduce_lifecycle.py` | Re-ingest, train, gate, package, deploy and evaluate, replacing fixed reports |

## Data-to-model path

~~~mermaid
flowchart TD
    Raw["Pinned CFPB ZIPs"] --> Ingest["Ray cleaning and chronological deduplication"]
    Ingest --> Train["April–July training"]
    Ingest --> Validation["August–September validation"]
    Ingest --> Test["October test"]
    Ingest --> Future["November–December future"]
    Train --> Compare["Fit and compare two TF-IDF classifiers"]
    Validation --> Compare
    Compare --> Thresholds["Select category thresholds on validation"]
    Thresholds --> Original["Export original serving package"]
    Test --> October["Evaluate frozen original"]
    Thresholds --> October
    Future --> Lifecycle["Separate historical lifecycle"]
    Original --> Lifecycle
~~~

The October test does not choose the original model or its thresholds. November
has separate candidate training, threshold-selection and acceptance windows.
December is reserved until the candidate decision and deployment are frozen.
See [model development](model_development.md) for exact periods and counts.

## Baseline stages

`scripts/reproduce_baseline.py` verifies source cleanliness, the pre-rebuild
snapshot and all three raw archive hashes; checks dependencies/Compose; stops
services without deleting volumes; then force-runs seven stages sequentially.
It retains MLflow history and writes one current baseline transcript/report.

| Stage | File that does the work | Main input | Main output/evidence |
|---|---|---|---|
| Raw acquisition/pinning | `config/raw_sources.json`, `data/raw.dvc` | Three preserved CFPB ZIP exports | Expected source SHA-256 values and DVC object reference |
| `ingest` | [src/ingest.py](../src/ingest.py) | Raw ZIPs | Four cleaned/deduplicated `data/processed/*.csv`; `reports/ingestion_summary.json` |
| `validate_data` | [tests/test_ingest.py](../tests/test_ingest.py) | Ingestion functions and processed data dependencies | `reports/ingestion_tests.xml` |
| `train` | [src/train.py](../src/train.py) | Train and validation CSVs | Two tracked models, `artifacts/training/`, `reports/training/` comparison/predictions |
| `select_threshold` | [src/select_threshold.py](../src/select_threshold.py) | Validation predictions and training results | `artifacts/policy.json`, `reports/threshold/` operating-point outputs |
| `validate_threshold` | [tests/test_threshold.py](../tests/test_threshold.py) | Threshold functions/policy | `reports/threshold_tests.xml` |
| `evaluate` | [src/evaluate.py](../src/evaluate.py) | Frozen original model/policy and October CSV | `reports/test/` predictions, metrics and confusion matrix |
| `export_model` | [src/export_model.py](../src/export_model.py) | Selected original model and policy | `artifacts/serving/` MLflow package/manifest/policy; `reports/export_model.json` |

Ray processes archive-reading/cleaning tasks using two CPU workers. The driver
then deduplicates IDs and normalised text forward in time. Model fitting uses
the earlier training period; validation is used for comparison and thresholds.

The current original training run is `376d762990d44d59af5080825e9be19a`.
A real replay creates a different run ID. The README's checkpoint binds that
new original ID into `config/lifecycle.json` before the lifecycle phase, while
preserving the dates and acceptance thresholds. Do not copy a historical UUID
into a newly trained model's configuration.

## Historical monitoring-to-deployment path

~~~mermaid
flowchart TD
    Monitor["Score November 1–15"] --> Trigger{"Any frozen trigger?"}
    Trigger -->|"No"| Keep["Retain original"]
    Trigger -->|"Yes"| Train["Train candidate"]
    Demo["Explicit historical demonstration"] --> Train
    Train --> Tune["Tune thresholds: November 16–22"]
    Tune --> Accept{"Acceptance: November 23–30"}
    Accept -->|"Fail"| Keep
    Accept -->|"Pass all six"| Package["Package and verify candidate"]
    Package --> Deploy["Candidate → original → candidate drill"]
    Deploy --> Final["December final evaluation"]
    Final --> Verify["77-case suite and live checks"]
~~~

| Responsibility | File | Main current evidence |
|---|---|---|
| Distribution and labelled-performance monitoring | [src/monitor_lifecycle.py](../src/monitor_lifecycle.py) | `reports/lifecycle/monitoring.json`, `artifacts/lifecycle/drift_reference.json` |
| Trigger-controlled sequence | [src/run_lifecycle.py](../src/run_lifecycle.py) | `reports/lifecycle/runner.json`; unit-tested no-trigger/rejection/failure branches |
| Candidate fit and separate threshold selection | [src/retrain_candidate.py](../src/retrain_candidate.py) | `artifacts/lifecycle/candidate/model.joblib`, `policy.json`; `reports/lifecycle/candidate/` |
| Same-period original/candidate comparison and six acceptance gates | [src/accept_candidate.py](../src/accept_candidate.py) | `reports/lifecycle/acceptance/decision.json`, two prediction CSVs |
| Portable candidate packaging and equivalence | [src/package_candidate.py](../src/package_candidate.py) | `artifacts/lifecycle/candidate/serving/`; `reports/lifecycle/candidate_packaging.json` |
| Actual Docker switching, HTTP comparison and rollback drill | [scripts/verify_lifecycle_deployment.py](../scripts/verify_lifecycle_deployment.py) | `reports/lifecycle/deployment_verification.json`; selected `.env` bind path |
| Reserved December measurement | [src/evaluate_lifecycle_final.py](../src/evaluate_lifecycle_final.py) | `reports/lifecycle/final/summary.json`, predictions, class report and confusion matrix |
| Complete historical replay, checks, timings and diagrams | [scripts/reproduce_lifecycle.py](../scripts/reproduce_lifecycle.py) | `reports/reproduction/lifecycle.json`, `logs/reproduction/lifecycle.log`, pipeline diagrams/live check |

The actual monitoring batch did **not** trigger retraining. The default controller
recorded `no_trigger`; the explicit demonstration path subsequently produced the
accepted candidate `caa8bd53da5f4fb1871725b08a80ec70`. These outcomes describe
different steps and are consistent. The wrapper records that distinction.

The lifecycle wrapper checks the newly bound baseline/configuration and performs
the demonstration path only as explicitly defined. Rejected candidates retain
the original. Deployment and December stages are frozen against ordinary DVC
reproduction; the wrapper executes them deliberately and records their outputs.
A bare `dvc repro --force` is not the documented full-replay procedure.

## Online prediction path

1. [frontend/app.py](../frontend/app.py) validates a single text or UTF-8 CSV,
   sends JSON through the configurable REST URL, and renders/downloads results.
2. [backend/main.py](../backend/main.py) owns Pydantic request/response models,
   `RoutingService`, prediction routes, review decisions, errors and response
   records. It loads the model once during application startup.
3. [backend/model_loader.py](../backend/model_loader.py) checks package/policy
   identities and manifest hashes before loading the trusted MLflow model.
4. The model predicts five category probabilities. Argmax gives the product
   and confidence; the category policy decides automatic routing or review.
5. The API returns product, confidence, threshold, recommended/assigned team,
   review flag/reason and model version. Durable response records exclude text.

The original remains at host `artifacts/serving/`. The selected candidate is at
host `artifacts/lifecycle/candidate/serving/`. `compose.override.yaml` binds the
chosen folder to the common internal `/app/artifacts/serving` path. The build
still needs the original bundle because the Dockerfile copies it into the image.
Runtime `/healthz` establishes what is actually loaded.

## Console, metrics and infrastructure files

| File | What it does |
|---|---|
| [backend/pipeline.py](../backend/pipeline.py) | Reads real DVC dependencies; draws the DAG; aggregates saved JSON/XML/log evidence; runs read-only DVC status |
| [backend/metrics.py](../backend/metrics.py) | Request/inference/routing/confidence metrics and saved pipeline evidence collector |
| [backend/lifecycle_metrics.py](../backend/lifecycle_metrics.py) | Exposes labelled historical monitoring/acceptance/December evidence without claiming live delayed-label scoring |
| [backend/__init__.py](../backend/__init__.py) | Package marker; not an executable stage |
| [monitoring/prometheus.yml](../monitoring/prometheus.yml) | Scrape targets, probe relabelling, intervals and alert-rule inclusion |
| [monitoring/blackbox.yml](../monitoring/blackbox.yml) | HTTP probe module configuration |
| [monitoring/alerts.yml](../monitoring/alerts.yml) | Six local Prometheus alert conditions and waiting periods |
| [monitoring/grafana/dashboards/complaint-routing.json](../monitoring/grafana/dashboards/complaint-routing.json) | Provisioned application, VM and labelled historical lifecycle panels |
| [monitoring/grafana/provisioning/datasources/prometheus.yml](../monitoring/grafana/provisioning/datasources/prometheus.yml) | Prometheus datasource, UID `complaint-prom` |
| [monitoring/grafana/provisioning/dashboards/default.yml](../monitoring/grafana/provisioning/dashboards/default.yml) | Dashboard-file provisioning |
| [Dockerfile](../Dockerfile) | Shared pinned dependency layer and separate backend/frontend image targets |
| [compose.yaml](../compose.yaml), [compose.override.yaml](../compose.override.yaml) | Six services, local ports, volumes, health checks and selected serving bind |
| [.env.example](../.env.example) | Non-secret base-image/UID template; actual password and bundle choice go in ignored `.env` |
| [requirements.lock.txt](../requirements.lock.txt), [requirements.txt](../requirements.txt) | Locked packages and top-level dependency declaration |
| [dvc.yaml](../dvc.yaml), [dvc.lock](../dvc.lock) | Stage graph/commands plus recorded dependency/output hashes |
| [.dvcignore](../.dvcignore) | Excludes irrelevant runtime paths from DVC scans |
| [config/lifecycle.json](../config/lifecycle.json) | Frozen original identity, monitoring windows, trigger and acceptance settings |
| [config/raw_sources.json](../config/raw_sources.json) | Preserved input source and archive hashes |
| [MLproject](../MLproject) | Docker-backed backend-test entry point |

The Refresh button fetches evidence/status. It does not execute training.
This delivery leaves that console unchanged. Pipeline `workspace_status` may
be `unavailable` when its DVC subprocess fails/times out; diagnose it separately
from the model-serving health response.

## Test, recovery and evidence files

| File/group | Responsibility |
|---|---|
| [scripts/run_final_checks.py](../scripts/run_final_checks.py) | Runs the full suite against the candidate matched to final evaluation; writes XML/summary/log |
| [scripts/smoke_containers.py](../scripts/smoke_containers.py) | Valid/batch/invalid/OOV HTTP checks plus pipeline and frontend readiness |
| [scripts/test_mlproject.sh](../scripts/test_mlproject.sh) | Runs the original-bundle backend module through Docker-backed MLproject |
| [scripts/verify_artifact_recovery.py](../scripts/verify_artifact_recovery.py) | Creates a separate checkout/empty cache, pulls DVC assets and compares both restored models |
| [scripts/verify_recovered_deployment.py](../scripts/verify_recovered_deployment.py) | Builds recovered images, smoke-tests ports 8002/8502 and removes its containers |
| Nine [tests/](../tests) modules | Unit/integration cases; all 77 IDs and purposes are in [test_cases.md](test_cases.md) |
| [reports/](../reports) | Machine-readable numerical evidence; current records are indexed in [rubric_file_map.md](rubric_file_map.md) |
| [logs/reproduction/](../logs/reproduction) | Two committed current replay transcripts; other runtime logs are ignored |
| [evidence/](../evidence) | Actual screenshots; [index](../evidence/README.md) distinguishes historical/current proof |

## What is overwritten and what is retained

Stage reports, numerical CSVs, plots and the two replay transcripts use fixed
paths and are replaced by the corresponding run. MLflow intentionally retains
run history. Runtime request UUID response files can accumulate in ignored
`reports/app_results/`. DVC cache/remote objects and retained recovery checkouts
are separate from the visible source tree. Browser screenshots are manual;
replace an existing image only after capturing the new screen.

Changing documentation requires no pipeline replay. A frontend redesign normally
requires rebuilding/recreating the frontend service and checking UI behaviour;
it does not by itself require model training. Update endpoint consumers and
related documentation if any request or response contract is changed.
