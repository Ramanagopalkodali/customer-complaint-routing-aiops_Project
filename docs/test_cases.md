# Automated test-case catalogue

Source: the latest 77-case full-suite XML in the audited snapshot. Parameterized suffixes identify the input variants in each test file. Results below are the recorded VM results; this documentation audit did not rerun the model-dependent suite.

| ID | Test/source | Expected behaviour | Recorded result |
|---|---|---|---|
| T001 | [`test_backend.py`](../tests/test_backend.py) · `test_health` | 200, status ok and a model version | PASS |
| T002 | [`test_backend.py`](../tests/test_backend.py) · `test_single_prediction_contract` | Valid product/probability/team and consistent review fields | PASS |
| T003 | [`test_backend.py`](../tests/test_backend.py) · `test_rejects_invalid_single_input[payload0]` | HTTP 422 for the parameterised invalid payload | PASS |
| T004 | [`test_backend.py`](../tests/test_backend.py) · `test_rejects_invalid_single_input[payload1]` | HTTP 422 for the parameterised invalid payload | PASS |
| T005 | [`test_backend.py`](../tests/test_backend.py) · `test_rejects_invalid_single_input[payload2]` | HTTP 422 for the parameterised invalid payload | PASS |
| T006 | [`test_backend.py`](../tests/test_backend.py) · `test_rejects_invalid_single_input[payload3]` | HTTP 422 for the parameterised invalid payload | PASS |
| T007 | [`test_backend.py`](../tests/test_backend.py) · `test_rejects_invalid_single_input[payload4]` | HTTP 422 for the parameterised invalid payload | PASS |
| T008 | [`test_backend.py`](../tests/test_backend.py) · `test_rejects_invalid_single_input[payload5]` | HTTP 422 for the parameterised invalid payload | PASS |
| T009 | [`test_backend.py`](../tests/test_backend.py) · `test_rejects_invalid_single_input[payload6]` | HTTP 422 for the parameterised invalid payload | PASS |
| T010 | [`test_backend.py`](../tests/test_backend.py) · `test_rejects_invalid_single_input[payload7]` | HTTP 422 for the parameterised invalid payload | PASS |
| T011 | [`test_backend.py`](../tests/test_backend.py) · `test_rejects_invalid_batch[payload0]` | HTTP 422 for the parameterised invalid batch | PASS |
| T012 | [`test_backend.py`](../tests/test_backend.py) · `test_rejects_invalid_batch[payload1]` | HTTP 422 for the parameterised invalid batch | PASS |
| T013 | [`test_backend.py`](../tests/test_backend.py) · `test_rejects_invalid_batch[payload2]` | HTTP 422 for the parameterised invalid batch | PASS |
| T014 | [`test_backend.py`](../tests/test_backend.py) · `test_batch_matches_single_predictions_in_order` | Batch order and predictions match individual calls | PASS |
| T015 | [`test_backend.py`](../tests/test_backend.py) · `test_unrecognized_text_requires_review` | OOV input receives human_review=true | PASS |
| T016 | [`test_backend.py`](../tests/test_backend.py) · `test_pipeline_snapshot` | Pipeline fields/DAG/ingestion evidence returned | PASS |
| T017 | [`test_backend.py`](../tests/test_backend.py) · `test_metrics_count_success_and_validation_failure` | Success and validation-failure counters increment | PASS |
| T018 | [`test_backend.py`](../tests/test_backend.py) · `test_metrics_expose_process_and_saved_evidence` | Process and saved-evidence metrics exposed | PASS |
| T019 | [`test_candidate_acceptance.py`](../tests/test_candidate_acceptance.py) · `test_qualifying_candidate_passes` | Every acceptance guardrail is true | PASS |
| T020 | [`test_candidate_acceptance.py`](../tests/test_candidate_acceptance.py) · `test_candidate_failing_a_guardrail_is_rejected[macro_f1-0.824-macro_f1_improves]` | Named guardrail is false | PASS |
| T021 | [`test_candidate_acceptance.py`](../tests/test_candidate_acceptance.py) · `test_candidate_failing_a_guardrail_is_rejected[recall-value1-per_class_recall_preserved]` | Named guardrail is false | PASS |
| T022 | [`test_candidate_acceptance.py`](../tests/test_candidate_acceptance.py) · `test_candidate_failing_a_guardrail_is_rejected[automatic_count-499-sufficient_automatic_predictions]` | Named guardrail is false | PASS |
| T023 | [`test_candidate_acceptance.py`](../tests/test_candidate_acceptance.py) · `test_candidate_failing_a_guardrail_is_rejected[automatic_accuracy-0.93-automatic_accuracy_floor]` | Named guardrail is false | PASS |
| T024 | [`test_candidate_acceptance.py`](../tests/test_candidate_acceptance.py) · `test_candidate_failing_a_guardrail_is_rejected[automatic_accuracy-0.944-automatic_accuracy_preserved]` | Named guardrail is false | PASS |
| T025 | [`test_candidate_acceptance.py`](../tests/test_candidate_acceptance.py) · `test_candidate_failing_a_guardrail_is_rejected[automatic_coverage-0.77-automatic_coverage_preserved]` | Named guardrail is false | PASS |
| T026 | [`test_candidate_acceptance.py`](../tests/test_candidate_acceptance.py) · `test_candidate_failing_a_guardrail_is_rejected[automatic_accuracy-None-automatic_accuracy_floor]` | Named guardrail is false | PASS |
| T027 | [`test_ingest.py`](../tests/test_ingest.py) · `test_chronological_boundaries[2024-04-01-train]` | Date maps to the named chronological split | PASS |
| T028 | [`test_ingest.py`](../tests/test_ingest.py) · `test_chronological_boundaries[2024-07-31-train]` | Date maps to the named chronological split | PASS |
| T029 | [`test_ingest.py`](../tests/test_ingest.py) · `test_chronological_boundaries[2024-08-01-validation]` | Date maps to the named chronological split | PASS |
| T030 | [`test_ingest.py`](../tests/test_ingest.py) · `test_chronological_boundaries[2024-09-30-validation]` | Date maps to the named chronological split | PASS |
| T031 | [`test_ingest.py`](../tests/test_ingest.py) · `test_chronological_boundaries[2024-10-01-test]` | Date maps to the named chronological split | PASS |
| T032 | [`test_ingest.py`](../tests/test_ingest.py) · `test_chronological_boundaries[2024-10-31-test]` | Date maps to the named chronological split | PASS |
| T033 | [`test_ingest.py`](../tests/test_ingest.py) · `test_chronological_boundaries[2024-11-01-future]` | Date maps to the named chronological split | PASS |
| T034 | [`test_ingest.py`](../tests/test_ingest.py) · `test_chronological_boundaries[2024-12-31-future]` | Date maps to the named chronological split | PASS |
| T035 | [`test_ingest.py`](../tests/test_ingest.py) · `test_removes_duplicate_id_across_splits` | Repeated ID excluded from later split | PASS |
| T036 | [`test_ingest.py`](../tests/test_ingest.py) · `test_removes_repeated_text_across_splits` | Normalised repeated text excluded later | PASS |
| T037 | [`test_ingest.py`](../tests/test_ingest.py) · `test_removes_repeated_text_within_split` | Duplicate text removed within split | PASS |
| T038 | [`test_ingest.py`](../tests/test_ingest.py) · `test_rejects_missing_class` | Missing target class raises ValueError | PASS |
| T039 | [`test_ingest.py`](../tests/test_ingest.py) · `test_rejects_overlapping_dates` | Overlapping split dates raise ValueError | PASS |
| T040 | [`test_ingest.py`](../tests/test_ingest.py) · `test_preserves_unique_records` | Unique records and expected class counts retained | PASS |
| T041 | [`test_lifecycle_metrics.py`](../tests/test_lifecycle_metrics.py) · `test_missing_reports_are_unavailable` | Availability is zero for missing reports | PASS |
| T042 | [`test_lifecycle_metrics.py`](../tests/test_lifecycle_metrics.py) · `test_valid_report_preserves_zero_trigger_and_model_identity` | Zero-valued trigger and run ID preserved | PASS |
| T043 | [`test_lifecycle_metrics.py`](../tests/test_lifecycle_metrics.py) · `test_invalid_metric_does_not_publish_partial_report` | Invalid report is unavailable without partial gauges | PASS |
| T044 | [`test_lifecycle_monitoring.py`](../tests/test_lifecycle_monitoring.py) · `test_identical_distributions_have_zero_divergence` | Divergence approximately zero | PASS |
| T045 | [`test_lifecycle_monitoring.py`](../tests/test_lifecycle_monitoring.py) · `test_disjoint_distributions_have_unit_divergence` | Base-2 divergence approximately one | PASS |
| T046 | [`test_lifecycle_monitoring.py`](../tests/test_lifecycle_monitoring.py) · `test_invalid_distributions_are_rejected[left0-right0]` | Invalid counts/shapes raise ValueError | PASS |
| T047 | [`test_lifecycle_monitoring.py`](../tests/test_lifecycle_monitoring.py) · `test_invalid_distributions_are_rejected[left1-right1]` | Invalid counts/shapes raise ValueError | PASS |
| T048 | [`test_lifecycle_monitoring.py`](../tests/test_lifecycle_monitoring.py) · `test_invalid_distributions_are_rejected[left2-right2]` | Invalid counts/shapes raise ValueError | PASS |
| T049 | [`test_lifecycle_monitoring.py`](../tests/test_lifecycle_monitoring.py) · `test_invalid_distributions_are_rejected[left3-right3]` | Invalid counts/shapes raise ValueError | PASS |
| T050 | [`test_lifecycle_monitoring.py`](../tests/test_lifecycle_monitoring.py) · `test_trigger_boundaries_and_independent_conditions` | Equality does not trigger; each exceeded condition does | PASS |
| T051 | [`test_lifecycle_runner.py`](../tests/test_lifecycle_runner.py) · `test_no_trigger_skips_training_and_deployment` | No train/package/deploy callbacks | PASS |
| T052 | [`test_lifecycle_runner.py`](../tests/test_lifecycle_runner.py) · `test_rejected_candidate_is_not_packaged_or_deployed` | Reject outcome skips package/deploy | PASS |
| T053 | [`test_lifecycle_runner.py`](../tests/test_lifecycle_runner.py) · `test_accepted_candidate_runs_steps_in_order` | Monitor/train/accept/package/deploy order | PASS |
| T054 | [`test_lifecycle_runner.py`](../tests/test_lifecycle_runner.py) · `test_step_failure_stops_following_steps[monitor]` | Injected stage exception prevents later callbacks | PASS |
| T055 | [`test_lifecycle_runner.py`](../tests/test_lifecycle_runner.py) · `test_step_failure_stops_following_steps[train]` | Injected stage exception prevents later callbacks | PASS |
| T056 | [`test_lifecycle_runner.py`](../tests/test_lifecycle_runner.py) · `test_step_failure_stops_following_steps[accept]` | Injected stage exception prevents later callbacks | PASS |
| T057 | [`test_lifecycle_runner.py`](../tests/test_lifecycle_runner.py) · `test_step_failure_stops_following_steps[package]` | Injected stage exception prevents later callbacks | PASS |
| T058 | [`test_lifecycle_runner.py`](../tests/test_lifecycle_runner.py) · `test_step_failure_stops_following_steps[deploy]` | Injected stage exception prevents later callbacks | PASS |
| T059 | [`test_lifecycle_runner.py`](../tests/test_lifecycle_runner.py) · `test_invalid_monitoring_never_starts_training[monitoring0]` | Invalid status/trigger prevents training | PASS |
| T060 | [`test_lifecycle_runner.py`](../tests/test_lifecycle_runner.py) · `test_invalid_monitoring_never_starts_training[monitoring1]` | Invalid status/trigger prevents training | PASS |
| T061 | [`test_lifecycle_runner.py`](../tests/test_lifecycle_runner.py) · `test_inconsistent_acceptance_never_deploys` | Contradictory gate/decision evidence rejected | PASS |
| T062 | [`test_model_bundle.py`](../tests/test_model_bundle.py) · `test_rejects_modified_policy` | Changed policy fails bundle hash verification | PASS |
| T063 | [`test_model_bundle.py`](../tests/test_model_bundle.py) · `test_loads_without_tracking_database` | Five-class model loads without creating tracking DB | PASS |
| T064 | [`test_pipeline_lifecycle.py`](../tests/test_pipeline_lifecycle.py) · `test_evaluation_is_linked_to_matching_live_model` | Matching model identity flag is true | PASS |
| T065 | [`test_pipeline_lifecycle.py`](../tests/test_pipeline_lifecycle.py) · `test_different_live_model_does_not_inherit_historical_evaluation` | Different model identity flag is false | PASS |
| T066 | [`test_pipeline_lifecycle.py`](../tests/test_pipeline_lifecycle.py) · `test_malformed_optional_evidence_does_not_break_console` | Malformed optional JSON becomes null | PASS |
| T067 | [`test_threshold.py`](../tests/test_threshold.py) · `test_selects_maximum_eligible_coverage` | Highest eligible coverage threshold selected | PASS |
| T068 | [`test_threshold.py`](../tests/test_threshold.py) · `test_includes_confidence_equal_to_threshold` | Confidence exactly at threshold is accepted | PASS |
| T069 | [`test_threshold.py`](../tests/test_threshold.py) · `test_reviews_all_when_quality_target_unmet` | No qualifying threshold yields review-all | PASS |
| T070 | [`test_threshold.py`](../tests/test_threshold.py) · `test_requires_minimum_automatic_count` | Insufficient support cannot enable automatic routing | PASS |
| T071 | [`test_threshold.py`](../tests/test_threshold.py) · `test_rejects_invalid_confidence[nan]` | Nonfinite/out-of-range confidence raises ValueError | PASS |
| T072 | [`test_threshold.py`](../tests/test_threshold.py) · `test_rejects_invalid_confidence[inf]` | Nonfinite/out-of-range confidence raises ValueError | PASS |
| T073 | [`test_threshold.py`](../tests/test_threshold.py) · `test_rejects_invalid_confidence[-0.1]` | Nonfinite/out-of-range confidence raises ValueError | PASS |
| T074 | [`test_threshold.py`](../tests/test_threshold.py) · `test_rejects_invalid_confidence[1.1]` | Nonfinite/out-of-range confidence raises ValueError | PASS |
| T075 | [`test_threshold.py`](../tests/test_threshold.py) · `test_thresholds_use_predicted_categories` | Threshold grouping uses predicted labels | PASS |
| T076 | [`test_threshold.py`](../tests/test_threshold.py) · `test_disabled_and_unknown_categories_require_review` | Disabled/unknown category routes to review | PASS |
| T077 | [`test_threshold.py`](../tests/test_threshold.py) · `test_routing_applies_each_category_boundary` | Each predicted category uses its own threshold | PASS |

## Input variant key

The payload suffixes refer to the order in the linked parameter decorators:

| Family | Variants |
|---|---|
| Invalid single payload0–7 | Missing text; empty text; spaces; short text; integer; null; 10,001 characters; extra property |
| Invalid batch payload0–2 | Empty list; 101 complaints; one invalid item among valid items |
| Invalid distributions left0–3/right0–3 | Zero total; negative count; unequal vector lengths; nonfinite count |
| Invalid confidence | NaN, positive infinity, -0.1 and 1.1 |
| Acceptance guardrail variants | Insufficient F1, excessive recall drop, count 499, accuracy below floor/preservation, low coverage, unavailable accuracy |

The source modules specify constructed arrays, records and exact assertions.
These fixture inputs are distinct from the full ingestion/model-run evidence.
