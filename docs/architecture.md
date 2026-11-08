# Architecture

```mermaid
flowchart TD
    User["Support agent"] --> UI["Streamlit frontend"]
    UI -->|"Configurable REST calls"| API["FastAPI backend"]
    API --> Model["MLflow classifier"]
    API --> Policy["Routing thresholds"]
    API --> Reports["Pipeline reports and DVC status"]
    API --> Results["Saved prediction responses"]
    ZIP["CFPB archives"] --> Ray["Ray ingestion"]
    Ray --> Data["Chronological datasets"]
    Data --> Train["Training and evaluation"]
    Train --> Model
    Train --> Policy
    Train --> Reports
```

## Block explanations

- Frontend: complaint entry, CSV upload, results, help and pipeline screen.
- Backend: input validation, model loading, inference and routing.
- Model: TF-IDF and calibrated LinearSVC, selected by validation macro-F1.
- Policy: thresholds for predicted categories; uncertain inputs require review.
- Ray: reads ZIPs, filters complaints and creates chronological datasets.
- DVC: tracks datasets and orchestrates processing and validation stages.
- MLflow: records experiments, packaged models and evaluation results.
- Reports: saved metrics, test outcomes and prediction responses without text.

Docker packaging, monitoring and drift/retraining are subsequent stages.
