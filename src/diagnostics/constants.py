"""Constant and near-constant feature diagnostic."""

import pandas as pd


def constant_columns_check(frame: pd.DataFrame, near_ratio: float = 0.95) -> dict:
    constants, near_constants, findings = [], [], []
    for column in frame.columns:
        counts = frame[column].value_counts(dropna=False)
        unique = int(frame[column].nunique(dropna=False))
        dominant_ratio = round(float(counts.iloc[0] / len(frame)), 4) if len(frame) else 0.0
        item = {"column": str(column), "unique_count_including_null": unique,
                "dominant_ratio": dominant_ratio}
        if unique <= 1:
            constants.append(item)
            kind, severity = "Constant column", "medium"
        elif dominant_ratio >= near_ratio:
            near_constants.append(item)
            kind, severity = "Near-constant column", "low"
        else:
            continue
        findings.append({"issue": kind, "severity": severity, "column": str(column),
                         "evidence": f"{unique} distinct values including null; dominant fraction {dominant_ratio:.2%}",
                         "impact": "This feature may provide little predictive information.",
                         "recommendation": "Review its role before excluding it from model inputs."})
    return {"status": "ok", "tool": "constant_columns_check",
            "summary": f"{len(constants)} constant and {len(near_constants)} near-constant columns.",
            "data": {"constant_columns": constants, "near_constant_columns": near_constants,
                     "near_constant_threshold": near_ratio}, "findings": findings}
