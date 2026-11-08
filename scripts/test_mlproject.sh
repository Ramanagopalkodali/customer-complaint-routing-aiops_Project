#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p logs reports
MLFLOW_TRACKING_URI="sqlite:///$PWD/mlflow.db" \
mlflow run . -e backend_tests \
  --experiment-name complaint-routing \
  -A volume="$PWD:/app" \
  -A user="$(id -u):$(id -g)" \
  2>&1 | tee logs/mlproject_tests.log
