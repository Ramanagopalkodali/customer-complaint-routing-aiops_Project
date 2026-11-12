# Evaluation rubric answers

Reference: **AI Application Evaluation Guideline (1).pdf**, pages 1–2. The rubric totals 25 marks: demonstration 5, software engineering 5, AIOps 10 and viva 5. This table answers each question; it does not predict marks or certify full compliance. Status distinguishes source implementation, recorded evidence, newly supplied documentation and remaining work.

| Section | Rubric question | Answer for this implementation | Status | Related document |
|---|---|---|---|---|
| UI/UX [3] | Intuitive for the problem? | Single/CSV flows show product, confidence, team and review reason. | Implemented; demo judgement | [user_manual.md](user_manual.md) |
| UI/UX [3] | Easy for a non-technical user? | Four labelled tabs, sample CSV, spinner, readable results and download. | Implemented; manual demo | [user_manual.md](user_manual.md) |
| UI/UX [3] | Foolproof UX? | Strict API/CSV constraints and review policy handle specified invalid cases; arbitrary off-domain text is not guaranteed safe. | Bounded | [low_level_design.md](low_level_design.md) |
| UI/UX [3] | Free of UI errors? | HTTP/TestClient checks pass and historical screenshots exist; full browser automation is absent. | Partial evidence | [test_plan_and_report.md](test_plan_and_report.md) |
| UI/UX [3] | Colours, shapes and appearance? | Streamlit layout/cards/warnings and provisioned Grafana; visual quality requires evaluator judgement. | Demo assessment | [user_manual.md](user_manual.md) |
| UI/UX [3] | Responsive UI? | Waiting indicators and bounded inputs implemented; browser/device/load responsiveness not benchmarked. | Partial evidence | [test_plan_and_report.md](test_plan_and_report.md) |
| UI/UX [3] | User manual? | Task-oriented non-technical manual provided. | Document provided | [user_manual.md](user_manual.md) |
| Pipeline [2] | Separate screen including data ingestion? | Pipeline tab renders the actual DVC-derived dependency graph and ingestion counts/speed. | Implemented | [architecture.md](architecture.md) |
| Pipeline [2] | Alternative MLOps UI used? | Custom screen is the primary view; MLflow UI and Grafana are optional/operator tool views. | Answered | [deployment.md](deployment.md) |
| Pipeline [2] | Seamless multiple-tool experience? | Backend assembles saved DVC/MLflow/test evidence into one REST snapshot; tool UIs are not embedded. | Implemented with limits | [high_level_design.md](high_level_design.md) |
| Pipeline [2] | Pipeline management console? | An interactive evidence console refreshes saved results and DVC status; execution uses CLI wrappers. Run/stop buttons are not explicitly required by the rubric. | Implemented visibility; control interpretation qualified | [low_level_design.md](low_level_design.md) |
| Pipeline [2] | Errors, failures and successes console? | Saved XML outcomes, lifecycle status and available baseline log failures are displayed; no general run-history UI. | Implemented with limits | [test_plan_and_report.md](test_plan_and_report.md) |
| Pipeline [2] | Pipeline speed/throughput? | Ingestion 23.411 s and 96,341.28 input rows/s; per-step timings are in replay JSON. | Recorded measurement | [model_development.md](model_development.md) |
| Design [2] | Application design document? | Current architecture, HLD, LLD, deployment and lifecycle design are supplied. | Documents provided | [README.md](README.md) |
| Design [2] | OO or functional paradigm? | RoutingService/collectors/Pydantic classes plus functional numerical/gating helpers. | Implemented | [high_level_design.md](high_level_design.md) |
| Design [2] | LLD endpoints and I/O? | All custom endpoints, request/response fields, validation and files specified. | Document provided | [low_level_design.md](low_level_design.md) |
| Design [2] | Architecture diagram? | Local serving/monitoring and offline lifecycle diagrams with block descriptions. | Document provided | [architecture.md](architecture.md) |
| Design [2] | HLD diagram? | Conditional training/acceptance/deployment flow and rationale documented. | Document provided | [high_level_design.md](high_level_design.md) |
| Design [2] | Loose frontend/backend coupling through configurable REST? | Frontend only uses HTTP; API_BASE_URL and separate Compose services provide separation. | Implemented | [low_level_design.md](low_level_design.md) |
| Implementation [2] | Standardised Python style? | Named modules/functions/classes and docstrings; syntax audit passes. No formatter/linter report; some unused imports/long lines remain. | Partial evidence | [audit_findings.md](audit_findings.md) |
| Implementation [2] | Logging? | Baseline/lifecycle logs, step/status records and backend exceptions; submitted text excluded from durable response/log output. | Implemented | [low_level_design.md](low_level_design.md) |
| Implementation [2] | Comprehensive exception handling? | Validation, stage aborts, bundle failures, HTTP errors and drill recovery handled. XML/schema edge paths remain bounded limitations. | Implemented with limits | [low_level_design.md](low_level_design.md) |
| Implementation [2] | Adheres to design? | This design was checked against supplied source and recorded I/O; the documentation update changes no implementation files. | Source-reviewed | [architecture.md](architecture.md) |
| Implementation [2] | Inline documentation? | Module/function/class docstrings and targeted comments exist. No formal docstring completeness measurement. | Implemented with limits | [high_level_design.md](high_level_design.md) |
| Implementation [2] | API follows interface specification? | Pydantic/OpenAPI and route definitions match the documented custom endpoints. | Source/evidence checked | [low_level_design.md](low_level_design.md) |
| Implementation [2] | Unit-test cases implemented? | 77 recorded cases combine unit, temporary-file and real-model/API integration checks. | Implemented | [test_cases.md](test_cases.md) |
| Testing [1] | Test plan? | Scope, levels, commands, manual checks and retest procedure provided. | Document provided | [test_plan_and_report.md](test_plan_and_report.md) |
| Testing [1] | Enlistment of cases? | All 77 XML case IDs link to their source modules and expected behaviour. | Document provided | [test_cases.md](test_cases.md) |
| Testing [1] | Report counts passed/failed? | 77 passed, zero failures/errors/skips in latest full-suite XML/JSON. | Recorded PASS | [test_plan_and_report.md](test_plan_and_report.md) |
| Testing [1] | Acceptance criteria defined? | Data/API/promotion/deployment criteria and six fixed model gates are explicit. | Implemented/documented | [test_plan_and_report.md](test_plan_and_report.md) |
| Testing [1] | Acceptance criteria met? | Current candidate passed all six checks; core HTTP/monitoring checks passed. Fresh handoff checks are pending. | Core passed; handoff pending | [audit_findings.md](audit_findings.md) |
| Data engineering [2] | Ingestion/transformation using Ray/Spark/K8s? | Ray reads/cleans three archives with two CPU workers; driver deduplicates chronologically. | Ray implemented | [model_development.md](model_development.md) |
| Data engineering [2] | Data-engineering speed/throughput? | Measured whole-ingestion report includes duration, rows/s and source dispositions. | Recorded | [model_development.md](model_development.md) |
| Data engineering [2] | Ray/Spark/K8s or custom pipeline present? | Ray plus a DVC-orchestrated pipeline. Spark/Kubernetes/Airflow are not needed for this chosen implementation. | Implemented | [architecture.md](architecture.md) |
| Source control/CI [2] | CI using DVC? | Validation/test stages gate local DVC reproduction and wrappers stop failures; no push-triggered hosted CI. | Local CI implemented | [high_level_design.md](high_level_design.md) |
| Source control/CI [2] | DVC DAG? | dvc.yaml/lock and generated PNG/Mermaid DAG are present, including ingestion and lifecycle. | Implemented | [architecture.md](architecture.md) |
| Source control/CI [2] | Git, Git LFS and/or DVC versioning? | Git source/evidence and DVC large working assets; ordinary Git for small pictures and reports. Active LFS tracking is absent. | Rubric alternative met; proposal deviation | [proposal_compliance.md](proposal_compliance.md) |
| Tracking [2] | How experiments tracked during building? | Two local MLflow experiments, SQLite store, model URIs/run IDs and saved comparison/lifecycle results. | Implemented; DB outside ZIP | [model_development.md](model_development.md) |
| Tracking [2] | Metrics/parameters/artifacts tracked? | F1/accuracy/log loss/timing, TF-IDF/estimator settings, predictions, matrices, policies and model packages. | Implemented | [model_development.md](model_development.md) |
| Tracking [2] | Beyond autolog? | Explicit log_params/log_metrics/log_artifacts and tags for source commit/data/config/model hashes. | Implemented | [high_level_design.md](high_level_design.md) |
| Instrumentation [2] | Prometheus instrumentation? | Counters, histograms, loaded-model gauge, saved-report collectors and health probes. | Implemented | [low_level_design.md](low_level_design.md) |
| Instrumentation [2] | Information monitored? | Requests/errors/preparation latency/confidence/routing/batches/model ID, VM health and historical model/drift scores. | Implemented | [low_level_design.md](low_level_design.md) |
| Instrumentation [2] | All components monitored? | Apps, exporters and VM are live-monitored; ephemeral Ray/training/MLflow use saved evidence rather than dedicated continuous exporters. | Partial for literal all-components reading | [architecture.md](architecture.md) |
| Instrumentation [2] | Grafana in near real time? | Provisioned Prometheus datasource/dashboard, 10-second scrape and 5-second refresh; fresh selected-model metric verified. | Recorded PASS | [deployment.md](deployment.md) |
| Packaging [2] | MLflow APIfication? | MLflow sklearn packages are loaded by custom FastAPI; standalone MLflow Serve was not evidenced. Optional direct-serving check is documented. | Interpretation/evidence gap | [deployment.md](deployment.md) |
| Packaging [2] | MLprojects dev/test parity? | MLproject docker_env uses the backend image and Docker-backed backend tests; recorded XML is older and requires refresh. | Implemented; refresh evidence | [deployment.md](deployment.md) |
| Packaging [2] | FastAPI APIs for interactive UI? | Health, single/batch prediction, pipeline and metrics endpoints support the separate UI. | Implemented | [low_level_design.md](low_level_design.md) |
| Packaging [2] | Backend/frontend dockerised? | Separate Dockerfile targets using shared pinned dependency stage. | Implemented | [architecture.md](architecture.md) |
| Packaging [2] | Separate Compose services? | backend and frontend services communicate over internal REST; six services total. | Implemented | [deployment.md](deployment.md) |
| Viva [5] | Explain the entire project? | Use architecture/data/lifecycle flow, current provenance and metric distinctions. | Requires student's oral demonstration | [high_level_design.md](high_level_design.md) |
| Viva [5] | Answer Assignments 1–10? | Review actual course assignments separately; this ZIP does not establish preparation for all ten. | Not assessable from repository | [audit_findings.md](audit_findings.md) |
| Viva [5] | Explain MLOps tools/use cases? | Explain Ray ingestion, DVC graph/cache, MLflow tracking, Docker isolation and Prometheus/Grafana roles. | Preparation guide | [architecture.md](architecture.md) |
| Viva [5] | Explain design/implementation choices? | Defend CPU-linear models, calibration, macro-F1, predicted-category thresholds and chronological splits. | Preparation guide | [high_level_design.md](high_level_design.md) |
| Viva [5] | Defend challenged choices? | Discuss no-trigger versus demonstration, allowed accuracy drop, local-only deployment and explicit limitations. | Requires student's defence | [model_development.md](model_development.md) |

## Mandatory documents

All five are supplied in this update: architecture/block explanations, HLD/rationale, LLD/API I/O, test plan/case catalogue, and non-technical manual. The uploaded repo already had initial drafts, but several stated that implemented stages were still pending or referenced previous model IDs.

## Assessment boundaries

The functional project is substantially implemented and the latest replay is well evidenced. Current-model recovery/backup refresh, matching DVC-store distribution and fresh-clone startup, and the tool-specific MLflow/LFS interpretations must be addressed transparently. Read-only job management, complete live component coverage, UI responsiveness and code-style completeness remain qualified rather than unconditional yes answers.
