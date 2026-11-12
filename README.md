# Customer Complaint Routing System with AIOps

A local application for banking and finance support agents. Paste one complaint
or upload a CSV to obtain the predicted product, estimated confidence,
recommended support team and human-review decision.

The five products are bank accounts, credit cards, credit reporting, debt
collection and mortgages. The application makes recommendations; it does not
create tickets or forward complaints to a real department.

## Recorded result

The supplied VM replay completed successfully on 12 November 2026 IST:
**77 automated cases passed, with no failures, errors or skips**.
The candidate passed all six November acceptance checks, was deployed, rolled
back to the original model, and redeployed. December evaluation then completed.

| December metric | Recorded value |
|---|---:|
| Complaints | 41,282 |
| Macro-F1 | 0.831386 |
| Overall accuracy | 89.60% |
| Automatically routed fraction | 83.06% |
| Accuracy within automatically routed complaints | 94.25% |

Selected training run: `caa8bd53da5f4fb1871725b08a80ec70`.
These are saved historical-label results. Confidence and validation precision
targets do not guarantee correctness on a new complaint.

## Repository map

| Folder/file | Purpose |
|---|---|
| `backend/`, `frontend/` | Independent FastAPI and Streamlit services |
| `src/` | Ray ingestion, model comparison, routing and historical lifecycle |
| `scripts/` | Existing reproduction, deployment and verification commands |
| `config/`, `dvc.yaml`, `dvc.lock` | Frozen policies, input checksums and pipeline versions |
| `monitoring/` | Prometheus, probes, alerts and provisioned Grafana dashboard |
| `data/`, `artifacts/` | DVC working datasets and generated model assets |
| `reports/`, `logs/reproduction/` | Fixed-path machine evidence and two replay transcripts |
| `evidence/` | Screenshots and their index |
| `docs/` | Design, API, testing, user and compliance documentation |

## Clone, restore artifacts and start

Run these commands **inside the Ubuntu/Linux VM**, as your normal user.
Prerequisites: Git, Conda, Docker Engine with Compose V2, and initial internet
access for Git/package/image downloads. Use Python 3.11 for the host environment
and the pinned Docker base from `.env.example`. The private Git repository
requires access credentials.

**Important artifact prerequisite:** Git contains source and saved reports,
but not the model binaries or training datasets. The repository's DVC remote
is a private, same-VM filesystem store rather than a public download service.
Before starting a different machine, obtain the maintainer's matching
`complaint-routing-dvc-store` directory or its archive, and place the extracted
store at `$HOME/complaint-routing-dvc-store`. On the existing VBox this directory
already exists. A Git clone alone is insufficient; the commands below restore
the committed model/data versions from that store without retraining.

### 1. Clone and install the host environment

~~~bash
git clone https://github.com/Ramanagopalkodali/customer-complaint-routing-aiops_Project.git &&
cd customer-complaint-routing-aiops_Project
conda create -n complaint-aiops python=3.11 pip -y
conda activate complaint-aiops
python -m pip install -r requirements.lock.txt &&
python -m pip check
~~~

On your existing VBox, reuse the environment and project instead:

~~~bash
conda activate complaint-aiops
cd ~/customer-complaint-routing-aiops_Project
~~~

### 2. Restore the exact DVC assets

Skip this step on the existing VM when all assets are present and current.
For a clone, after copying/extracting the store:

~~~bash
artifact_store="$HOME/complaint-routing-dvc-store"
test -d "$artifact_store" &&
dvc remote add --local --force -d localstore "$artifact_store" &&
dvc pull
~~~

Stop if the store is missing or `dvc pull` fails. Do not build the backend with
missing serving files. The DVC store must include the objects referenced by this
Git revision's `dvc.lock` and `data/raw.dvc`. Neither MLflow's tracking database
nor raw-data re-downloads are required for inference once serving assets are
restored.

### 3. Prepare local configuration

The following is a one-time setup **command**, not an added application file.
It checks the selected model identity against saved final evidence, creates
writable runtime folders, and creates/updates ignored `.env` configuration.
An existing nonempty Grafana password is preserved.

~~~bash
python - <<'PYCODE'
import json
import os
import secrets
from pathlib import Path

