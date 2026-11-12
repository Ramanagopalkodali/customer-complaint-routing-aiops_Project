# Test plan, acceptance criteria and report

## Scope and approach

The automated suite combines pure-function/unit cases, temporary-file integration,
real portable-model loading and FastAPI TestClient integration. Separate scripts
verify real Docker/HTTP deployment, rollback, monitoring and recovered-checkout
inference. Browser interaction and load/capacity testing have separate evidence
limits.

This report describes the uploaded snapshot and its recorded VM execution.
The audit checked source syntax, available DVC file hashes, report hash chains,
current run-ID consistency and independently recomputed prediction metrics.
It did not rerun the model-dependent suite in the audit environment.

## Latest full-suite result

From [tests_summary.json](../reports/final/tests_summary.json) and
[full_tests.xml](../reports/final/full_tests.xml):

| Outcome | Count |
|---|---:|
| Total | 77 |
| Passed | 77 |
| Failed | 0 |
| Errors | 0 |
| Skipped | 0 |

Model: `caa8bd53da5f4fb1871725b08a80ec70`.
Source commit: `1a1af3f7daf3e2f38eaae5a2f590576f30020497`.

| Test module | Cases | Coverage |
|---|---:|---|
| `test_backend.py` | 18 | Health, output contract, single/batch validation, ordering, OOV review, pipeline and metrics |
| `test_candidate_acceptance.py` | 8 | Qualifying candidate and individual gate failures |
| `test_ingest.py` | 14 | Eight date boundaries, ID/text deduplication, missing classes, overlapping dates and unique records |
| `test_lifecycle_metrics.py` | 3 | Missing reports, zero trigger/model identity, invalid metrics |
| `test_lifecycle_monitoring.py` | 7 | Divergence semantics, invalid counts and trigger boundaries |
| `test_lifecycle_runner.py` | 11 | No trigger, rejection, accepted order, stage failures and inconsistent evidence |
| `test_model_bundle.py` | 2 | Modified-policy rejection and inference without tracking DB |
| `test_pipeline_lifecycle.py` | 3 | Matching/different model identity and malformed optional evidence |
| `test_threshold.py` | 11 | Maximum eligible coverage, equality, minimum counts, invalid confidence and category policies |

The [case catalogue](test_cases.md) lists all parameterised case IDs and expected
behaviour. Older 16/18/20-case XML files are progressive/subset historical reports;
they overlap this suite and must not be added to the 77.

## Acceptance criteria

| Area | Required behaviour | Recorded evidence/outcome |
|---|---|---|
| Data | Pinned archives, required columns, supported products, nonempty narratives, all five classes and chronological separation | Baseline PASS; ingestion summary and 14 cases |
| Leakage | Remove repeated IDs/normalised text across splits; fit features/calibration on training; tune thresholds separately | Code checks, ingestion cases and split/evaluation provenance |
| Model | Compare LR/SVC by validation macro-F1; save/reload model and its predictions | Comparison/reload PASS; October held out |
| Routing | ≥ threshold accepts; OOV/null-threshold requires review; strict text/count validation | Threshold and backend cases PASS |
| Monitoring | Correct base-2 JSD, strict boundaries and independent trigger conditions | 7 cases PASS; actual batch no trigger |
| Acceptance | Every one of six frozen numerical checks must pass | Current decision has six true checks; 8 gate cases |
| Promotion | Rejecting a candidate never packages/deploys it; stage failure stops later callbacks | 11 controller cases PASS |
| Packaging | Hashes and identities agree; predictions/probabilities match reload | Package PASS; 6 smoke examples |
| Deployment | Candidate deployment, original rollback and candidate redeployment match local reference output | Three live phases PASS, invalid input 422, frontend 200 |
| Final evaluation | December only after selection/deployment; no final-data tuning | Final report PASS and explicit false tuning flags |
| Current identity | Health, pipeline, final evaluation and metrics identify the selected candidate | Live check PASS |
| Monitoring readiness | Six scrape targets up, two application probes equal 1, fresh selected-model score | Live check PASS |
| Recovery | Empty-cache pull plus portable inference and isolated Docker smoke for current models | Historical checks passed; current-ID refresh pending |
| Tracking backup | Coherent DB/artifact snapshot and inference from copied current packages | Historical checks passed; current-run backup verification pending |

The acceptance report's PASS means the evaluation completed; the separate
`decision` and all gate booleans determine promotion. Final evaluation PASS means
integrity/computation succeeded, not that an arbitrary accuracy target was met.

## Commands and generated results

~~~bash
python scripts/run_final_checks.py
python scripts/smoke_containers.py
~~~

The first runs all cases using the selected candidate via `SERVING_DIR` and
writes fixed XML/summary/log paths. The second exercises real local endpoints.
Use the root README's separate full-replay procedure to repeat ingestion/training
and lifecycle work. Avoid re-running final evaluation to tune a model.

To refresh Docker environment parity evidence:

~~~bash
bash scripts/test_mlproject.sh
~~~

The existing MLproject command tests the original bundle through the shared
backend Docker image. Current candidate HTTP tests are supplied by the full
suite. Its submitted XML contains 16 historical cases; refresh it for the
current 18-case backend module before claiming current MLproject coverage.

## Manual test plan

The following checks should be recorded during final demo rehearsal. Historical
screenshots exist, but no current automated browser test is claimed.

| ID | Action | Expected behaviour | Supplied status |
|---|---|---|---|
| UI-01 | Submit a supported complaint | Product/confidence/team shown; no UI exception | Historical screenshot; current HTTP PASS |
| UI-02 | Submit a short complaint | Actionable minimum-length warning | Historical screenshot |
| UI-03 | Upload valid 2-record CSV and download | Ordered results and readable CSV with 2 records | Historical screenshot |
| UI-04 | Upload wrong header, over-limit or malformed CSV | Actionable validation error; no partial result | Code guards; full browser execution not supplied |
| UI-05 | View review-required input | Human-review reason and provisional team displayed | Historical screenshot; OOV HTTP case PASS |
| UI-06 | Refresh Pipeline | DAG, current model ID and matching final result displayed | Current endpoint PASS; screenshot refresh pending |
| UI-07 | Inspect laptop/mobile-width layout and waiting states | Usable layout, spinner and error handling | Manual responsiveness/accessibility assessment pending |
| OBS-01 | Generate synthetic requests and inspect Grafana | Request/routing/confidence panels populate | Current synthetic traffic and monitoring PASS |
| OBS-02 | Rehearse endpoint failure and recovery | Prometheus alert pending→firing→inactive after configured waits | Historical alert screenshot; repeat only if fresh failure evidence required |
| HAND-01 | Follow README in a fresh Git clone with the matching DVC store | DVC pull restores packages; private env, Docker health and selected ID correct | Current-model fresh-clone drill pending; older drill passed |

No throughput/load SLO for API traffic is asserted. Ingestion throughput is one
measured whole-pipeline run. The latency metric measures response preparation,
not browser/network end-to-end completion. There is no coverage-percentage or
formal accessibility/lint report.

## Failure handling and retest rules

On a failed baseline/lifecycle command, inspect the fixed transcript and JSON
step/error record. Later commands stop. Investigate schema/hash/provenance
failures before repeating; do not register old outputs as newly executed.
Candidate rejection retains the original and does not evaluate December.
The deployment drill attempts original-model recovery for failures within its
own phases. Later test/observability failures require operator inspection.

After changes to model/API/routing logic, rerun the relevant cases and complete
the full suite. Documentation-only changes do not require retraining. This update supplies no
new application or setup code and adds no cases to the recorded 77.
