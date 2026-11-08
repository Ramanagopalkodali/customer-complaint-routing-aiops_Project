# Model development and evaluation

Compared TF-IDF with Logistic Regression and calibrated LinearSVC.
Selected calibrated LinearSVC by validation macro-F1.
TF-IDF is fitted on training data; SVC calibration uses training folds.
Category-specific review thresholds were selected on validation data.
October was used for held-out evaluation, without threshold adjustment.

## Held-out results

- test_accuracy: 0.8952223882904705
- test_automatic_accuracy: 0.9466111200128184
- test_automatic_count: 31205
- test_automatic_coverage: 0.8041282275936711
- test_macro_f1: 0.8264181985761796
- test_review_rate: 0.19587177240632891

## Limitations

The validation routing-precision target is not a future guarantee.
October mortgage routing precision was 91.70%; debt collection routing precision was 94.55%, with only 165 automatically routed cases.
Only 3.33% of actual debt-collection complaints were correctly automatically routed. Human review remains essential.

Detailed results: reports/test/summary.json, team_routing.csv, classification_report.json and confusion_matrix.png.

Training run: 978e2c9d02e0494195e9989a3222fd9d

Evaluation run: 495ec69309314dd580dce1884664bc84

Evaluation source commit: c62b6332549f653e319907fb15261b38a875bc39
