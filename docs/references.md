# Requirements and technical references

## Supplied requirements used in this audit

1. **AI Application Evaluation Guideline (1).pdf**, pages 1–2:
   demonstration, software engineering, AIOps implementation, viva and five
   mandatory documents.
2. **AI Application Development Guidelines.pdf**, pages 1–3:
   core principles, lifecycle framework, local-only stack and best practices.
3. **aiops_project .pdf**, pages 1–3:
   submitted Google Forms receipt, “Customer Complaint Routing System with
   AIOps”, Ramana Gopal Kodali, DA24B010, 5 October 2026.

These PDFs were read during preparation. They are named here for traceability;
this repository does not claim that private ChatGPT links give evaluators access.
Retain the original course/proposal documents with the academic submission
according to the instructor's instructions.

## Implementation sources of truth

The current source code, `dvc.yaml`/`dvc.lock`, saved OpenAPI schema, test XML,
replay logs, report hash chain and prediction CSVs establish the implementation.
Design text describes this actual implementation rather than treating a
framework recommendation as already implemented.

## Primary technical references

- [CFPB public complaint database](https://www.consumerfinance.gov/data-research/consumer-complaints/)
- [DVC reproduction](https://dvc.org/doc/command-reference/repro)
- [DVC manually completed output registration](https://dvc.org/doc/command-reference/commit)
- [DVC frozen stages](https://dvc.org/doc/command-reference/freeze)
- [DVC ignore files](https://dvc.org/doc/user-guide/project-structure/dvcignore-files)
- [MLflow local serving](https://mlflow.org/docs/latest/ml/deployment/deploy-model-locally/)
- [MLflow CLI](https://mlflow.org/docs/latest/api_reference/cli.html)
- [Git attributes and checkout conversion](https://git-scm.com/docs/gitattributes)

The technical links support usage of the tools. They are not assertions that
code was copied from a particular course example or that an unexecuted optional
command already passed. Package versions remain pinned by the project.
