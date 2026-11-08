# Customer Complaint Routing System with AIOps

A local application that predicts a financial complaint's product, estimates
confidence, recommends a support team and flags uncertain cases for review.

Supported products: bank accounts, credit cards, credit reporting,
debt collection and mortgages.

## Environment setup

Run from the cloned repository root.
Create and activate the environment:

    conda create -n complaint-aiops python=3.11 pip -y
    conda activate complaint-aiops
    python -m pip install -r requirements.lock.txt
    python -m pip check

## Data and model prerequisites

Original CFPB ZIPs, processed datasets and model bundles are tracked through
DVC and excluded from ordinary Git storage.

The Docker build requires artifacts/serving to be present. The full pipeline
console also needs restored datasets, DVC metadata and saved reports.
Complete artifact-recovery and clean-checkout instructions will be finalized
before submission. A GitHub ZIP alone currently does not contain these artifacts.

With the required original archives available, committed source and the
environment installed, the pipeline is orchestrated through:

    dvc repro

## Run with Docker Compose

For initial configuration, copy .env.example to .env if .env does not exist.
Set LOCAL_UID and LOCAL_GID to the values from id -u and id -g.
PYTHON_BASE records the selected base-image digest.

    docker compose build
    docker compose up -d --wait
    docker compose ps

Frontend: http://127.0.0.1:8501
API documentation: http://127.0.0.1:8000/docs

The frontend and backend run as separate services. Original terminal-based
servers should be stopped before Compose binds the same ports.

## Verification

Live container checks:

    python scripts/smoke_containers.py

MLproject backend tests inside the Docker environment:

    bash scripts/test_mlproject.sh

Reports are saved under reports/. Logs are saved under logs/.
Successful application responses are saved under reports/app_results/
without complaint text.

## Stop

    docker compose down

## Documentation

- docs/architecture.md: architecture and block explanations
- docs/high_level_design.md: design choices and component diagram
- docs/low_level_design.md: API inputs and outputs
- docs/test_plan_and_report.md: acceptance criteria and test evidence
- docs/user_manual.md: instructions for support agents
- docs/deployment.md: deployment details and limitations
- docs/model_development.md: model comparison and evaluation

## Screenshots

Current screenshots under evidence/ are stored as ordinary Git image files.
Earlier commits may still reference Git LFS objects.

## Current progress

Stages 1-5 are implemented and verified on the development VM.
Monitoring, drift/retraining and final clean-checkout verification remain.
