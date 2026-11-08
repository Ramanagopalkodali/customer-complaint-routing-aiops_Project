"""Read CFPB archives with Ray and build chronological, deduplicated datasets.

Original archives remain unchanged. Only narrative text is a model input;
product is the target. IDs and dates are retained for auditing and splitting.
"""
import csv
import hashlib
import io
import json
import logging
import tempfile
import time
from collections import Counter
from contextlib import ExitStack
from datetime import date
from pathlib import Path
from zipfile import ZipFile

import ray

ROOT = Path(__file__).resolve().parents[1]
LABELS = {
    "Credit reporting or other personal consumer reports": "credit_reporting",
    "Debt collection": "debt_collection",
    "Credit card": "credit_card",
    "Checking or savings account": "bank_account",
    "Mortgage": "mortgage",
}
SOURCES = [
    ("cfpb_2024_04_07.zip", "2024-04-01", "2024-07-31", ["train"]),
    ("cfpb_2024_08_10.zip", "2024-08-01", "2024-10-31",
     ["validation", "test"]),
    ("cfpb_2024_11_12.zip", "2024-11-01", "2024-12-31", ["future"]),
]
FIELDS = ["complaint_id", "date_received", "text", "label"]
SPLITS = ["train", "validation", "test", "future"]


def choose_split(received):
    """Assign a validated ISO date to a fixed chronological split."""
    if received <= "2024-07-31":
        return "train"
    if received <= "2024-09-30":
        return "validation"
    if received <= "2024-10-31":
        return "test"
    return "future"


@ray.remote(num_cpus=1)
def read_archive(filename, start, end, splits, staging):
    """Stream one archive into candidate files without returning text via Ray."""
    csv.field_size_limit(10 * 1024 * 1024)
    counts = Counter()
    path = ROOT / "data" / "raw" / filename
    with ExitStack() as stack:
        writers = {}
        for split in splits:
            handle = stack.enter_context(
                open(Path(staging) / f"{split}_candidate.csv",
                     "w", encoding="utf-8", newline="")
            )
            writer = csv.DictWriter(handle, fieldnames=FIELDS)
            writer.writeheader()
            writers[split] = writer

        archive = stack.enter_context(ZipFile(path))
        members = [n for n in archive.namelist() if n.lower().endswith(".csv")]
        if len(members) != 1:
            raise ValueError(f"{filename}: expected exactly one CSV")
        raw = stack.enter_context(archive.open(members[0]))
        text_stream = stack.enter_context(
            io.TextIOWrapper(raw, encoding="utf-8-sig", newline="")
        )
        reader = csv.DictReader(text_stream)
        required = {
            "Complaint ID", "Date received", "Product",
            "Consumer complaint narrative",
        }
        if not required.issubset(reader.fieldnames or []):
            raise ValueError(f"{filename}: required columns missing")

        for row in reader:
            counts["input_rows"] += 1
            label = LABELS.get((row["Product"] or "").strip())
            if label is None:
                counts["excluded_product"] += 1
                continue
            narrative = " ".join(
                (row["Consumer complaint narrative"] or "").split()
            )
            if not narrative:
                counts["missing_narrative"] += 1
                continue
            complaint_id = (row["Complaint ID"] or "").strip()
            if not complaint_id:
                counts["missing_id"] += 1
                continue
            received = (row["Date received"] or "").strip()
            if date.fromisoformat(received).isoformat() != received:
                raise ValueError(f"{filename}: unexpected date format")
            if not start <= received <= end:
                raise ValueError(f"{filename}: date outside expected period")
            split = choose_split(received)
            writers[split].writerow({
                "complaint_id": complaint_id,
                "date_received": received,
                "text": narrative,
                "label": label,
            })
            counts["candidate_rows"] += 1

    return filename, dict(counts)


def build_datasets(staging):
    """Deduplicate in split order so later sets cannot repeat earlier text."""
    seen_ids = set()
    seen_text = set()
    summary = {}
    for split in SPLITS:
        counts = Counter()
        classes = Counter()
        earliest = latest = None
        candidate = Path(staging) / f"{split}_candidate.csv"
        output = Path(staging) / f"{split}.csv"
        with candidate.open(encoding="utf-8", newline="") as source, \
                output.open("w", encoding="utf-8", newline="") as target:
            writer = csv.DictWriter(target, fieldnames=FIELDS)
            writer.writeheader()
            for row in csv.DictReader(source):
                counts["candidate_rows"] += 1
                digest = hashlib.sha256(
                    row["text"].casefold().encode("utf-8")
                ).digest()
                duplicate_id = row["complaint_id"] in seen_ids
                duplicate_text = digest in seen_text
                seen_ids.add(row["complaint_id"])
                seen_text.add(digest)
                if duplicate_id or duplicate_text:
                    counts["duplicates_removed"] += 1
                    continue
                writer.writerow(row)
                counts["output_rows"] += 1
                classes[row["label"]] += 1
                received = row["date_received"]
                earliest = min(earliest, received) if earliest else received
                latest = max(latest, received) if latest else received

        if set(classes) != set(LABELS.values()):
            raise ValueError(f"{split}: one or more target classes absent")
        summary[split] = {
            **dict(counts), "class_counts": dict(sorted(classes.items())),
            "date_min": earliest, "date_max": latest,
        }
        logging.info("%s: %s", split, summary[split])

    for earlier, later in zip(SPLITS, SPLITS[1:]):
        if summary[earlier]["date_max"] >= summary[later]["date_min"]:
            raise ValueError("Chronological split boundaries overlap")
    return summary


def main():
    """Run ingestion, validate outputs, and save measured execution results."""
    (ROOT / "logs").mkdir(exist_ok=True)
    (ROOT / "reports").mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(ROOT / "logs" / "ingestion.log", mode="w"),
        ],
    )
    started = time.perf_counter()
    report_path = ROOT / "reports" / "ingestion_summary.json"
    report_path.unlink(missing_ok=True)
    try:
        logging.info("START: Ray archive reading; two CPU workers")
        ray.init(num_cpus=2, include_dashboard=False)
        with tempfile.TemporaryDirectory(
            prefix="ingestion_", dir=ROOT / "data"
        ) as staging:
            pending = [
                read_archive.remote(*source, staging) for source in SOURCES
            ]
            source_stats = {}
            while pending:
                ready, pending = ray.wait(pending, num_returns=1)
                name, counts = ray.get(ready[0])
                source_stats[name] = counts
                logging.info("Archive complete: %s %s", name, counts)

            logging.info("Deduplicating and checking chronological splits")
            split_stats = build_datasets(staging)
            output_dir = ROOT / "data" / "processed"
            output_dir.mkdir(exist_ok=True)
            for split in SPLITS:
                (Path(staging) / f"{split}.csv").replace(
                    output_dir / f"{split}.csv"
                )

        elapsed = time.perf_counter() - started
        total = sum(s["input_rows"] for s in source_stats.values())
        report = {
            "status": "PASS",
            "sources": source_stats,
            "splits": split_stats,
            "duration_seconds": round(elapsed, 3),
            "input_rows_per_second": round(total / elapsed, 2),
            "throughput_scope": "whole pipeline including Ray startup",
            "deduplication": "complaint ID and case-insensitive whitespace-normalized text",
        }
        report_path.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        logging.info("PASS: %s rows checked in %.2f seconds; %.2f rows/sec",
                     f"{total:,}", elapsed, total / elapsed)
        logging.info("Saved report: %s", report_path)
    except Exception:
        logging.exception("Ingestion FAILED")
        raise
    finally:
        ray.shutdown()


if __name__ == "__main__":
    main()
