# Latest handoff verification

This post-audit check supersedes the earlier pending recovery/backup/MLproject evidence statuses. It does not change historical measurements.

Verified at: 2026-11-12T00:29:15.036235+00:00.

Source checkpoint: `0d4054dda2d851e32be100da4634af32d88f7e0c`.

Original training run: `376d762990d44d59af5080825e9be19a`. Selected candidate: `caa8bd53da5f4fb1871725b08a80ec70`.

| Check | Result |
|---|---|
| Empty-cache DVC recovery of both current models | PASS |
| Recovered-checkout Docker/HTTP smoke | PASS |
| Current Docker-backed MLproject backend suite | 18 passed, zero failures/errors/skips |
| SQLite integrity, current run/model inclusion, copied artifact hashes | PASS |
| Inference from copied MLflow packages | PASS |
| DVC and MLflow archives, every archived file hash checked | PASS |

Machine evidence: [verification](../reports/final/handoff_verification.json), [archive manifest](../reports/final/artifact_handoff.json), [MLproject](../reports/mlproject_success.json), [backup](../reports/final/mlflow_backup_verification.json).

Archives are outside Git, under `~/complaint-routing-handoff/`. They have been prepared inside the VM. Copy them to the host/USB or share them with the evaluator separately; off-machine transfer has not been verified by this script. Tracking DB artifact paths are not relocated; direct copied-package inference was checked.

The MLproject cases overlap the complete 77-case suite and must not be added to its total. No training or December reevaluation ran. Screenshots and the recording are separate presentation tasks.

## Artifact distribution

[Shared artifact folder](https://drive.google.com/drive/folders/1KHOP9f8lswEbXwzxMYLv2oAKEw8zBRI4?usp=sharing).

The owner confirmed that all four files are visible and downloadable.
Archive checksums are provided in SHA256SUMS.txt and handoff_manifest.json.
