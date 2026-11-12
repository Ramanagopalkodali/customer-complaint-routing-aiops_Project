# Screenshot and machine evidence index

Screenshots retain their existing paths. The stage 7/8 image bytes in the uploaded snapshot match the earlier model-generation screenshots and are historical. Current replay JSON/XML/CSV/logs identify the new candidate `caa8bd53da5f4fb1871725b08a80ec70`. A screenshot of an old model is not current-model proof.

## Current machine evidence

| Evidence | Location |
|---|---|
| Baseline replay | [baseline.json](../reports/reproduction/baseline.json), [log](../logs/reproduction/baseline.log) |
| Lifecycle replay | [lifecycle.json](../reports/reproduction/lifecycle.json), [log](../logs/reproduction/lifecycle.log) |
| Full suite | [77-case XML](../reports/final/full_tests.xml), [summary](../reports/final/tests_summary.json) |
| Current HTTP/monitoring | [live check](../reports/final/pipeline_live_check.json) |
| November acceptance | [decision](../reports/lifecycle/acceptance/decision.json) |
| Deployment/rollback | [verification](../reports/lifecycle/deployment_verification.json) |
| December evaluation | [summary](../reports/lifecycle/final/summary.json), [confusion matrix](../reports/lifecycle/final/confusion_matrix.png) |
| Generated pipeline | [PNG](../reports/reproduction/pipeline_dag.png), [Mermaid](../reports/reproduction/pipeline_dag.mmd) |

## Existing screenshot inventory

| Group | File |
|---|---|
| Monitoring | [alerts_firing.png](alerts_firing.png) |
| Application/testing | [app_batch.png](app_batch.png) |
| Application/testing | [app_invalid_input.png](app_invalid_input.png) |
| Application/testing | [app_pipeline.png](app_pipeline.png) |
| Application/testing | [app_pipeline_results.png](app_pipeline_results.png) |
| Application/testing | [app_pipeline_throughput.png](app_pipeline_throughput.png) |
| Application/testing | [app_review.png](app_review.png) |
| Application/testing | [app_single.png](app_single.png) |
| Application/testing | [backend_api.png](backend_api.png) |
| Monitoring | [backend_mentrics.png](backend_mentrics.png) |
| Application/testing | [backend_running.png](backend_running.png) |
| Application/testing | [backend_tests.png](backend_tests.png) |
| Model development | [category_thresholds.png](category_thresholds.png) |
| Packaging/testing | [container_smoke.png](container_smoke.png) |
| Packaging/testing | [docker_build_running.png](docker_build_running.png) |
| Packaging/testing | [docker_services.png](docker_services.png) |
| Monitoring | [grafana_application_trafic.png](grafana_application_trafic.png) |
| Monitoring | [grafana_initial.png](grafana_initial.png) |
| Monitoring | [grafana_vm_mentrics.png](grafana_vm_mentrics.png) |
| Data engineering | [ingestion_dag.png](ingestion_dag.png) |
| Data engineering | [ingestion_dag_1.png](ingestion_dag_1.png) |
| Data engineering | [ingestion_result.png](ingestion_result.png) |
| Data engineering | [ingestion_running.png](ingestion_running.png) |
| Data engineering | [ingestion_tests.png](ingestion_tests.png) |
| Packaging/testing | [mlproject_tests.png](mlproject_tests.png) |
| Model development | [model_comparision.png](model_comparision.png) |
| Packaging/testing | [model_export.png](model_export.png) |
| Monitoring | [monitoring_instrumentation_tests.png](monitoring_instrumentation_tests.png) |
| Monitoring | [monitoring_traffic_pass.png](monitoring_traffic_pass.png) |
| Model development | [october_test.png](october_test.png) |
| Packaging/testing | [portable_backend_tests.png](portable_backend_tests.png) |
| Monitoring | [prometheus_alerts.png](prometheus_alerts.png) |
| Monitoring | [prometheus_config.png](prometheus_config.png) |
| Monitoring | [prometheus_targets.png](prometheus_targets.png) |
| Model development | [review_threshold.png](review_threshold.png) |
| stage7 (historical) | [stage7/candidate_acceptance.png](stage7/candidate_acceptance.png) |
| stage7 (historical) | [stage7/candidate_training.png](stage7/candidate_training.png) |
| stage7 (historical) | [stage7/conditional_runner.png](stage7/conditional_runner.png) |
| stage7 (historical) | [stage7/december_final_evaluation.png](stage7/december_final_evaluation.png) |
| stage7 (historical) | [stage7/deployment_rollback.png](stage7/deployment_rollback.png) |
| stage7 (historical) | [stage7/lifecycle_dashboard.png](stage7/lifecycle_dashboard.png) |
| stage7 (historical) | [stage7/monitoring_result.png](stage7/monitoring_result.png) |
| stage8 (historical) | [stage8/full_tests.png](stage8/full_tests.png) |
| stage8 (historical) | [stage8/pipeline_lifecycle.png](stage8/pipeline_lifecycle.png) |
| stage8 (historical) | [stage8/recovered_deployment.png](stage8/recovered_deployment.png) |
| Model development | [training_result.png](training_result.png) |
| Model development | [training_running.png](training_running.png) |
| Model development | [validation_team_routing.png](validation_team_routing.png) |

## Final refresh

After the current model/recovery checks pass, replace these existing pictures using the same filenames: `stage8/pipeline_lifecycle.png` (current model and matching December result), `stage7/lifecycle_dashboard.png` (live/historical panels), `stage8/full_tests.png`, and `stage8/recovered_deployment.png` after current recovery. The old alert firing image remains useful historical alert-rule evidence.

Add one focused `stage8/mlflow_runs.png` showing the current training run with parameters, metrics and artifacts. This image is an instruction for final capture and is not claimed to exist yet. Use synthetic text and exclude private passwords. Computational reports/logs are saved automatically; browser screenshots require actual manual capture.
