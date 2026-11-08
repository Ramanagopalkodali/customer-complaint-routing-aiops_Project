"""Check chronological boundaries, leakage prevention and data quality gates."""
import csv

import pytest

from src.ingest import FIELDS, LABELS, SPLITS, build_datasets, choose_split


@pytest.mark.parametrize("received,expected", [
    ("2024-04-01", "train"),
    ("2024-07-31", "train"),
    ("2024-08-01", "validation"),
    ("2024-09-30", "validation"),
    ("2024-10-01", "test"),
    ("2024-10-31", "test"),
    ("2024-11-01", "future"),
    ("2024-12-31", "future"),
])
def test_chronological_boundaries(received, expected):
    assert choose_split(received) == expected


def write_candidates(folder, rows):
    for split, records in rows.items():
        with (folder / f"{split}_candidate.csv").open(
            "w", encoding="utf-8", newline=""
        ) as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(records)


@pytest.fixture
def candidates():
    dates = {
        "train": "2024-04-01",
        "validation": "2024-08-01",
        "test": "2024-10-01",
        "future": "2024-11-01",
    }
    return {
        split: [
            {
                "complaint_id": f"{split}-{i}",
                "date_received": dates[split],
                "text": f"{split} example {label}",
                "label": label,
            }
            for i, label in enumerate(LABELS.values())
        ]
        for split in SPLITS
    }


def test_removes_duplicate_id_across_splits(tmp_path, candidates):
    duplicate = dict(candidates["validation"][0])
    duplicate["complaint_id"] = candidates["train"][0]["complaint_id"]
    duplicate["text"] = "A different narrative with an already used ID"
    candidates["validation"].append(duplicate)
    write_candidates(tmp_path, candidates)

    summary = build_datasets(tmp_path)

    assert summary["validation"]["output_rows"] == 5
    assert summary["validation"]["duplicates_removed"] == 1
    with (tmp_path / "validation.csv").open(newline="") as handle:
        ids = {row["complaint_id"] for row in csv.DictReader(handle)}
    assert duplicate["complaint_id"] not in ids


def test_removes_repeated_text_across_splits(tmp_path, candidates):
    duplicate = dict(candidates["test"][0])
    duplicate["complaint_id"] = "different-id"
    duplicate["text"] = candidates["train"][0]["text"].upper()
    candidates["test"].append(duplicate)
    write_candidates(tmp_path, candidates)

    summary = build_datasets(tmp_path)

    assert summary["test"]["output_rows"] == 5
    assert summary["test"]["duplicates_removed"] == 1


def test_removes_repeated_text_within_split(tmp_path, candidates):
    duplicate = dict(candidates["train"][0])
    duplicate["complaint_id"] = "another-training-id"
    candidates["train"].append(duplicate)
    write_candidates(tmp_path, candidates)

    summary = build_datasets(tmp_path)

    assert summary["train"]["output_rows"] == 5
    assert summary["train"]["duplicates_removed"] == 1


def test_rejects_missing_class(tmp_path, candidates):
    candidates["validation"].pop()
    write_candidates(tmp_path, candidates)

    with pytest.raises(ValueError, match="target classes absent"):
        build_datasets(tmp_path)


def test_rejects_overlapping_dates(tmp_path, candidates):
    candidates["validation"][0]["date_received"] = "2024-04-01"
    write_candidates(tmp_path, candidates)

    with pytest.raises(ValueError, match="boundaries overlap"):
        build_datasets(tmp_path)


def test_preserves_unique_records(tmp_path, candidates):
    write_candidates(tmp_path, candidates)
    summary = build_datasets(tmp_path)

    for split in SPLITS:
        assert summary[split]["output_rows"] == 5
        with (tmp_path / f"{split}.csv").open(
            encoding="utf-8", newline=""
        ) as handle:
            assert list(csv.DictReader(handle)) == candidates[split]
