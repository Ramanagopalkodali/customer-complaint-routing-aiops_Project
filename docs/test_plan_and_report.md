# Test plan and report

## Data engineering stage

Acceptance criteria:
- All source ZIPs pass integrity checks.
- Required input columns are present.
- Only the five selected products and nonempty narratives are retained.
- Every output split contains all five classes.
- Chronological split boundaries do not overlap.
- Repeated complaint IDs and normalized text are excluded across splits.
- Pipeline counts and throughput are saved automatically.

Verification:
- A full Ray ingestion run completed successfully.
- Its results are recorded in reports/ingestion_summary.json.
- Fourteen automated tests passed in the initial test run.
- Tests cover date boundaries, duplicate IDs, duplicate text, missing
  classes, overlapping dates and preservation of unique records.
- The latest automated test results are saved in reports/ingestion_tests.xml.

Scope:
The automated tests use small constructed datasets to check the splitting
and deduplication functions. The full ingestion run also checks source
columns, dates, output class coverage and chronological separation.
Near-duplicate or semantically similar narratives are not detected.

Application, model and deployment tests will be added with those stages.

## Model and routing stage

- Both trained models passed MLflow reload prediction checks.
- Eleven routing-policy tests passed; see reports/threshold_tests.xml.
- Held-out probability shape, range and normalization checks passed.
- Model hash matched the frozen policy before evaluation.
- Test results and limitations are in docs/model_development.md.
