# Development guideline assessment

Reference: **AI Application Development Guidelines.pdf**, pages 1–3.
This is an evidence-based assessment of its framework. The guideline explicitly
allows adaptation to project requirements/context; the local-only restriction
and the evaluation rubric still apply. Documenting a limit does not implement
the missing capability.

## Core principles

| Principle | Implementation/evidence | Assessment |
|---|---|---|
| Automation | Baseline/lifecycle wrappers run ingestion, tests, training, gating, deployment and checks with fixed outputs. A committed model-ID binding separates phases. | Substantial local automation; not fully unattended CD |
| Reproducibility | Pinned raw hashes, DVC dependency/output hashes, Git commits, MLflow run/model IDs and portable bundle manifests. | Implemented; distribution/recovery refresh needed |
| CI | DVC test/validation stages stop failed downstream work. | Local invocation; no push-triggered hosted pipeline |
| Monitoring/logging | Live app/VM/probe metrics, saved historical performance/drift, backend and replay logs. | Implemented with batch-performance limits |
| Collaboration | Shared Git source/configuration/evidence and documented interfaces. | Repository support; teamwork practices not assessable |
| Version control | Git plus DVC for source/data/models/config; MLflow for experiment records. | Implemented; active Git LFS absent |
| Environment parity | Docker backend/frontend targets, locked Python packages, MLproject using backend image. | Reusable environment recipe; host/container OS not identical |

## Lifecycle requirements

| Area | Implementation | Gap/boundary |
|---|---|---|
| Business understanding and measurable outcomes | Five products, confidence/team/review; macro-F1 plus accuracy and routing coverage/precision; fixed acceptance gates. | No real support-workflow time-saving or customer-satisfaction study |
| Data identification/acquisition | Public CFPB source, three preserved exports, schema/dates/checksums and DVC storage. | Original download was manual; no immutable public URL for those exact exports |
| Collection scripts/configuration versioning | Ray ingestion and pinned source manifest are versioned. | Download automation itself was not supplied |
| EDA/quality | Missing narratives, excluded products, class imbalance, deduplication counts, chronological checks and length-distribution proxies. | Basic EDA; no comprehensive outlier/subgroup/fairness report |
| Automated preprocessing | Ray reads/filters, normalises text and driver deduplicates; tests and summary report. | Does not detect semantic near-duplicates |
| Feature engineering | Sparse TF-IDF unigram/bigram features fit on training data. | No formal feature-importance or feature-ablation artifact |
| Feature impact/versioning | Fixed TF-IDF settings and two-model validation results tracked. | Predictive coefficient/attribution analysis is not reported |
| Algorithm choice/training | Logistic Regression and calibrated LinearSVC; class balance, seed 42, CPU thread limits. | Fixed hyperparameters, no broad search |
| Evaluation/model comparison | Validation selection, October original test, separate November candidate acceptance and December final result. | No confidence intervals or statistical significance study |
| Experiment tracking | Explicit metrics/parameters/artifacts/tags beyond autolog, local MLflow models/run IDs. | Current real tracking DB is outside Git ZIP; fresh backup needed |
| Containerised training | Inference and MLproject tests use Docker; main data/model training runs in the pinned host Conda environment. | Training container execution was not evidenced |
| Deployment strategy/serving | Online local inference through separate frontend/FastAPI; MLflow portable packages. | One backend instance; no canary/blue-green traffic split |
| CI/CD deployment automation | CLI replay validates acceptance then deploys/verifies selected model. | Invocation/identity commit checkpoint is manual; no push-triggered deployment |
| Rollback | Verified candidate→original→candidate drill and failure recovery within deployment helper. | Later wrapper failures do not universally auto-rollback |
| Performance monitoring | Request/error/latency/confidence/routing metrics plus saved labelled scores. | No live ground-truth feedback/accuracy stream |
| Drift detection | Base-2 JSD of length/predicted-category marginals and labelled F1 floor. | Historical proxy drift; not a universal semantic/concept-drift detector |
| Retraining | Conditional trigger path, explicit rehearsal, acceptance gate and versioned candidate. | One frozen historical scenario, no arbitrary incoming-batch scheduler |
| Alerting | Six continuously evaluated Prometheus rules and historical firing screenshot. | No Alertmanager/external notification delivery |
| Model lifecycle/versioning | Manifest/source hashes, training/model URIs, DVC original/candidate and persisted bundle selection. | No named registry production alias or model-retirement service |

## Stack and best practices

| Topic | Assessment |
|---|---|
| Local-only execution | Training, serving and monitoring run on the VM. Git/package/image/data retrieval use remote sources; no cloud model execution is configured. |
| Ray/Spark/Kubernetes recommendation | Ray is chosen. Spark and Kubernetes are alternatives; adding them is not required to justify this implementation. |
| Docker/Compose | Both application services and four monitoring/exporter services are defined. Swarm/K8s not applicable to this single-VM scope. |
| Model serving recommendation | Custom REST serving loads an MLflow package. A direct MLflow Serve check is documented as an additional option. |
| Clean documented testable code | Docstrings, separated layers and 77 recorded automated cases. No linter/formatter/coverage report supplied. |
| Unit/integration/end-to-end testing | Pure-function and API/model integration plus real HTTP/Docker smoke exist. Full browser end-to-end automation is absent. |
| Security/encryption | Loopback binding, non-root app containers, private env and payload hashes; no API login, TLS or verified at-rest encryption. Encryption requirement remains unimplemented. |
| Scalability | Sparse features, bounded batches, shared Docker layers and two-worker ingestion fit laptop resources. No capacity/concurrency benchmark supports production-scale claims. |
| Explainability | Product probabilities, thresholds and explicit review reasons are exposed. No instance attribution/SHAP/global coefficient report is supplied. |
| Documentation | Five mandatory design/test/user documents and operator/compliance maps supplied in this update. |
| Continuous improvement | Reproducible reports and explicit remaining actions support review. No claim about an established team learning/review process can be proven from this ZIP. |

## Practical priorities

1. Apply the current documentation, supply the matching DVC store separately
   and follow the README from a clean Git checkout.
2. Refresh current-model DVC/Docker recovery, MLproject checks and MLflow backup;
   transfer recovery material outside the VM.
3. Capture current Pipeline/Grafana/MLflow evidence and rehearse the demo/viva.
4. If time and evaluator expectations require broader guideline coverage, add
   bounded feature-importance/ablation, meaningful API capacity measurement,
   source-style/coverage checks and appropriate security work. These are current
   gaps, not capabilities created by the documentation.

The project satisfies the central local historical-routing lifecycle described
in its proposal. It should not be represented as a production-hardened or
unconditionally complete implementation of every broad guideline.
