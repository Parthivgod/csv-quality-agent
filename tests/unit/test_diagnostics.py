import json
from pathlib import Path

import pandas as pd

from src.diagnostics.cardinality import high_cardinality_check
from src.diagnostics.constants import constant_columns_check
from src.diagnostics.correlation import correlation_check
from src.diagnostics.duplicates import duplicate_rows_check
from src.diagnostics.imbalance import class_imbalance_check
from src.diagnostics.missing import missing_values_check
from src.diagnostics.outliers import outlier_check
from src.diagnostics.profile import dataset_profile


def fixture(name: str) -> tuple[pd.DataFrame, dict]:
    frame = pd.read_csv(Path("data/samples") / f"{name}.csv")
    expected = json.loads((Path("data/expected") / f"{name}.json").read_text())
    return frame, expected


def test_missing_duplicates_constants_match_manifest() -> None:
    frame, expected = fixture("corrupted_missing_duplicates")
    missing = missing_values_check(frame)
    counts = {item["column"]: item["missing_count"] for item in missing["data"]["affected_columns"]}
    assert list(counts) == expected["expected_columns"]["missing_values"]
    assert counts == {"age": expected["expected_counts"]["age_missing"],
                      "income": expected["expected_counts"]["income_missing"]}
    assert duplicate_rows_check(frame)["data"]["duplicate_count"] == expected["expected_counts"]["duplicates"]
    assert [x["column"] for x in constant_columns_check(frame)["data"]["constant_columns"]] == expected["expected_columns"]["constant_column"]


def test_class_imbalance_and_cardinality_match_manifest() -> None:
    frame, expected = fixture("corrupted_class_imbalance")
    imbalance = class_imbalance_check(frame, "label")
    assert {x["class"]: x["count"] for x in imbalance["data"]["classes"]} == expected["expected_counts"]
    assert imbalance["data"]["majority_minority_ratio"] == 9.0
    assert [x["column"] for x in high_cardinality_check(frame)["data"]["candidates"]] == expected["expected_columns"]["high_cardinality"]


def test_outliers_and_correlation_match_manifest() -> None:
    frame, expected = fixture("corrupted_outliers_corr")
    outliers = outlier_check(frame)
    flagged = [x["column"] for x in outliers["data"]["columns"] if x["outlier_count"]]
    assert flagged == expected["expected_columns"]["outliers"]
    assert all(x["outlier_count"] == 1 for x in outliers["data"]["columns"] if x["column"] in flagged)
    pairs = correlation_check(frame)["data"]["pairs"]
    assert [(x["left"], x["right"]) for x in pairs] == [("feature_x", "feature_y")]
    assert pairs[0]["correlation"] == 1.0


def test_skipped_cases_and_json_serializability() -> None:
    frame = pd.DataFrame({"name": ["a", "b", "c"], "label": ["x", "x", "x"]})
    assert outlier_check(frame)["status"] == "skipped"
    assert correlation_check(frame)["status"] == "skipped"
    assert class_imbalance_check(frame, None)["status"] == "skipped"
    assert class_imbalance_check(frame, "label")["status"] == "skipped"
    for function in (dataset_profile, missing_values_check, duplicate_rows_check,
                     constant_columns_check, high_cardinality_check):
        json.dumps(function(frame))


def test_clean_missing_and_duplicates() -> None:
    frame = pd.read_csv("data/samples/clean_small.csv")
    assert not missing_values_check(frame)["findings"]
    assert duplicate_rows_check(frame)["data"]["duplicate_count"] == 0


def test_high_cardinality_ignores_continuous_numeric_features() -> None:
    frame = pd.DataFrame({"age": list(range(25)), "income": list(range(100, 125)),
                          "student_id": list(range(25)),
                          "record_code": [f"R{i}" for i in range(25)]})
    candidates = high_cardinality_check(frame)["data"]["candidates"]
    assert [item["column"] for item in candidates] == ["student_id", "record_code"]
