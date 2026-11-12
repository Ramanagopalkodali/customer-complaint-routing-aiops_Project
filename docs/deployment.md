# Local deployment, release and recovery

## Supported operating mode

Commands are intended for the Ubuntu/Linux development VM. Docker runs the
application, metrics store/dashboard and exporters locally. Git/package/image
downloads require network access during setup; inference is performed locally.
The host Python 3.11 Conda environment is used for DVC restoration, training,
MLproject and verification commands.

## Artifact restoration and startup

The supplied Git ZIP lacks model binaries because canonical assets are
DVC-managed. The local remote path is intentionally not committed. Obtain the
matching store separately, then follow the root README's clone/environment,
`dvc pull`, ignored `.env`, writable-directory and Compose startup commands.
Git alone is insufficient to start this revision on another machine.

On the existing VBox, preserve the working `.env`, model folders and DVC store.
Documentation-only updates require no rebuild/restart. To resume stopped
services, use `docker compose up -d --wait --wait-timeout 180`.

Use both Compose files:

~~~bash
docker compose -f compose.yaml -f compose.override.yaml build backend frontend
docker compose -f compose.yaml -f compose.override.yaml up -d --wait --wait-timeout 180
~~~

The host original bundle is `artifacts/serving`. The candidate bundle is
`artifacts/lifecycle/candidate/serving`. Compose binds the selected host folder
to the backend's `/app/artifacts/serving`. Host `artifacts/policy.json` remains
the original policy, so inspect the selected serving bundle's policy when
checking the active candidate. `GET /healthz` is the runtime identity check.

## Services and persistence

| Service | VM endpoint | Main persistent inputs/outputs |
|---|---|---|
| Backend | 127.0.0.1:8000 | Selected bundle read-only; reports/logs writable; project evidence read-only; DVC temp writable |
| Frontend | 127.0.0.1:8501 | Backend URL configured through environment |
| Prometheus | 127.0.0.1:9090 | Provisioned scrape/alert files; named time-series volume |
| Grafana | 127.0.0.1:3000 | Provisioned datasource/dashboard; named settings volume |
| Blackbox | Internal 9115 | HTTP health-probe configuration |
| node-exporter | Internal 9100 | Read-only VM filesystem/proc/sys mounts and host PID namespace |

Prometheus retention is configured for two days and 256 MB. Scrape/evaluation
intervals are 10 seconds; Grafana dashboard refresh is 5 seconds. The six
scrape targets include two application probes. A scrape target being up means
the exporter was scraped; `probe_success=1` separately establishes HTTP health.

Named volumes survive `docker compose down`. Routine shutdown should not use
`down -v` if dashboard/time-series history is needed.

## Permissions and secrets

Create host logs/reports/DVC temporary directories before the first container
startup; otherwise Docker can create root-owned directories. The README commands
create them as the current user and set LOCAL_UID/LOCAL_GID to match.
Backend/frontend run with that configured identity.
If existing runtime folders are root-owned, repair only those known generated
folders after checking ownership; do not recursively change the whole project.

`.env` is private and ignored. Preserve a nonempty existing Grafana password;
the README configuration command does so. For an already initialised Grafana volume, changing an
environment password does not necessarily change the stored account password;
recover the original configuration or deliberately reset the local account.
A fresh volume uses the configured password.

Ports bind to VM loopback. There is no API authentication, TLS, or verified
at-rest encryption. Model checksum verification detects byte changes in trusted
packages; it is not a signature or an encryption scheme. Do not expose this
demonstration publicly without additional security work.

## Routine checks and idle dashboards

~~~bash
curl -fsS http://127.0.0.1:8000/healthz
curl -fsS http://127.0.0.1:8501/_stcore/health
python scripts/smoke_containers.py
docker compose logs --tail 100 backend frontend
~~~

The live smoke sends synthetic requests and checks valid input, batch
count, invalid input 422, OOV review, pipeline and frontend health. Request-rate,
latency and confidence panels need recent prediction samples; idle or newly
restarted series may show no data until requests and at least two scrapes occur.
An inactive alert normally means its expression is not currently sustained.

Configured rules: scrape target down (30 s), application endpoint down (30 s),
backend 5xx increase (30 s), prediction p95 preparation latency >1 s (2 min),
available VM memory <10% (1 min), missing saved pipeline report (1 min).
No Alertmanager or external notification receiver is configured.

## Deployment and rollback

`verify_lifecycle_deployment.py` verifies a selected candidate's hashes and
acceptance before switching. It compares real HTTP predictions with the local
reference on six examples, checks invalid input/frontend health, then performs
candidate → original → candidate. It persists the final choice in `.env`.
On failure within that drill it attempts original-model recovery and records
the result. The source original bundle remains available throughout.

Manual original-model selection for this one invocation:

~~~bash
SERVING_BUNDLE_PATH=./artifacts/serving docker compose \
  -f compose.yaml -f compose.override.yaml up -d --no-deps \
  --force-recreate --wait backend
~~~

To return to the selected candidate:

~~~bash
SERVING_BUNDLE_PATH=./artifacts/lifecycle/candidate/serving docker compose \
  -f compose.yaml -f compose.override.yaml up -d --no-deps \
  --force-recreate --wait backend
~~~

These shell overrides apply to that command only; they do not change `.env`.
For a persistent selection, update SERVING_BUNDLE_PATH there deliberately.
The Pipeline screen marks a December result as belonging to another model
during original-model rollback. Check `/healthz` after switching.

