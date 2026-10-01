"""Target class distribution diagnostic."""

import pandas as pd


def class_imbalance_check(frame: pd.DataFrame, target: str | None) -> dict:
    if not target or target not in frame.columns:
        return {"status": "skipped", "tool": "class_imbalance_check",
                "summary": "Select a valid target column to assess class imbalance.", "data": {}, "findings": []}
    counts = frame[target].value_counts(dropna=True)
    if len(counts) < 2:
        return {"status": "skipped", "tool": "class_imbalance_check",
                "summary": "Target needs at least two observed classes.", "data": {}, "findings": []}
    if len(counts) > 50 or len(counts) > max(10, len(frame) * 0.2):
        return {"status": "skipped", "tool": "class_imbalance_check",
                "summary": "Selected target has too many distinct values for a class-imbalance check.",
                "data": {"unique_classes": int(len(counts))}, "findings": []}
    total = int(counts.sum())
    classes = [{"class": str(label), "count": int(count), "proportion": round(int(count) / total, 4),
                "percentage": round(int(count) / total * 100, 4)}
               for label, count in counts.items()]
    ratio = round(float(counts.iloc[0] / counts.iloc[-1]), 4)
    findings = []
    if ratio >= 3:
        findings.append({"issue": "Class imbalance", "severity": "high" if ratio >= 9 else "medium",
                         "column": target,
                         "evidence": f"Majority/minority ratio {ratio}:1; counts {classes}",
                         "impact": "A classifier can favor common classes and hide poor minority recall.",
                         "recommendation": "Use stratified splits and per-class metrics; consider weighting or resampling."})
    return {"status": "ok", "tool": "class_imbalance_check",
            "summary": f"Target {target} has {len(classes)} classes; majority/minority ratio {ratio}:1.",
            "data": {"target": target, "classes": classes, "majority_class": classes[0]["class"],
                     "minority_class": classes[-1]["class"], "majority_minority_ratio": ratio,
                     "thresholds_ratio": {"medium": 3.0, "high": 9.0},
                     "missing_target_count": int(frame[target].isna().sum())}, "findings": findings}