root = Path.cwd()
original = root / "artifacts/serving/manifest.json"
candidate = root / "artifacts/lifecycle/candidate/serving/manifest.json"
assert original.is_file() and candidate.is_file(), "Restore both DVC bundles first"
version = json.loads(candidate.read_text())["training_run_id"]
final = json.loads((root / "reports/lifecycle/final/summary.json").read_text())
assert version == final["selected_training_run_id"], "Model/evaluation mismatch"
for relative in ("logs", "reports/app_results", ".dvc/tmp"):
    directory = root / relative
    directory.mkdir(parents=True, exist_ok=True)
    assert os.access(directory, os.W_OK), f"Directory not writable: {directory}"
path = root / ".env"
text = path.read_text() if path.exists() else (root / ".env.example").read_text()
values = {}
for line in text.splitlines():
    if "=" in line and not line.lstrip().startswith("#"):
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
password = values.get("GRAFANA_ADMIN_PASSWORD") or secrets.token_urlsafe(24)
updates = {
    "LOCAL_UID": str(os.getuid()),
    "LOCAL_GID": str(os.getgid()),
    "GRAFANA_ADMIN_PASSWORD": password,
    "SERVING_BUNDLE_PATH": "./artifacts/lifecycle/candidate/serving",
}
lines = [line for line in text.splitlines()
         if line.split("=", 1)[0].strip() not in updates]
lines.extend(f"{key}={value}" for key, value in updates.items())
path.write_text("\n".join(lines) + "\n")
path.chmod(0o600)
print("Local configuration prepared; selected model:", version)
PYCODE
~~~

If the directory check fails, inspect ownership of the reported generated
directory before fixing it. Do not run the project as root or change ownership
of the entire repository. Model-payload hashes are verified by the existing
backend loader at startup; the command above only checks model identities.

### 4. Build and start all six services

~~~bash
docker compose -f compose.yaml -f compose.override.yaml build backend frontend &&
docker compose -f compose.yaml -f compose.override.yaml up -d --wait --wait-timeout 180 &&
docker compose ps
curl -fsS http://127.0.0.1:8000/healthz
curl -fsS http://127.0.0.1:8501/_stcore/health
~~~

Expected: application services become healthy; the backend reports
`status: ok` and the selected training run. Open these links in the VM browser:

| Service | Local URL |
|---|---|
| Application | http://127.0.0.1:8501 |
| API documentation | http://127.0.0.1:8000/docs |
| Prometheus targets | http://127.0.0.1:9090/targets |
| Grafana | http://127.0.0.1:3000 |

Grafana username is `admin`. View your local password with:

~~~bash
python - <<'PYCODE'
from pathlib import Path
for line in Path(".env").read_text().splitlines():
    if line.strip().startswith("GRAFANA_ADMIN_PASSWORD="):
        print(line.split("=", 1)[1])
PYCODE
~~~

Keep that value local. For an existing Grafana volume, the stored login may
retain its original password. Preserve your existing `.env` rather than
generating a replacement password. Uploaded CSV content remains in the active
Streamlit session's memory; backend output records exclude submitted text.

Loopback URLs refer to the VM. Use its browser or an explicitly configured SSH
tunnel when accessing from the Mac/Windows host. If Pipeline shows DVC workspace
`unavailable`, this means its status subprocess failed or timed out; it does
not by itself establish that inference or the trained model is broken. Inspect
host `dvc status --json` and container logs before claiming current freshness.

## Stop, restart and diagnose

~~~bash
docker compose down
docker compose up -d --wait --wait-timeout 180
docker compose logs --tail 100 backend frontend
~~~

`down` preserves named monitoring volumes; retain them to keep Grafana settings.
The [user manual](docs/user_manual.md) covers complaint and CSV use.
See [deployment](docs/deployment.md) for permissions, rollback, Grafana and idle
dashboard behavior. Prediction-rate/confidence panels need recent prediction
traffic; historical scores are separately labelled.

## Developer environment and tests

Activate the existing host environment with `conda activate complaint-aiops`.
If creating a new environment, use the installation commands above. With both
serving packages available, run the full suite without retraining or repeating December evaluation:

~~~bash
python scripts/run_final_checks.py &&
python scripts/smoke_containers.py
~~~

Outputs: `reports/final/full_tests.xml`, `reports/final/tests_summary.json`,
`logs/final_tests.log` and `reports/container_smoke.json`.
The full suite links its candidate bundle to the saved final evaluation.
After the suite succeeds, `dvc commit --force final_checks` registers the
freshly executed XML/summary in the lock without rerunning tests or training.
Test inventory and interpretation: [test plan](docs/test_plan_and_report.md)
and [all 77 cases](docs/test_cases.md).

