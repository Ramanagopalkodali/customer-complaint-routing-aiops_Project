# User manual

## Open the application

With both services running, open http://127.0.0.1:8501 in the VM browser.

## One complaint

1. Open One complaint.
2. Paste a complaint containing 10-10,000 characters.
3. Select Recommend a team.
4. Read the product, confidence and assigned team.
5. If Human review appears, a person must choose the final destination.

Supported products: bank accounts, credit cards, credit reporting,
debt collection and mortgages. Confidence is an estimate, not a guarantee.

## CSV upload

1. Open CSV upload and download the sample template.
2. Prepare a UTF-8 CSV with exactly one column named text.
3. Include 1-100 complaints, each containing 10-10,000 characters.
4. Keep the file within 1 MiB.
5. Upload it and select Route complaints.
6. Review the results and download the routing CSV.

Correct reported input errors and upload again. Invalid complaints cause
the entire batch to be rejected.

## Understand results

Recommended team is the suggested product team. Assigned team is either
that team or Human review. Review flags require a person's decision.

Successful prediction responses are saved automatically without complaint
text. Batch results can also be downloaded.

## Pipeline screen

Open Pipeline to inspect the workflow, saved throughput, model comparison,
test outcomes and available failure entries. Refresh pipeline evidence
updates the snapshot. It does not start training or show live task progress.

## Troubleshooting

If the service is unavailable, ask the operator to check the backend.
For input errors, check text length, CSV columns, row count and file size.
Use synthetic examples for screenshots.
