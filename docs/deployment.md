# Local deployment

## Requirements

Docker and Docker Compose, the repository, its restored data/model artifacts,
and the pipeline reports are required for the complete pipeline console.
The original MLflow database is not needed for model inference.

## Build and start

Restore the DVC artifacts or reproduce the pipeline first.
The exported model bundle must exist at artifacts/serving.

Copy .env.example to .env. Set LOCAL_UID and LOCAL_GID to the output of
id -u and id -g. PYTHON_BASE pins the selected base-image digest.

Run docker compose build, then docker compose up -d --wait.
Check docker compose ps.

Frontend: http://127.0.0.1:8501
API documentation: http://127.0.0.1:8000/docs

## Design

Frontend and backend run as separate services. The frontend uses the
backend service name for REST requests.

The backend image contains the portable MLflow model and policy bundle.
The bundle is checked against its recorded file hashes at startup.
Reports and logs persist through host mounts. Repository access supports
the read-only pipeline console; DVC temporary state has a writable mount.

## Verification

Portable model export preserved predictions and probabilities on five
synthetic smoke examples. Eighteen portable-backend tests passed locally.
Both Compose services became healthy. The MLproject entry point passed
16 backend tests inside the Docker environment.

Run python scripts/smoke_containers.py for live endpoint checks.
Run bash scripts/test_mlproject.sh for the MLproject tests.
Results are saved under reports/ and logs/.

## Stop and restart

Run docker compose down to stop the services.
Run docker compose up -d --wait to start them again.

## Reproducibility limits

DVC artifact retrieval and a complete clean-checkout reproduction still
require final verification. The base-image digest and Python packages are
pinned; operating-system packages installed through apt are not fully pinned.
