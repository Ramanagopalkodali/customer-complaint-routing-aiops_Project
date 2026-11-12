# High-level design and rationale

## Problem and measurable outcomes

Manual reading and department selection for free-text financial complaints is
slow and inconsistent. The application predicts one of five CFPB products,
estimates confidence and maps the product to a recommended support team.
Uncertain inputs receive a human-review assignment. This is a support decision
tool; no integration with an organisation's ticketing system is implemented.

Primary model selection metric: macro-F1. Supporting measures: accuracy,
per-class recall/confusion matrices, automatic-routing accuracy and coverage.
The latter measures evaluate different subsets and are reported separately.
November acceptance has fixed numerical requirements; December is a final
measurement rather than a tuning resource.

## Design choices

| Choice | Rationale and trade-off |
|---|---|
| TF-IDF unigram/bigram features | CPU-friendly sparse representation; captures product vocabulary/phrases. It has limited semantic understanding and vocabulary-based OOD detection. |
| Logistic Regression versus calibrated LinearSVC | Bounded comparison aligned with the proposal and laptop limits. SVC achieved the higher validation macro-F1. No large architecture/hyperparameter search is claimed. |
| Training-fold sigmoid calibration | LinearSVC lacks native probabilities. Three training-data folds support confidence estimates while keeping validation/October/December out of fitting. Calibration does not guarantee future accuracy. |
| Class-balanced estimators and macro-F1 | Reduce domination by credit-reporting complaints. Minority-category performance still needs inspection. |
| Chronological splits and forward deduplication | Simulate future operation and reduce repeated-ID/normalized-text leakage. Semantic near-duplicates are not detected. |
| Per-predicted-category thresholds | Products differ in uncertainty. A predicted label is available at inference; selecting thresholds by true label would be unusable and misleading. |
| Separate frontend/backend | UI and inference evolve independently through configurable REST. Each has a separate Compose service. |
| Portable MLflow packages and manifests | Keep prediction independent of the original tracking DB; verify policy/model identity and package bytes. |
| DVC graph with validation gates | Reproduce dependencies and stop downstream work on failed test commands. Git records source; MLflow records experiment identity/outputs. |
| Explicit historical replay | Exercises retraining/acceptance/rollback within local resources. No fabricated drift trigger is needed. |
| Read-only pipeline console | Makes data ingestion, model metrics, errors and saved tests visible without exposing job-execution privileges. It provides no training start/stop UI. |
| Docker dependency stage and pinned Python requirements | Share application/test package versions and cached layers. Host Conda and container OS environments are not byte-identical. |

## Software organisation

`RoutingService` encapsulates the model, policy and prediction logic. Pydantic
models define request/response contracts. Collector classes adapt saved evidence
to Prometheus. Functional helpers calculate divergence, trigger reasons,
threshold decisions and acceptance checks. CLI entry points own filesystem,
tracking and process side effects.

FastAPI routes own validation, response persistence and instrumentation; the
frontend owns interaction and rendering. The backend's evidence adapter reads
the DVC configuration rather than maintaining a second hardcoded DAG. Runtime
report/model locations are configurable through environment variables.

## Lifecycle state transitions

~~~mermaid
flowchart TD
    Monitor["Score historical November batch"] --> Trigger{"Trigger exceeded?"}
    Trigger -->|"No"| Keep["Retain original"]
    Trigger -->|"Yes"| Train["Train isolated candidate"]
    Rehearsal["Explicit demonstration request"] --> Train
    Train --> Gate{"All six acceptance checks pass?"}
    Gate -->|"No"| Keep
    Gate -->|"Yes"| Package["Verify portable package"]
    Package --> Deploy["Deploy, rollback, redeploy"]
    Deploy --> Evaluate["Evaluate December and verify services"]
~~~

The default controller returns `no_trigger` when neither distribution proxy nor
labelled macro-F1 crosses its boundary. The full replay separately invokes the
demonstration stage in that case. A saved `no_trigger` controller report and a
subsequent accepted candidate can therefore coexist without contradiction.
Current model identity comes from the running backend, not the earlier controller
record.

Monitoring uses JSD > 0.10 for either length or predicted-product distribution,
or labelled macro-F1 < 0.80. Equality does not trigger. November labels are assumed
available after arrival in this historical simulation.

The candidate trains on April–July plus November 1–15, chooses thresholds on
November 16–22, and is compared with the original on November 23–30. Every gate
must pass: macro-F1 gain ≥0.005; each class recall drop ≤0.05; automatic count
≥500; automatic accuracy ≥0.94; its drop versus original ≤0.005; coverage drop
≤0.02. December is evaluated after selection and deployment.

## Reproduction and release boundaries

The baseline replay force-executes seven stages. Its new run ID must be committed
into the lifecycle configuration before the lifecycle replay, preserving dates
and acceptance settings. This is an explicit provenance checkpoint, not fully
unattended ingestion-to-production CD. Frozen deployment/evaluation DVC stages
are run deliberately by the lifecycle wrapper and then registered in the lock.

Inference assets and training data are DVC-managed and excluded from ordinary
Git. A clone must obtain the matching DVC store separately, configure its local
remote and pull the committed objects before building Docker. Inference itself
does not need the tracking database. This is a documented artifact handoff,
not a self-contained Git-only distribution. Future training releases require
both a Git checkpoint and a matching DVC push.

## Observability and operations

Request counts, response-preparation latency, errors, batch size, prediction
confidence, routing decisions and loaded model identity are live measurements.
Ingestion performance and model/drift scores are saved batch measurements.
Health probes cover both applications; node-exporter covers VM resources.
Prometheus scrapes/evaluates every 10 seconds; Grafana refreshes every 5 seconds.

Six Prometheus alert rules are configured. No Alertmanager/notification receiver
is included. Ray/training/MLflow are represented by saved outputs and local
tracking, not continuous dedicated process exporters.

The deployment drill performs a sequential switch and rollback on one backend
instance. It is not a blue/green, canary or zero-downtime deployment. Later-stage
failures require operator inspection; rollback commands are documented.

## Current result and limitations

The accepted candidate achieved 0.837020 macro-F1 on the same November acceptance
rows versus 0.830577 for the original. Its December macro-F1 is 0.831386,
with 94.25% accuracy among the 83.06% automatically routed complaints.
Comparing October and December alone cannot establish improvement because the
datasets differ. No statistical significance interval is reported.

No authentication/TLS, at-rest encryption, multi-worker metrics aggregation,
load/capacity benchmark, formal feature-importance/ablation analysis or
demographic fairness assessment is provided. Historical drift replay is not an
arbitrary live-stream retraining service. These bounds match the laptop
demonstration context and are recorded explicitly in the guideline assessment.
