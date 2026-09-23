"""Dataset overview diagnostic."""

import pandas as pd


def dataset_profile(frame: pd.DataFrame) -> dict:
    numeric = [str(c) for c in frame.select_dtypes(include="number").columns]
    return {
        "status": "ok", "tool": "dataset_profile",
        "summary": f"Dataset has {len(frame)} rows and {len(frame.columns)} columns.",
        "data": {
            "rows": int(len(frame)), "columns": int(len(frame.columns)),
            "dtypes": {str(c): str(frame[c].dtype) for c in frame.columns[:50]},
            "numeric_columns": numeric[:50],
            "categorical_columns": [str(c) for c in frame.columns if str(c) not in numeric][:50],
            "unique_counts": {str(c): int(frame[c].nunique(dropna=True)) for c in frame.columns[:50]},
            "null_counts": {str(c): int(frame[c].isna().sum()) for c in frame.columns[:50]},
            "truncated": len(frame.columns) > 50,
        },
        "findings": [],
    }
