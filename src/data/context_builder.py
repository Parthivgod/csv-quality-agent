"""Bounded schema-only context for the language model."""

import pandas as pd


def build_context(frame: pd.DataFrame, target: str | None = None, max_columns: int = 50) -> dict:
    """Build compact metadata; never include raw cell values or sample rows."""
    columns = list(frame.columns[:max_columns])
    numeric = [c for c in columns if pd.api.types.is_numeric_dtype(frame[c])]
    return {
        "rows": int(len(frame)),
        "columns": int(len(frame.columns)),
        "schema": [{"name": str(c), "dtype": str(frame[c].dtype)} for c in columns],
        "numeric_columns": [str(c) for c in numeric],
        "categorical_columns": [str(c) for c in columns if c not in numeric],
        "target_column": target if target in frame.columns else None,
        "schema_truncated": len(frame.columns) > max_columns,
    }
