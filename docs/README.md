# Project documentation

Author: Ramana Gopal Kodali, DA24B010.
Reference snapshot: 12 November 2026; Customer Complaint Routing System with AIOps.

| Mandatory document | File |
|---|---|
| Architecture diagram and block explanations | [architecture.md](architecture.md) |
| High-level design, choices and rationale | [high_level_design.md](high_level_design.md) |
| Low-level design, endpoints and I/O | [low_level_design.md](low_level_design.md) |
| Test plan, acceptance criteria and results | [test_plan_and_report.md](test_plan_and_report.md) |
| Test-case catalogue, all 77 recorded cases | [test_cases.md](test_cases.md) |
| Non-technical user manual | [user_manual.md](user_manual.md) |

The test plan and case catalogue together satisfy the fourth mandatory item.

| Supporting document | Use |
|---|---|
| [workflow_and_files.md](workflow_and_files.md) | Data-to-deployment sequence and which file does what |
| [rubric_compliance.md](rubric_compliance.md) | Answers to every evaluation-rubric question |
| [rubric_file_map.md](rubric_file_map.md) | Code/evidence grouped by Demonstration, Software Engineering, AIOps and Viva |
| [model_development.md](model_development.md) | Dataset, models, thresholds and recorded numerical outcomes |
| [deployment.md](deployment.md) | Runtime, artifacts, rollback and recovery |
| [development_guidelines.md](development_guidelines.md) | Guideline assessment and qualified limitations |
| [proposal_compliance.md](proposal_compliance.md) | Submitted GForm promises matched to implementation |
| [audit_findings.md](audit_findings.md) | Independent audit, current versus historical proof and remaining actions |
| [references.md](references.md) | Requirement documents and official tool references |

Use the [root README](../README.md) for existing startup, test and replay commands.
Use the [evidence index](../evidence/README.md) for screenshot paths and the
machine-readable reports that establish the latest run.

The supplied full-suite XML records **77 passing cases** for candidate
`caa8bd53da5f4fb1871725b08a80ec70`. Available source syntax, DVC file hashes,
report links and saved prediction metrics were independently checked. The raw
datasets, model binaries and tracking database are excluded from the Git ZIP;
the documentation audit did not execute those unavailable assets. Recorded VM
reports establish the runtime results.

This delivery contains Markdown only. It modifies no implementation, test,
Docker, DVC or monitoring files, creates no new setup scripts, moves no images
and runs no training. Retain a copy of replaced documents outside the repository
if you want a pre-update snapshot. The current screen is documented as an
interactive evidence console with execution through existing CLI commands.
