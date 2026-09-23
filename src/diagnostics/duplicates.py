"""Exact duplicate-row diagnostic."""

import pandas as pd


def duplicate_rows_check(frame: pd.DataFrame) -> dict:
    count = int(frame.duplicated().sum())
    pct = round(100 * count / len(frame), 2) if len(frame) else 0.0
    findings = ([{"issue": "Duplicate rows", "severity": "medium", "column": None,
                  "evidence": f"{count}/{len(frame)} rows duplicate earlier rows ({pct}%)",
                  "impact": "Repeated observations may overweight patterns; some repeats may be legitimate.",
                  "recommendation": "Review duplicate records in domain context before deduplication."}] if count else [])
    return {"status": "ok", "tool": "duplicate_rows_check",
            "summary": f"{count} duplicate rows ({pct}%). Contextual review is needed.",
            "data": {"duplicate_count": count, "duplicate_pct": pct}, "findings": findings}
