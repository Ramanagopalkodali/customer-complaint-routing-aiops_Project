# Repository audit and remaining actions

## Snapshot reviewed

- Archive: `customer-complaint-routing-aiops_Project-main-2(3).zip`.
- Audit date: 12 November 2026.
- ZIP SHA-256: `0eb7a5fe8dac072b8c74ca11810b105cf67ab156c3409a429609e3d55091c606`.
- Relevant project files: 201, approximately 23.0 MiB before this update.
- All three requirement PDFs were read: evaluation guideline, development
  guideline and submitted GForm proposal.

The ZIP also contains a separate Finder `__MACOSX` metadata tree. It is packaging
noise rather than application source. Use a Git archive for a clean submission;
do not remove necessary application/configuration files to make the tree smaller.

## Verified strengths

The supplied baseline and lifecycle replay both report PASS. Current original
run: `376d762990d44d59af5080825e9be19a`. Accepted/deployed candidate:
`caa8bd53da5f4fb1871725b08a80ec70`.

The audit independently parsed 34 Python files and 38 JSON files, parsed the
YAML/XML evidence, verified **39 distinct available file hashes** against
`dvc.lock`, verified the recorded report SHA-256 chain and consistent selected
run IDs, and recomputed both validation score pairs, both original/candidate threshold grids, acceptance/December metrics and the December confusion matrix from saved prediction CSVs.
No available-file hash or recomputed-metric mismatch was found.

The latest full-suite XML records 77 passed cases, zero failures/errors/skips.
The deployment report records candidate deployment, original rollback and
candidate redeployment. Live checks record six scrape targets up, both probes
equal 1, frontend/Grafana health and the current model's score in Prometheus.
Saved DVC status is an empty mapping.

December: macro-F1 0.831386, accuracy 0.895984, automatic coverage 0.830580 and
automatic accuracy 0.942545 on 41,282 complaints. There was no real monitoring
trigger; retraining was an explicit demonstration. Every model acceptance
check passed. These are numerical/report checks, not a new live VM execution
inside the documentation environment.

## Findings and remedies

| Priority | Finding in the uploaded snapshot | Remedy/status |
|---|---|---|
| Before sharing | Git ZIP contains no inference packages; DVC remote exists only in local configuration. Fresh clone cannot build the backend from those files alone. | README requires the matching store separately, restores it with DVC and prepares local runtime configuration. Distribution of the store is still an owner handoff action. |
| Before sharing | README still says stages 1–5 and has incomplete first-start/artifact instructions. | Replaced with clone plus DVC restoration/startup, separate full replay/tests, evidence and recovery instructions. |
| Before sharing | Architecture/test/deployment docs describe implemented features as pending or use previous run IDs. | All five mandatory documents refreshed; case catalogue and compliance maps added. |
| Before final handoff | Recovery/Docker recovery records still cover old original `978e2c9d02e0494195e9989a3222fd9d` and candidate `f8d2fa4071174ad3b799a9719ba4697c`. | Rerun the two existing recovery scripts after current lock/artifacts are saved. |
| Before final handoff | MLflow backup covers 10 historical runs/56 files/3 packages, predating the new models. | Refresh a consistent DB/artifact backup, verify current run/model inclusion and copy outside VM. No new backup code is supplied. |
| Before final handoff | MLproject XML has 16 historical backend cases rather than the current 18-case backend module. | Rerun existing MLproject wrapper and retain the current result. |
| Evidence refresh | Stage 7/8 screenshot bytes are unchanged from the previous snapshot. | Keep them labelled historical; overwrite current Pipeline, Grafana and final-test screenshots after verification. Add MLflow UI evidence. |
| Rubric interpretation | “Pipeline management console” is a read-only snapshot; no start/stop/job queue UI. | Clearly documented; CLI supplies execution control. |
| Rubric interpretation | FastAPI loads an MLflow package; standalone MLflow Serve not evidenced. | Optional direct serving smoke instructions provided. |
| Proposal deviation | Git LFS was named, but active LFS tracking is absent. | Document normal Git/DVC choice; do not claim LFS use. |
| Broad guidelines | No encryption/auth/TLS, load/capacity benchmark, feature-importance/ablation/fairness report, full browser automation or style-tool report. | Explicit gaps; not created by documentation. |
| Monitoring scope | Ray/training/MLflow are represented by batch evidence; no dedicated continuous process exporters or alert receiver. | Document saved-versus-live metrics and local alert-rule scope. |

## Update contents and safety boundary

This update replaces README/design/test/user/evidence-index text and adds
workflow/file-responsibility, rubric/guideline/proposal maps and this audit.
**All delivered files are Markdown.** No application, setup, test or pipeline
scripts are added or changed. Docker/DVC/monitoring configuration, datasets,
model bytes and screenshot paths are preserved.

The README uses existing scripts and ordinary setup commands; it does not claim
that a Git clone already contains excluded assets. Copy the supplied folders
into the existing repository without deleting unrelated files. Preserve old
documents outside the repository if a pre-update copy is needed.

## Owner checklist

1. Copy the Markdown update into the repository and review the API/UI facts.
2. Commit/push the documentation. No full replay is required for this update.
3. Before handoff, push the current DVC objects and make the matching store
   available separately to the evaluator; a Git-only ZIP lacks model binaries.
4. Refresh the two existing recovery checks and Docker-backed MLproject result
   against the current IDs when time permits.
5. Refresh the MLflow DB/artifact backup and copy verified recovery assets
   outside the VM if off-machine protection is required.
6. After the planned frontend redesign, update UI screenshots and any changed
   labels in the manual; preserve older test screenshots as historical evidence.
7. If a literal MLflow Serve endpoint is required by the evaluator, use the
   optional smoke described in deployment; it is not claimed to have run.

None of these handoff/documentation actions requires a new model fit or December
retuning. Leave the working pipeline console unchanged for this submission;
its current visibility and CLI execution boundary are documented accurately.

For a clean source ZIP after committing:

~~~bash
git archive --format=zip --output=../customer-complaint-routing-submission.zip HEAD
~~~

That archive contains committed source/evidence/docs, not DVC model/data bytes
or the MLflow database. Supply the matching artifacts separately.

## Overall conclusion

The core proposed application and local historical AIOps lifecycle are implemented
and supported by a strong, internally consistent replay record. Final handoff
requires artifact-store access and current recovery/backup evidence. Several
broad guideline and rubric-interpretation items remain qualified. A blanket
“every rubric/guideline is completely met” or guaranteed full-mark claim would
not be supported by this snapshot.

Documentation was prepared with AI assistance against the supplied source,
records and three requirement documents. The student remains responsible for
reviewing the material, following course disclosure rules and defending the
design in the viva.
