# User manual

## What the application does

Complaint Routing helps a support agent choose a team for a financial complaint.
It recognises bank-account, credit-card, credit-reporting, debt-collection and
mortgage complaints. It displays a product, estimated confidence and assigned
team. A review flag means a person must decide the final destination.

The application recommends a destination; it does not send a complaint to a
department or create a ticket. It does not determine whether the customer's
claim is valid.

## Open the application

Ask the operator to start the application using the root README. In the
**Ubuntu VM browser**, open http://127.0.0.1:8501.
The page has four tabs: **One complaint**, **CSV upload**, **Pipeline** and
**How to use**. The same address in the Mac/Windows host browser refers to that
host, so use the VM browser unless the operator has configured a tunnel.

## Route one complaint

1. Choose **One complaint**.
2. Paste a complaint about a supported financial product.
3. Enter 10–10,000 characters; avoid including passwords/account identifiers.
4. Select **Recommend a team** and wait for the spinner to finish.
5. Read Product, Confidence and Assigned team.
6. Follow any **Human review required** message.

A useful synthetic example is:
“My credit card was charged twice for the same purchase.”
The result depends on the loaded model; an example is not a promise that a
particular complaint will always be automatically routed.

## Interpret the result

| Display | Meaning/action |
|---|---|
| Product | The model's predicted financial-product category |
| Confidence | An estimate expressed as a percentage, not a guarantee |
| Assigned team | The recommended product team or Human review |
| Human review: low confidence | The category-specific threshold was not reached |
| Human review: unrecognised text | The model found no usable vocabulary |
| Human review: category requires review | Automatic routing is disabled for that category |
| Suggested product team | A provisional recommendation for the person reviewing the case |

Check unusual, unclear, multilingual or unrelated complaints manually even if
confidence looks high. Recognised words do not prove that an input is in scope.
During human review, use your organisation's normal procedure to select the
final team; this demonstration has no review-resolution workflow.

## Route a CSV

1. Choose **CSV upload** and select **Download sample CSV**.
2. Keep exactly one column named `text`.
3. Put one complaint in each record, using 10–10,000 characters.
4. Save as UTF-8 CSV, with 1–100 complaints and a file size at most 1 MiB.
5. Upload the file and select **Route complaints**.
6. Read the table and review any flagged records.
7. Select **Download routing results** to keep a local CSV.

Example file:

~~~csv
text
"My credit card was charged twice for the same purchase."
"My mortgage payment was not credited to my loan account."
~~~

Use CSV quoting when text contains commas or line breaks. Do not add an index,
extra columns or an empty complaint. Correct the reported record and upload
again if validation fails. A rejected batch produces no partial successful
batch response.

The downloaded results include the CSV record number, product/team decisions,
review information, model version and confidence percentage. The input text is
not repeated in the download. Keep your original CSV if you need to match the
record number back to a complaint.

## Pipeline tab

This tab is mainly for the operator or evaluator. It displays the DVC diagram,
saved ingestion speed, model comparison, currently loaded model ID, historical
monitoring, candidate checks, December results and saved test summaries.
Select **Refresh pipeline evidence** to request a new snapshot.

This screen does not start/stop jobs or continuously score newly arriving
complaints. A saved no-trigger decision can precede a separately requested
retraining demonstration. The Current model field is the authoritative runtime
identity. A warning appears if saved December results belong to another model.

## Common problems

| Message/symptom | What to do |
|---|---|
| Complaint too short | Enter at least 10 characters after outer whitespace is removed. |
| CSV rejected | Check UTF-8 encoding, exact `text` header, size, record count and text lengths. |
| Prediction service unavailable | Ask the operator to check the backend; retain the complaint and retry later. |
| Request timed out | Retry once; report recurring delays to the operator. |
| Human review required | Ask a person to choose the destination. Do not change model thresholds through the UI. |
| Pipeline evidence unavailable | Ask the operator to check saved reports and the backend; inference may have a separate status. |
| Input changed after a batch | Press Route complaints again to compute results for the new upload. |

While a session is active, the upload is held in the Streamlit session's memory.
Backend response files and logs exclude submitted complaint text. Use synthetic
examples for screenshots and follow your organisation's data-handling rules.
The application is a local academic demonstration without login or encryption.
