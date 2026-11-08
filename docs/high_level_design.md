# High-level design

## Objective

Predict a financial complaint's product, estimate confidence, recommend
a support team and flag uncertain cases for human review.

## Design choices and rationale

Frontend and backend are independent processes connected by configurable
REST calls. The frontend does not load models or read backend files.
This separation allows either component to change independently.

RoutingService owns inference and routing. Pydantic defines API contracts.
FastAPI loads the MLflow model once at startup and checks its provenance
against the frozen policy.

TF-IDF and linear classifiers suit the available CPU-based laptop.
Logistic Regression and calibrated LinearSVC were compared using validation
macro-F1. LinearSVC won. Calibration uses training folds.

Chronological splits separate training, validation, October testing and
future batches. Repeated IDs and normalized text are removed across splits.
Semantic near-duplicates may remain.

Thresholds are selected by predicted category using validation data.
Low-confidence, disabled-category and unrecognized-vocabulary inputs
require human review.

DVC orchestrates the pipeline. MLflow tracks experiments and models.
The pipeline console displays saved evidence and current DVC freshness.

## Limitations

October macro-F1 was 0.8264. Automatic routing covered 80.41% of complaints
at 94.66% accuracy. Validation precision targets are not future guarantees.
Debt collection has low automatic coverage. Human review is essential.
The system supports five categories and cannot reliably identify every
out-of-domain complaint.
