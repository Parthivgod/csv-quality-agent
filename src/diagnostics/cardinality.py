"""Identifier-like high-cardinality feature diagnostic."""

import re

import pandas as pd


def _identifier_named(column: str) -> bool:
    """Treat numeric fields as IDs only when their names suggest identifiers."""
    name = str(column).lower()
    return bool(re.search(r"(^|_)(id|key|uuid|code)($|_)", name) or "identifier" in name)


def high_cardinality_check(frame: pd.DataFrame, ratio: float = 0.90, min_non_null: int = 20) -> dict:
    candidates, findings = [], []
    for column in frame.columns:
        if pd.api.types.is_numeric_dtype(frame[column]) and not _identifier_named(str(column)):
            continue
        non_null = int(frame[column].notna().sum())
        if non_null < min_non_null:
            continue
        unique = int(frame[column].nunique(dropna=True))
        unique_ratio = round(unique / non_null, 4)
        if unique_ratio < ratio:
            continue
        candidates.append({"column": str(column), "unique_count": unique,
                           "non_null_count": non_null, "unique_ratio": unique_ratio,
                           "possible_interpretation": "Potential identifier-like or high-cardinality feature; review context."})
        findings.append({"issue": "High-cardinality feature", "severity": "low", "column": str(column),
                         "evidence": f"{unique}/{non_null} non-null values unique (ratio {unique_ratio})",
                         "impact": "Identifiers may encourage memorization or misleading numeric ordering; categories can expand encodings.",
                         "recommendation": "Determine whether the field is an identifier or useful predictor before changing it."})
    return {"status": "ok", "tool": "high_cardinality_check",
            "summary": f"{len(candidates)} potential high-cardinality columns.",
            "data": {"candidates": candidates, "ratio_threshold": ratio, "min_non_null": min_non_null},
            "findings": findings}