Run the existing Docker-backed MLproject test separately:

~~~bash
bash scripts/test_mlproject.sh
~~~

That entry point tests the original serving bundle mounted at `/app`;
the selected candidate is covered by `run_final_checks.py`. The submitted
MLproject XML is historical and should be refreshed before final handoff.

## Full rebuild workflow

This is an explicit historical replay. It stops services, refreshes generated
results, and can train/deploy a candidate. Starting the application above does
not run this workflow.

First restore the **exact** DVC snapshot. On the current VM the store is already
at `$HOME/complaint-routing-dvc-store`. On a different machine, copy the supplied
offline store/archive there before these commands:

~~~bash
artifact_store="$HOME/complaint-routing-dvc-store"
test -d "$artifact_store" &&
dvc remote add --local --force -d localstore "$artifact_store" &&
dvc pull
~~~

The store is separate from Git. The three raw ZIP checksums are committed in
`config/raw_sources.json`. CFPB's [official database](https://www.consumerfinance.gov/data-research/consumer-complaints/)
provides exports and an API, but later exports may contain different rows or
ZIP bytes. Use the preserved snapshot for exact replay. Initial export filters
and expected schema are in [data/model development](docs/model_development.md).

The baseline runner requires one pre-rebuild snapshot beside the repo. Existing
VM users already have it. For a fresh full-rebuild checkout, create it once:

~~~bash
python - <<'PYCODE'
from pathlib import Path
import tarfile
root = Path.cwd()
backup = root.parent / "complaint-routing-before-rebuild.tar.gz"
if not backup.exists():
    temporary = backup.with_name(backup.name + ".partial")
    try:
        with tarfile.open(temporary, "w:gz") as archive:
            for name in (
                "src", "backend", "frontend", "scripts", "tests", "config",
                "monitoring", "docs", "evidence", "reports", "artifacts",
                "logs", "README.md", "Dockerfile", "MLproject",
                "compose.yaml", "compose.override.yaml", "dvc.yaml",
                "dvc.lock", "requirements.txt", "requirements.lock.txt",
                "data/raw.dvc", ".env.example", ".gitignore", ".gitattributes",
                ".dvcignore",
            ):
                if (root / name).exists():
                    archive.add(root / name, arcname=name)
        temporary.chmod(0o600)
        temporary.replace(backup)
    finally:
        temporary.unlink(missing_ok=True)
print(backup)
PYCODE
~~~

This archive preserves code, serving assets and evidence. Raw/processed data
remain recoverable through DVC; back up the tracking DB/artifacts separately.
Commit any source/configuration edits before running:

~~~bash
python scripts/reproduce_baseline.py
~~~

Expected: `reports/reproduction/baseline.json` reports `PASS` and a new original
training run. Bind that identity while retaining periods and acceptance settings:

~~~bash
python - <<'PYCODE' &&
import hashlib
import json
from pathlib import Path
baseline = json.loads(Path("reports/reproduction/baseline.json").read_text())
assert baseline["status"] == "PASS"
manifest_path = Path("artifacts/serving/manifest.json")
assert hashlib.sha256(manifest_path.read_bytes()).hexdigest() == baseline["serving_manifest_sha256"]
manifest = json.loads(manifest_path.read_text())
assert manifest["training_run_id"] == baseline["original_model_version"]
path = Path("config/lifecycle.json")
config = json.loads(path.read_text())
config["champion_training_run_id"] = manifest["training_run_id"]
temporary = path.with_suffix(".tmp")
temporary.write_text(json.dumps(config, indent=2) + "\n")
temporary.replace(path)
print("Bound champion:", manifest["training_run_id"])
PYCODE
git add config/lifecycle.json dvc.lock reports &&
git diff --cached --check &&
git commit -m "Record rebuilt baseline and bind lifecycle champion" &&
python scripts/reproduce_lifecycle.py
~~~

The lifecycle runner refreshes monitoring, executes the conditional controller,
uses an explicit rehearsal if the historical batch has no trigger, gates the
candidate, packages it, verifies deployment/rollback, evaluates December and
runs the full suite and live monitoring checks. A failed acceptance gate retains
the original and returns `CHAMPION_RETAINED`. Investigate that result rather than
lowering thresholds using December outcomes.

The deployment and final-evaluation stages remain frozen in DVC. The runner
executes their commands explicitly and registers completed evidence. Use this
two-phase workflow for full replay; a bare forced `dvc repro` does not perform
the complete identity-binding/deployment/final-evaluation sequence.

