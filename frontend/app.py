"""Support-agent frontend; all inference happens through configurable REST calls."""
import io
import os

import pandas as pd
import requests
import streamlit as st

API_URL = os.environ.get("API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
PRODUCTS = {
    "bank_account": "Checking or savings account",
    "credit_card": "Credit card",
    "credit_reporting": "Credit reporting",
    "debt_collection": "Debt collection",
    "mortgage": "Mortgage",
}

st.set_page_config(
    page_title="Complaint Routing",
    page_icon="📬",
    layout="wide",
)
st.title("Customer Complaint Routing")
st.caption(
    "Identify the product, suggest a support team, and flag complaints "
    "that need a person to review them."
)


def call_backend(endpoint, payload):
    """Show actionable errors without exposing internal exception details."""
    try:
        response = requests.post(
            f"{API_URL}{endpoint}", json=payload, timeout=60
        )
        if response.status_code == 422:
            st.error(
                "The input was rejected. Each complaint must contain "
                "10–10,000 characters; a batch may contain 1–100 complaints."
            )
            return None
        response.raise_for_status()
        return response.json()
    except requests.Timeout:
        st.error("The prediction request timed out. Please try again.")
    except requests.ConnectionError:
        st.error("The prediction service is unavailable. Check that it is running.")
    except (requests.RequestException, ValueError):
        st.error("The prediction service could not complete the request.")
    return None


def results_table(results):
    """Use readable labels and percentages for display and CSV export."""
    frame = pd.DataFrame(results)
    frame["product"] = frame["product"].map(PRODUCTS)
    frame["confidence_percent"] = (frame.pop("confidence") * 100).round(2)
    return frame


single_tab, batch_tab, pipeline_tab, help_tab = st.tabs(
    ["One complaint", "CSV upload", "Pipeline", "How to use"]
)

with single_tab:
    with st.form("single_complaint"):
        text = st.text_area(
            "Complaint",
            height=180,
            max_chars=10000,
            placeholder="Paste a banking or financial-product complaint here.",
        )
        submitted = st.form_submit_button("Recommend a team", type="primary")

    if submitted:
        cleaned = text.strip()
        if len(cleaned) < 10:
            st.warning("Enter a complaint containing at least 10 characters.")
        else:
            with st.spinner("Reading the complaint…"):
                result = call_backend("/predict", {"text": cleaned})
            if result is not None:
                left, middle, right = st.columns(3)
                left.metric("Product", PRODUCTS[result["product"]])
                middle.metric("Confidence", f"{result['confidence']:.1%}")
                right.metric("Assigned team", result["assigned_team"])
                if result["human_review"]:
                    reasons = {
                        "low_confidence": "Confidence is below this category's threshold.",
                        "unrecognized_text": "The model could not recognize the text.",
                        "category_requires_review": "This category requires manual review.",
                    }
                    st.warning(
                        "Human review required. "
                        + reasons.get(result["review_reason"], "")
                    )
                    st.write("Suggested product team:", result["recommended_team"])
                else:
                    st.success("The complaint can be routed to the assigned team.")
                st.caption(
                    "Confidence is an estimate, not a guarantee. "
                    "A person should check unusual or unrelated complaints."
                )

with batch_tab:
    st.write(
        "Upload a UTF-8 CSV with exactly one column named `text`. "
        "Maximum: 100 complaints and 1 MiB."
    )
    template = pd.DataFrame({
        "text": [
            "My credit card was charged twice for the same purchase.",
            "My mortgage payment was not credited to my loan account.",
        ]
    })
    st.download_button(
        "Download sample CSV",
        template.to_csv(index=False),
        file_name="complaints_template.csv",
        mime="text/csv",
    )
    uploaded = st.file_uploader("Complaint CSV", type=["csv"])
    if uploaded is not None:
        content = uploaded.getvalue()
        if st.session_state.get("uploaded_content") != content:
            st.session_state["uploaded_content"] = content
            st.session_state.pop("batch_results", None)

        if st.button("Route complaints", type="primary"):
            try:
                if len(content) > 1024 * 1024:
                    raise ValueError("The CSV exceeds the 1 MiB limit.")
                frame = pd.read_csv(
                    io.BytesIO(content), dtype=str,
                    keep_default_na=False, encoding="utf-8-sig",
                )
                if list(frame.columns) != ["text"]:
                    raise ValueError("The CSV must have exactly one column: text.")
                if not 1 <= len(frame) <= 100:
                    raise ValueError("Upload between 1 and 100 complaints.")
                texts = frame["text"].str.strip()
                invalid = ~texts.str.len().between(10, 10000)
                if invalid.any():
                    rows = (frame.index[invalid] + 2).tolist()
                    raise ValueError(
                        f"CSV row(s) {rows}: text must contain 10–10,000 characters."
                    )
                with st.spinner("Routing complaints…"):
                    response = call_backend(
                        "/predict-batch", {"texts": texts.tolist()}
                    )
                if response is not None:
                    output = results_table(response["results"])
                    output.insert(0, "csv_row", range(2, len(output) + 2))
                    st.session_state["batch_results"] = output
            except (ValueError, UnicodeError, pd.errors.ParserError) as exc:
                st.error(str(exc))

        if "batch_results" in st.session_state:
            output = st.session_state["batch_results"]
            st.success(f"Processed {len(output)} complaints.")
            st.dataframe(output, hide_index=True, use_container_width=True)
            st.download_button(
                "Download routing results",
                output.to_csv(index=False),
                file_name="routing_results.csv",
                mime="text/csv",
            )

with help_tab:
    st.markdown("""
1. Choose **One complaint** or **CSV upload**.
2. Enter a complaint about one of the five supported financial products.
3. Select **Recommend a team** or **Route complaints**.
4. Check the assigned team and any human-review message.
5. For a batch, download the results CSV.

**Supported products:** bank accounts, credit cards, credit reporting,
debt collection, and mortgages.

**Human review:** the suggested category is provisional when review is
required. A support agent must decide the final destination.

**Confidence:** an estimated probability from the model. It does not
guarantee correctness or establish whether a complaint is in scope.
""")


@st.cache_data(ttl=15, show_spinner=False)
def fetch_pipeline():
    response = requests.get(f"{API_URL}/pipeline", timeout=30)
    response.raise_for_status()
    return response.json()


with pipeline_tab:
    import base64

    st.subheader("Pipeline console")
    st.caption(
        "Review saved execution evidence and the current DVC workspace status. "
        "This screen does not start training jobs."
    )
    if st.button("Refresh pipeline evidence"):
        fetch_pipeline.clear()
    try:
        with st.spinner("Loading pipeline evidence…"):
            snapshot = fetch_pipeline()
        st.write("DVC workspace:", snapshot["workspace_status"])
        st.caption("Snapshot: " + snapshot["generated_at"])
        st.image(
            base64.b64decode(snapshot["diagram_png_base64"]),
            caption="Dependencies from the repository's DVC configuration",
        )
        if snapshot["workspace_changes"]:
            with st.expander("Workspace changes"):
                st.json(snapshot["workspace_changes"])

        ingestion = snapshot.get("ingestion")
        if ingestion:
            first, second = st.columns(2)
            first.metric(
                "Ingestion throughput",
                f"{ingestion['input_rows_per_second']:,.0f} rows/sec",
            )
            second.metric(
                "Ingestion duration",
                f"{ingestion['duration_seconds']:.2f} sec",
            )
            st.caption(ingestion["throughput_scope"])
            rows = [
                {"split": name, "rows": details["output_rows"],
                 "start": details["date_min"], "end": details["date_max"]}
                for name, details in ingestion["splits"].items()
            ]
            st.dataframe(pd.DataFrame(rows), hide_index=True)

        st.subheader("Model comparison")
        if snapshot["models"]:
            rows = [
                {"model": name,
                 "validation_macro_f1": result["validation_macro_f1"],
                 "validation_accuracy": result["validation_accuracy"],
                 "MLflow_run": result["run_id"]}
                for name, result in snapshot["models"].items()
            ]
            st.dataframe(pd.DataFrame(rows), hide_index=True)
            st.write("Original validation-selected model type:", snapshot["selected_model"])

        st.subheader("Currently loaded model")
        st.code(snapshot.get("active_model_version") or "Unavailable")
        st.caption("Identity reported by the running backend model service.")

        lifecycle = snapshot.get("lifecycle", {})
        monitoring = lifecycle.get("monitoring")
        if monitoring:
            st.subheader("Historical November monitoring")
            st.json({
                "period": monitoring.get("period"),
                "model_run": monitoring.get("provenance", {}).get(
                    "champion_training_run_id"
                ),
                "metrics": monitoring.get("metrics"),
                "retraining_required": monitoring.get("retraining_required"),
            })

        acceptance = lifecycle.get("acceptance")
        if acceptance:
            st.subheader("Historical candidate acceptance")
            st.json({
                "decision": acceptance.get("decision"),
                "selected_run": acceptance.get("selected_run_id"),
                "checks": acceptance.get("checks"),
            })

        final = lifecycle.get("final")
        if final:
            st.subheader("Reserved December evaluation")
            st.caption(
                "Saved evaluation of model " +
                str(final.get("selected_training_run_id"))
            )
            if not snapshot.get("final_evaluation_matches_active_model"):
                st.warning(
                    "This saved evaluation belongs to a different model "
                    "from the currently loaded model."
                )
            st.json(final.get("metrics", {}))

        runner = lifecycle.get("runner")
        if runner:
            st.subheader("Last conditional lifecycle run")
            st.json({
                "status": runner.get("status"),
                "outcome": runner.get("outcome"),
                "active_model_after_run": runner.get("final_active_model_version"),
            })
            st.caption(
                "Saved historical workflow result; this screen does not "
                "start retraining or continuously monitor new batches."
            )

        if snapshot.get("test"):
            st.subheader("Historical October evaluation — original model")
            st.json(snapshot["test"]["metrics"])

        st.subheader("Saved test reports")
        st.dataframe(pd.DataFrame(snapshot["tests"]), hide_index=True)
        st.subheader("Recorded pipeline failures")
        if snapshot["recorded_failures"]:
            st.dataframe(
                pd.DataFrame(snapshot["recorded_failures"]), hide_index=True
            )
        else:
            st.info("No failure entries found in the available pipeline logs.")
        if snapshot["missing_logs"]:
            st.caption("Unavailable logs: " + ", ".join(snapshot["missing_logs"]))
    except (requests.RequestException, ValueError, KeyError):
        st.error(
            "Pipeline evidence is unavailable. Check the backend and retry."
        )