This is a sequential local deployment, with possible restart downtime. It does
not implement traffic splitting, blue/green or canary deployment. A failure in
later evaluation/tests/monitoring can leave a previously deployed candidate
active; inspect health and use the documented rollback instead of assuming
every wrapper failure performs rollback.

## Exact data and model recovery

Current training assets are recoverable using the local DVC store. It must be
pushed after the current lock is recorded. Then commit source/lock/reports before
running the existing recovery scripts:

~~~bash
dvc push
git add dvc.lock reports
git diff --cached --check
git commit -m "Record current recovery inputs"
python scripts/verify_artifact_recovery.py
python scripts/verify_recovered_deployment.py
~~~

If the checkpoint already has no changes, use the existing commit rather than
creating an empty one. The first script creates a separate Git checkout and
independent empty DVC cache, restores data/both models, compares local inference,
and checks independence from the tracking DB. It reads the local store at
`$HOME/complaint-routing-dvc-store`.

The second builds backend/frontend from that recovered checkout on ports
8002/8502, checks prediction/validation/pipeline identity, and removes its own
containers. The recovered checkout is retained outside the production repo.
The current submitted recovery records use the **previous** run IDs
`978e2c9d02e0494195e9989a3222fd9d` and `f8d2fa4071174ad3b799a9719ba4697c`;
refresh them before describing current-model clean-checkout recovery as verified.

## Tracking history backup and UI

The saved older verification covers 10 runs, 56 artifact files and three model
packages. It predates original `376d762990d44d59af5080825e9be19a` and candidate
`caa8bd53da5f4fb1871725b08a80ec70`; it remains historical evidence rather than
proof that the latest experiments were backed up.

For a fresh snapshot after all training/MLproject writes have stopped:

1. Use SQLite's backup API (or an equivalent consistent SQLite backup) to copy
   `mlflow.db`; copy the associated `mlruns/` tree into the same backup directory.
2. Check `PRAGMA integrity_check`, include both current training run IDs, and
   compare source/copied artifact hashes rather than relying only on file counts.
3. Load the copied MLflow sklearn packages directly and check predictions and
   finite, normalised probabilities; identify the current packages explicitly.
4. Save the actual verification result only after those checks run. Existing
   `reports/final/mlflow_backup*.json` and `mlflow_artifact_verification.json`
   should not be relabelled with new IDs without performing the checks.
5. Transfer the coherent snapshot outside the VM if protection against VM loss
   is required. Same-VM snapshots are not off-machine backups.

This documentation update does not implement or execute a new backup tool.
The backup refresh is a remaining handoff action, not a model-training task.

Optional tracking UI on that VM:

~~~bash
mlflow ui --backend-store-uri "sqlite:///$PWD/mlflow.db" --host 127.0.0.1 --port 5000
~~~

The Git checkout does not contain tracking history. Copy the DB and
`mlruns` together for history recovery. Absolute artifact URIs inside the DB
must be considered separately; relocating the full tracking UI to
another path/machine requires separate verification. Direct package inference
is portable and does not depend on those DB URIs.

## Optional direct MLflow Serve verification

The normal application exposes a custom FastAPI around an MLflow sklearn
package. A separate MLflow Serve process was not evidenced in the uploaded
snapshot. If a literal MLflow serving endpoint is expected for the packaging
rubric, run this additional local smoke without changing the application.
The raw MLflow endpoint returns class labels; FastAPI adds confidence, teams
and review-policy behaviour.

Terminal 1, in the training environment:

~~~bash
set -o pipefail
mlflow models serve \
  -m "$PWD/artifacts/lifecycle/candidate/serving/model" \
  --host 127.0.0.1 --port 5001 --env-manager local \
  2>&1 | tee logs/reproduction/mlflow_serve.log
~~~

After it is ready, Terminal 2:

~~~bash
python - <<'PYCODE'
import json
from pathlib import Path
import mlflow.sklearn
import numpy as np
import requests
bundle = Path("artifacts/lifecycle/candidate/serving")
payload = json.loads((bundle / "model/serving_input_example.json").read_text())
response = requests.post(
    "http://127.0.0.1:5001/invocations", json=payload, timeout=30
)
response.raise_for_status()
actual = response.json()["predictions"]
model = mlflow.sklearn.load_model(str(bundle / "model"))
expected = list(map(str, model.predict(np.asarray(payload["inputs"]))))
assert actual == expected
record = {
    "status": "PASS",
    "scope": "Local MLflow Serve output matches local package predictions",
    "bundle_training_run_id": json.loads(
        (bundle / "manifest.json").read_text()
    )["training_run_id"],
    "examples": len(actual),
    "predictions_match": True,
}
Path("reports/final/mlflow_serve_smoke.json").write_text(
    json.dumps(record, indent=2) + "\n"
)
print(json.dumps(record, indent=2))
PYCODE
~~~

Then stop Terminal 1 with Ctrl+C. This command uses the MLflow-generated input
example for the package. No execution result for this additional check is
claimed by the documentation audit.

Official serving reference:
[MLflow local deployment](https://mlflow.org/docs/latest/ml/deployment/deploy-model-locally/).

## Distribution and reproducibility bounds

Git provides the source/configuration and saved reports. The separately supplied
DVC store provides model/data bytes for startup and exact replay. The tracking
DB/artifact snapshot provides history recovery. A store/archive on the same VM
does not protect against VM loss. Current-model clean-checkout recovery and a
fresh tracking backup remain pending refresh in the audited snapshot.

Python dependency versions and a Docker base digest are pinned, but apt-installed
system packages are not fully pinned. Replayed MLflow run IDs/timestamps and
serialization hashes can change; verify internal provenance consistency within
each replay rather than expecting UUID/byte identity between new experiments.