## Evidence replacement and saving results

| Fixed location | Contents |
|---|---|
| `logs/reproduction/baseline.log` | Latest baseline command transcript |
| `logs/reproduction/lifecycle.log` | Latest lifecycle command transcript |
| `reports/reproduction/baseline.json`, `lifecycle.json` | Steps, timings, provenance and outcome |
| `reports/lifecycle/` | Latest monitoring, candidate, acceptance, deployment and final results |
| `reports/final/full_tests.xml`, `tests_summary.json` | Latest full-suite outcome |
| `reports/final/pipeline_live_check.json` | Current endpoint/model/monitoring verification |
| `reports/reproduction/pipeline_dag.png`, `pipeline_dag.mmd` | Generated workflow diagrams |

Phase reports and plots are replaced at those paths. MLflow intentionally
retains experiment history; operational request-response records accumulate in
the ignored `reports/app_results/` folder. Screenshots require manual capture.
The [evidence index](evidence/README.md) identifies historical images.

After a successful replay, push the DVC assets and save the source/evidence checkpoint:

~~~bash
dvc push &&
git add . &&
git diff --cached --check &&
git commit -m "Save verified replay and current evidence" &&
git push origin main
~~~

## Recovery and tracking handoff

Refresh clean-checkout recovery against the new model IDs after committing the
current DVC lock/reports and pushing artifacts:

~~~bash
python scripts/verify_artifact_recovery.py &&
python scripts/verify_recovered_deployment.py &&
bash scripts/test_mlproject.sh
~~~

The recovery Docker drill uses ports 8002/8502 and removes its test containers.
It uses a separate checkout and the same-VM DVC store. Its saved reports in this
snapshot still reference previous model IDs; refresh them before claiming
current-model clean-checkout recovery. MLproject testing adds a tracking run.

The existing MLflow backup checks cover an earlier 10-run/56-file snapshot.
The new model replay is recorded, but a fresh tracking-history backup is not
established by those old checks. See [deployment](docs/deployment.md) for the
backup scope and refresh procedure. No new backup script is added by this
documentation-only update.

For protection against VM loss, transfer the DVC store and a consistent MLflow
DB/artifact backup to the host or USB. For example, after `dvc push`:

~~~bash
tar -C "$HOME" -czf "$HOME/complaint-routing-dvc-store.tar.gz" complaint-routing-dvc-store
~~~

Copy the archive outside the VM using the configured VirtualBox shared folder
or removable storage. An archive kept inside the VM is still a same-VM backup.

## Documentation and compliance

- [Architecture and block explanations](docs/architecture.md)
- [High-level design and rationale](docs/high_level_design.md)
- [Low-level API and I/O specification](docs/low_level_design.md)
- [Test plan and report](docs/test_plan_and_report.md), [case catalogue](docs/test_cases.md)
- [Non-technical user manual](docs/user_manual.md)
- [End-to-end workflow and file responsibilities](docs/workflow_and_files.md)
- [Data and model development](docs/model_development.md)
- [Deployment and recovery](docs/deployment.md)
- [Rubric-to-code/evidence map](docs/rubric_file_map.md)
- [Evaluation rubric answers](docs/rubric_compliance.md)
- [Development guideline assessment](docs/development_guidelines.md)
- [Submitted proposal/GForm promises](docs/proposal_compliance.md)
- [Audit findings and remaining actions](docs/audit_findings.md)

All training, inference and monitoring run locally. This laptop demonstration
has a read-only pipeline console, historical labelled drift simulation, and no
application authentication/TLS or at-rest encryption. Automated browser tests,
concurrency benchmarks, feature-importance/ablation reports and live delayed-label performance
monitoring were not supplied. Those bounds and the Git LFS/tool-specific choices
are explicitly assessed in the compliance documents.

## Applying this documentation update

This update contains Markdown files only. It changes no Python, tests, Docker,
DVC or monitoring configuration and reruns no model stages. Copy README.md to
the project root and merge the supplied docs/ and evidence/ directories into
the existing directories; retain unrelated files. Review before committing:

~~~bash
git add README.md docs evidence/README.md &&
git diff --cached --check &&
git diff --cached --stat
~~~

Then commit/push the reviewed documentation. A frontend redesign can be done
separately; update the user manual and UI screenshots if labels or workflows
change. No frontend redesign is included in these files.

Latest post-audit status: [handoff verification](docs/handoff_verification.md).
