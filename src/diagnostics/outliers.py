"""IQR numeric outlier diagnostic."""

import pandas as pd
import numpy as np


def outlier_check(frame: pd.DataFrame) -> dict:
    numeric = frame.select_dtypes(include="number")
    if numeric.empty or len(numeric.columns) == 0:
        return {"status": "skipped", "tool": "outlier_check", "summary": "No numeric columns to assess.",
                "data": {}, "findings": []}
    results, findings = [], []
    for column in numeric.columns:
        values = numeric[column].replace([np.inf, -np.inf], np.nan).dropna()
        if len(values) < 4:
            continue
        q1, q3 = values.quantile([0.25, 0.75])
        iqr = q3 - q1
        lower, upper = float(q1 - 1.5 * iqr), float(q3 + 1.5 * iqr)
        count = int(((values < lower) | (values > upper)).sum())
        pct = round(count * 100 / len(values), 2)
        results.append({"column": str(column), "outlier_count": count, "outlier_pct": pct,
                        "lower_bound": round(lower, 4), "upper_bound": round(upper, 4),
                        "non_null_count": int(len(values))})
        if count:
            findings.append({"issue": "IQR outliers", "severity": "medium", "column": str(column),
                             "evidence": f"{count}/{len(values)} values outside [{lower:.4g}, {upper:.4g}] ({pct}%)",
                             "impact": "Extreme values may affect some models or preprocessing steps; they can also be valid.",
                             "recommendation": "Inspect these observations and the domain before any capping or removal."})
    return {"status": "ok", "tool": "outlier_check", "summary": f"{len(findings)} numeric columns have IQR outliers.",
            "data": {"columns": results, "method": "1.5 x IQR"}, "findings": findings}
