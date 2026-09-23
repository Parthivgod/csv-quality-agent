"""Regenerate deterministic teaching fixtures and known-issue manifests."""

import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SAMPLES = ROOT / "data" / "samples"
EXPECTED = ROOT / "data" / "expected"


def write(name: str, rows: list[dict], expected: dict | None = None) -> None:
    pd.DataFrame(rows).to_csv(SAMPLES / f"{name}.csv", index=False)
    if expected:
        (EXPECTED / f"{name}.json").write_text(json.dumps(expected, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    SAMPLES.mkdir(parents=True, exist_ok=True)
    EXPECTED.mkdir(parents=True, exist_ok=True)
    write("clean_small", [
        {"age": 22 + i % 6, "study_hours": 2 + i % 4, "group": ["A", "B", "C"][i % 3],
         "label": ["pass", "fail"][i % 2]} for i in range(12)
    ])

    rows = [{"age": None if i in {2, 5, 8, 11, 14, 17} else 20 + i,
             "income": None if i in {4, 10, 16} else 30000 + 1000 * i,
             "city": ["Pune", "Mumbai", "Delhi"][i % 3], "constant_feature": "same"}
            for i in range(28)]
    rows.extend([rows[3].copy(), rows[7].copy()])
    write("corrupted_missing_duplicates", rows, {
        "expected_issues": ["missing_values", "duplicates", "constant_column"],
        "expected_columns": {"missing_values": ["age", "income"], "constant_column": ["constant_feature"]},
        "expected_counts": {"duplicates": 2, "age_missing": 6, "income_missing": 3}
    })

    write("corrupted_class_imbalance", [
        {"record_id": f"R{i:03d}", "feature_a": i % 9, "feature_b": (i * 7) % 13,
         "label": "positive" if i >= 90 else "negative"} for i in range(100)
    ], {"expected_issues": ["class_imbalance", "high_cardinality"],
        "expected_columns": {"class_imbalance": ["label"], "high_cardinality": ["record_id"]},
        "expected_counts": {"negative": 90, "positive": 10}})

    values = list(range(1, 30)) + [200]
    write("corrupted_outliers_corr", [
        {"feature_x": x, "feature_y": 2 * x + 1, "feature_z": (i * 3) % 11}
        for i, x in enumerate(values)
    ], {"expected_issues": ["outliers", "high_correlation"],
        "expected_columns": {"outliers": ["feature_x", "feature_y"],
                             "high_correlation": ["feature_x", "feature_y"]}})


if __name__ == "__main__":
    main()
