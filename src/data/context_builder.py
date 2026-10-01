"""Bounded schema-only context for the language model."""

import pandas as pd


def build_context(frame, target: str | None = None, max_columns: int = 50,
                  selected_columns: list[str] | None = None) -> dict:
    """Build compact metadata; never include raw cell values or sample rows."""
    all_columns = list(frame.columns)
    columns = all_columns[:max_columns]
    if target in all_columns and target not in columns:
        columns = columns[:max_columns - 1] + [target]
    if isinstance(frame, pd.DataFrame):
        dtypes = {str(c): str(frame[c].dtype) for c in all_columns}
        rows, backend = len(frame), "pandas"
    else:
        dtypes = frame.dtypes
        rows, backend = frame.row_count, frame.backend
    numeric = [c for c in columns if pd.api.types.is_numeric_dtype(dtypes[str(c)])]
    return {
        "rows": int(rows),
        "columns": len(all_columns),
        "backend": backend,
        "schema": [{"name": str(c), "dtype": dtypes[str(c)]} for c in columns],
        "numeric_columns": [str(c) for c in numeric],
        "categorical_columns": [str(c) for c in columns if c not in numeric],
        "target_column": target if target in all_columns else None,
        "schema_truncated": len(all_columns) > max_columns,
        "schema_columns_omitted": max(0, len(all_columns) - len(columns)),
        "selected_numeric_columns": selected_columns,
    }
