"""High absolute Pearson correlation among numeric features."""

import pandas as pd
import numpy as np


def correlation_check(frame: pd.DataFrame, target: str | None = None, threshold: float = 0.95) -> dict:
    numeric = frame.select_dtypes(include="number").drop(columns=[target], errors="ignore")
    numeric = numeric.replace([np.inf, -np.inf], np.nan)
    if len(numeric.columns) < 2:
        return {"status": "skipped", "tool": "correlation_check",
                "summary": "At least two numeric feature columns are needed.", "data": {}, "findings": []}
    corr = numeric.corr()
    pairs, findings = [], []
    for i, left in enumerate(corr.columns):
        for right in corr.columns[i + 1:]:
            value = corr.loc[left, right]
            if pd.isna(value) or abs(value) < threshold:
                continue
            rounded = round(float(value), 4)
            pairs.append({"left": str(left), "right": str(right), "correlation": rounded})
            findings.append({"issue": "Strong feature correlation", "severity": "medium", "column": f"{left}, {right}",
                             "evidence": f"Pearson r({left}, {right}) = {rounded}",
                             "impact": "Possible redundancy or leakage candidate; correlation alone does not prove leakage.",
                             "recommendation": "Review feature provenance and model assumptions before dropping either feature."})
    return {"status": "ok", "tool": "correlation_check",
            "summary": f"{len(pairs)} numeric feature pairs meet |r| >= {threshold}.",
            "data": {"pairs": pairs, "threshold": threshold}, "findings": findings}
