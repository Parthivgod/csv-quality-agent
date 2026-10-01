"""Dataset interface shared by bounded in-memory and disk-backed diagnostics."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

import pandas as pd


@runtime_checkable
class DatasetHandle(Protocol):
    filename: str
    fingerprint: str
    file_bytes: int
    encoding: str
    warnings: tuple[str, ...]
    backend: str
    row_count: int
    columns: list[str]
    dtypes: dict[str, str]
    null_counts: dict[str, int]

    def preview(self, limit: int = 10) -> pd.DataFrame: ...
    def run_check(self, name: str, target: str | None = None, settings=None,
                  columns: list[str] | None = None) -> dict: ...
    def close(self) -> None: ...
    def interrupt(self) -> None: ...


def as_dataset(value: DatasetHandle | pd.DataFrame, settings=None) -> DatasetHandle:
    if isinstance(value, pd.DataFrame):
        from src.data.backends.pandas_backend import PandasDataset
        return PandasDataset.from_frame(value, settings=settings)
    return value
