# Rubric-to-file and evidence map

The evaluation guideline assigns **25 marks**: Demonstration 5, Software
Engineering 5, AIOps 10 and Viva 5. This document tells an evaluator where to
look and what to demonstrate. [rubric_compliance.md](rubric_compliance.md)
answers each question individually; it does not guarantee a score.

## Demonstration — 5 marks

| Subsection | Main implementation | Documentation/proof | Suggested demonstration |
|---|---|---|---|
| Frontend UI/UX — 3 | [frontend/app.py](../frontend/app.py); HTTP contracts in [backend/main.py](../backend/main.py) | [User manual](user_manual.md), [manual cases](test_plan_and_report.md#manual-test-plan), `evidence/app_single.png`, `app_batch.png`, `app_review.png`, `app_invalid_input.png` | Single complaint, review-required example, sample CSV and download, invalid input |
| ML pipeline visualisation — 2 | [backend/pipeline.py](../backend/pipeline.py), Pipeline tab in [frontend/app.py](../frontend/app.py), [dvc.yaml](../dvc.yaml) | [Workflow](workflow_and_files.md), [generated DAG](../reports/reproduction/pipeline_dag.png), [live check](../reports/final/pipeline_live_check.json), `evidence/stage8/pipeline_lifecycle.png` | Refresh console, show ingestion counts/speed, model comparison, current model and saved outcomes |

The console is interactive for evidence refresh; pipeline execution is through
CLI wrappers. It has no job start/stop controls. The rubric does not explicitly
specify those controls. Explain the implemented boundary rather than asserting
that Refresh executes a stage. Current screenshot shows DVC status unavailable;
diagnose host/container status separately if asked about freshness.

After the planned UI redesign, recapture frontend screenshots. Existing ones
remain historical examples until replaced; their layouts need not match a new UI.

## Software Engineering — 5 marks

| Subsection | Main files | Documents and evidence |
|---|---|---|
| Design principles — 2 | [backend/main.py](../backend/main.py), [model_loader.py](../backend/model_loader.py), [frontend/app.py](../frontend/app.py), [compose.yaml](../compose.yaml) | [Architecture](architecture.md), [HLD](high_level_design.md), [LLD](low_level_design.md); separate services/configurable REST; OO service/Pydantic plus functional numerical code |
| Implementation — 2 | `src/*.py`, `backend/*.py`, `frontend/app.py`, `scripts/*.py` | Module/function docstrings, validation/error handling, [baseline log](../logs/reproduction/baseline.log), [lifecycle log](../logs/reproduction/lifecycle.log), response/error contracts in LLD |
| Testing — 1 | Nine modules under [tests/](../tests), [run_final_checks.py](../scripts/run_final_checks.py), [smoke_containers.py](../scripts/smoke_containers.py) | [Test plan/report](test_plan_and_report.md), [77-case catalogue](test_cases.md), [full XML](../reports/final/full_tests.xml), [summary](../reports/final/tests_summary.json), [HTTP smoke](../reports/container_smoke.json) |

The latest full suite has **77 passed, 0 failed, 0 errors, 0 skipped** for
candidate `caa8bd53da5f4fb1871725b08a80ec70`. This combines unit and integration
cases; do not describe every case as an isolated unit test or add older subset
counts to this total. Syntax checks are not a formatter/linter/coverage report.

## AIOps — 10 marks

| Subsection | Main implementation/configuration | Machine evidence and explanation |
|---|---|---|
| Data engineering — 2 | [src/ingest.py](../src/ingest.py), [tests/test_ingest.py](../tests/test_ingest.py), [config/raw_sources.json](../config/raw_sources.json), [data/raw.dvc](../data/raw.dvc) | [Ingestion summary](../reports/ingestion_summary.json), [ingestion tests](../reports/ingestion_tests.xml), [baseline replay](../reports/reproduction/baseline.json); 2 Ray workers, 2,255,475 input rows, 23.411 s, 96,341.28 input rows/s |
| Source control / CI — 2 | [dvc.yaml](../dvc.yaml), [dvc.lock](../dvc.lock), [reproduce_baseline.py](../scripts/reproduce_baseline.py), [reproduce_lifecycle.py](../scripts/reproduce_lifecycle.py), Git configuration | [DAG](../reports/reproduction/pipeline_dag.mmd), [DVC status](../reports/lifecycle/dvc_status.json), [CI subset XML](../reports/lifecycle/ci_tests.xml), replay logs and source commits; local test-gated reproduction, not hosted push-triggered CI |
| Experiment tracking — 2 | [src/train.py](../src/train.py), [src/retrain_candidate.py](../src/retrain_candidate.py), [src/monitor_lifecycle.py](../src/monitor_lifecycle.py), [src/evaluate_lifecycle_final.py](../src/evaluate_lifecycle_final.py) | [Comparison](../reports/training/comparison.json), [candidate summary](../reports/lifecycle/candidate/training_summary.json), [final summary](../reports/lifecycle/final/summary.json), local `mlflow.db` and `mlruns/`; open MLflow UI on the training VM |
| Instrumentation — 2 | [backend/metrics.py](../backend/metrics.py), [backend/lifecycle_metrics.py](../backend/lifecycle_metrics.py), [Prometheus](../monitoring/prometheus.yml), [alerts](../monitoring/alerts.yml), [dashboard](../monitoring/grafana/dashboards/complaint-routing.json) | [Live check](../reports/final/pipeline_live_check.json), [metrics snapshot](../reports/reproduction/backend_metrics.prom), `evidence/prometheus_targets.png`, `alerts_firing.png`, `stage7/lifecycle_dashboard.png`; six target scrapes and two probes recorded healthy |
| Packaging — 2 | [src/export_model.py](../src/export_model.py), [src/package_candidate.py](../src/package_candidate.py), [backend/model_loader.py](../backend/model_loader.py), [MLproject](../MLproject), [Dockerfile](../Dockerfile), both Compose files | [Original export](../reports/export_model.json), [candidate package](../reports/lifecycle/candidate_packaging.json), [deployment/rollback](../reports/lifecycle/deployment_verification.json), [MLproject XML](../reports/mlproject_backend_tests.xml), [container smoke](../reports/container_smoke.json) |

Git versions source/reports/ordinary pictures; DVC versions excluded large assets.
The rubric permits Git/Git LFS and/or DVC. The submitted proposal named LFS, but
active LFS is absent: disclose the tool-specific difference rather than adding
it solely to change the documentation. Custom FastAPI serves MLflow packages;
literal standalone MLflow Serve is not evidenced. The packaging document gives
an optional additional check without claiming it already passed.

Current MLproject and clean-checkout recovery evidence need refresh: the supplied
MLproject XML has an older 16-case backend subset, while the module now has 18;
recovery records reference earlier model IDs. MLflow history is outside Git.
These distinctions are recorded in [audit findings](audit_findings.md).

## Additional proposal lifecycle proof

The proposal's retraining/replacement promises are demonstrated across several
rubric subsections rather than receiving a separate numbered mark allocation.

| Promise/operation | Implementation | Proof |
|---|---|---|
| Historical incoming-batch monitoring | [monitor_lifecycle.py](../src/monitor_lifecycle.py) | [monitoring.json](../reports/lifecycle/monitoring.json); actual batch had no trigger |
| Conditional automation | [run_lifecycle.py](../src/run_lifecycle.py), [runner tests](../tests/test_lifecycle_runner.py) | [runner.json](../reports/lifecycle/runner.json), full suite; no-trigger/rejection/failure checks |
| Candidate retraining | [retrain_candidate.py](../src/retrain_candidate.py) | [training summary](../reports/lifecycle/candidate/training_summary.json); explicit demonstration, not an actual drift event |
| Replace only after acceptance | [accept_candidate.py](../src/accept_candidate.py), [acceptance tests](../tests/test_candidate_acceptance.py) | [decision.json](../reports/lifecycle/acceptance/decision.json); all six gates passed |
| Deployment and retained rollback package | [verify_lifecycle_deployment.py](../scripts/verify_lifecycle_deployment.py) | [deployment verification](../reports/lifecycle/deployment_verification.json); candidate→original→candidate PASS |
| Final evaluation after selection | [evaluate_lifecycle_final.py](../src/evaluate_lifecycle_final.py) | [December summary](../reports/lifecycle/final/summary.json); no final-data tuning |

The complete [proposal map](proposal_compliance.md) and
[development-guideline assessment](development_guidelines.md) address the other
submitted commitments and broad framework recommendations.

## Viva — 5 marks

| Topic | Preparation source |
|---|---|
| Entire data-to-application flow | [Workflow/file guide](workflow_and_files.md), architecture and README |
| Why these models, splits and metrics | [HLD](high_level_design.md), [model development](model_development.md) |
| MLOps tool roles and their boundaries | Architecture, deployment and this map |
| Why no trigger still led to a candidate demonstration | Workflow, proposal map, monitoring/training reports |
| Confidence, human review and allowed acceptance trade-offs | LLD, test criteria, November comparison and December results |
| Questions from course Assignments 1–10 | Review those actual assignments separately; repository evidence cannot establish viva preparation |

## Practical evidence rule

Use current JSON/XML/CSV and model identities as numerical proof. Screenshots
provide a visual example; a historical test screenshot is not evidence that the
latest code was rerun. Keep older images labelled historical, refresh the UI
images after redesign and current-model images where IDs matter. No new results
or screenshots are fabricated by this documentation delivery.
