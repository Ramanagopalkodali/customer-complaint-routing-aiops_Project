# Submitted GForm proposal: promise-by-promise assessment

Reference: **aiops_project .pdf**, the Google Forms receipt titled
“Building an AI Application with AIOps”, submitted 5 October 2026.
Project: **Customer Complaint Routing System with AIOps**,
Ramana Gopal Kodali, DA24B010.

The proposal includes a laptop-resource constraint and possible stack adaptation.
That does not remove the requirement to disclose tool/coverage differences.

| Submitted promise | Current implementation/evidence | Assessment |
|---|---|---|
| Financial customer-service domain and public CFPB complaints | Three pinned 2024 CFPB exports, five product mappings and chronological processed datasets. | Implemented |
| Everything runs locally; no cloud platforms | Local CPU training, inference and monitoring in Ubuntu/Compose. No cloud model or training execution configured. | Implemented for execution |
| Predict product: card, mortgage, bank account, credit reporting or debt collection | Model classes validated against exactly those five support mappings. | Implemented |
| Show prediction confidence | Calibrated LinearSVC predict_proba; confidence returned in API/UI/CSV. | Implemented |
| Recommend support team | Deterministic product-to-team mapping and assigned team field. | Implemented; recommendation only |
| Flag low confidence for human review | Category-specific thresholds; OOV and disabled categories also require review. | Implemented |
| Compare Logistic Regression and LinearSVC with TF-IDF | Two tracked pipelines, validation reports/predictions, macro-F1 selection. | Implemented |
| Macro-F1 primary, accuracy and confusion matrix | Validation, October, acceptance and December records plus matrices/plots. | Implemented |
| Paste one complaint or upload multiple complaints | Streamlit single form and 1–100-record UTF-8 CSV path with result download. | Implemented |
| Ray automates ingestion, cleaning and preparation | Three archive tasks using two CPU workers, forward deduplication, quality checks and saved speed. | Implemented |
| Git, Git LFS and DVC track source/data/model artifacts | Git and DVC are active. Screenshots use ordinary Git; model/data packages use DVC; no active LFS tracking. | Tool-specific deviation: LFS not used |
| DVC DAG reproduces processing/training and forms CI basis, with test/validation stages | Versioned DVC pipeline and explicit baseline/lifecycle wrappers; failed commands stop progress. | Implemented locally; manual invocation/checkpoint |
| MLflow records parameters, metrics and artifacts for reproduction/comparison | Two experiments, explicit logged metadata/provenance, model URIs and reload checks. | Implemented; history stored locally |
| MLflow versions/packages the inference model | Portable MLflow sklearn packages, training identity and manifest/policy checks. | Implemented |
| FastAPI plus separate configurable REST frontend | API_BASE_URL; independent containers; frontend never imports model code. | Implemented |
| MLproject maintains development/test environment | Docker-backed project entry using backend image. | Implemented; current evidence refresh needed |
| Docker/Compose run frontend/backend as separate services | Separate build targets/services with health checks. | Implemented |
| Prometheus request count, response time, errors and confidence | Explicit counters/histograms and metrics endpoint; process/VM/health metrics added. | Implemented |
| Grafana dashboards | Provisioned datasource/dashboard with 5-second refresh. | Implemented and live readiness recorded |
| Chronological historical data simulates incoming batches | November monitoring/train/tuning/acceptance windows, December reserved evaluation. | Implemented exactly as historical simulation |
| Retrain if drift detected or model performance below threshold | OR trigger, guarded conditional controller and 11 workflow cases. Actual recorded monitoring was healthy. | Implemented; real-data trigger did not occur |
| Replace only when performance criteria pass; otherwise retain previous model | Six conjunctive gates and explicit retained-original branch; accepted candidate deployment/rollback verified. | Implemented |
| Architecture/HLD/LLD/test plan/user manual | Initial drafts were stale; current five mandatory documents and case catalogue are provided here. | Supplied by this update |
| Automated, monitored and capable of retraining within laptop limits | CPU-bounded stages and recorded complete replay; online request monitoring plus offline labelled performance. | Implemented within disclosed scope |

## Important interpretation points

**No trigger is a valid monitoring outcome.** The recorded divergences and F1
did not cross their limits. The default controller therefore retained the
original. The separately requested rehearsal trained candidate
`caa8bd53da5f4fb1871725b08a80ec70` with `training_reason=explicit_demonstration`.
This demonstrates retraining/gating/deployment without claiming a drift event.

**The proposal promises recommendations**, not actual dispatch into a company
ticketing system. Team labels are a configured mapping from CFPB product; no
real-company team-assignment ground truth is available.

**MLflow packaging with FastAPI is the submitted design.** It is implemented.
The evaluation rubric's separate “MLflow APIfication” wording may invite a
literal MLflow Serve demonstration; an optional local serving check is given
in the deployment document.

**Git LFS is a disclosed stack deviation.** DVC handles large canonical data/
training assets; ordinary Git handles small pictures and source/evidence.
The rubric permits Git/Git LFS and/or DVC, but the proposal named all three.
Do not state that this snapshot actively uses LFS.

The proposal does not promise Airflow, Spark, Kubernetes, a cloud service,
production-grade authentication, mobile support or a specific numerical final
accuracy. Those should not be invented as delivered features. The broader
guideline's security/explainability/scalability suggestions remain separately
assessed in [development_guidelines.md](development_guidelines.md).
