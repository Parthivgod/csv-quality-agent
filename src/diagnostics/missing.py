"""Missing-value diagnostic."""

import pandas as pd


def missing_values_check(frame: pd.DataFrame, medium_pct: float = 5, high_pct: float = 30) -> dict:
    rows = len(frame)
    affected = []
    findings = []
    for column in frame.columns:
        count = int(frame[column].isna().sum())
        if not count:
            continue
        pct = round(count * 100 / rows, 2) if rows else 0.0
        severity = "high" if pct > high_pct else "medium" if pct >= medium_pct else "low"
        affected.append({"column": str(column), "missing_count": count, "missing_pct": pct, "severity": severity})
        findings.append({"issue": "Missing values", "severity": severity, "column": str(column),
                         "evidence": f"{count}/{rows} values missing ({pct}%)",
                         "impact": "Training may fail or estimates may be biased without appropriate handling.",
                         "recommendation": "Investigate why values are missing, then choose justified imputation or removal."})
    return {"status": "ok", "tool": "missing_values_check",
            "summary": f"{len(affected)} columns contain missing values.",
            "data": {"affected_columns": affected, "thresholds_pct": {"medium": medium_pct, "high": high_pct}},
            "findings": findings}
