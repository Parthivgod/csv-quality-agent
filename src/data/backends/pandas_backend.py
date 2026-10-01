"""Reference DataFrame diagnostics behind the common dataset interface."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import time

import pandas as pd

from src.config import Settings
from src.data.csv_contract import CONTRACT_VERSION, CSVMetadata
from src.data.upload_store import UploadStore
from src.diagnostics.profile import dataset_profile
from src.diagnostics.missing import missing_values_check
from src.diagnostics.duplicates import duplicate_rows_check
from src.diagnostics.constants import constant_columns_check
from src.diagnostics.cardinality import high_cardinality_check
from src.diagnostics.cardinality import _identifier_named
from src.diagnostics.outliers import outlier_check
from src.diagnostics.imbalance import class_imbalance_check
from src.diagnostics.correlation import correlation_check


class PandasDataset:
    backend = "pandas"

    def __init__(self, frame: pd.DataFrame, filename: str = "in-memory.csv", *,
                 storage: UploadStore | None = None, metadata: CSVMetadata | None = None,
                 settings: Settings | None = None) -> None:
        self.frame = frame
        self.filename = filename
        self.storage = storage
        self.settings = settings or Settings()
        self.encoding = metadata.encoding if metadata else "in-memory"
        self.warnings = metadata.warnings if metadata else ()
        self.fingerprint = storage.fingerprint if storage else hashlib.sha256(pd.util.hash_pandas_object(frame, index=True).values.tobytes()).hexdigest()
        self.file_bytes = storage.file_bytes if storage else int(frame.memory_usage(deep=True).sum())
        self.row_count = len(frame)
        self.columns = list(frame.columns)
        self.dtypes = {str(c): str(frame[c].dtype) for c in frame.columns}
        self.null_counts = {str(c): int(frame[c].isna().sum()) for c in frame.columns}
        self._cache: dict[tuple, dict] = {}
        self._preview_rows = metadata.preview_rows if metadata else None
        self.closed = False

    @classmethod
    def from_frame(cls, frame: pd.DataFrame, filename="in-memory.csv", settings=None):
        return cls(frame, filename, settings=settings)

    def preview(self, limit: int = 10) -> pd.DataFrame:
        if self._preview_rows is not None:
            return pd.DataFrame(self._preview_rows[:max(0, min(limit, 10))], columns=self.columns)
        return self.frame.head(max(0, min(limit, 50))).copy()

    @property
    def numeric_columns(self) -> list[str]:
        return [column for column in self.columns if pd.api.types.is_numeric_dtype(self.frame[column])]

    def metadata(self) -> dict:
        return {"backend": self.backend, "filename": self.filename,
            "dataset_hash": self.fingerprint, "file_bytes": self.file_bytes,
            "rows": self.row_count, "columns": self.columns, "dtypes": self.dtypes,
            "null_counts": self.null_counts, "encoding": self.encoding, "warnings": list(self.warnings)}

    def run_check(self, name: str, target: str | None = None, settings=None, columns=None) -> dict:
        if self.closed:
            raise RuntimeError("Dataset is closed.")
        active = settings or self.settings
        key = (CONTRACT_VERSION, name, target, tuple(columns) if columns is not None else None, repr(active))
        start = time.perf_counter()
        if key in self._cache:
            result = deepcopy(self._cache[key])
            result["execution"]["cache_hit"] = True
            result["execution"]["elapsed_ms"] = round((time.perf_counter() - start) * 1000, 3)
            return result
        frame = self.frame
        if columns is not None and name in {"outlier_check", "correlation_check"}:
            unknown = set(columns) - set(self.columns)
            if unknown or len(set(columns)) != len(columns):
                raise ValueError("Select existing, distinct columns.")
            frame = frame[columns]
        functions = {
            "dataset_profile": lambda: dataset_profile(frame),
            "missing_values_check": lambda: missing_values_check(frame, active.missing_medium_pct, active.missing_high_pct),
            "duplicate_rows_check": lambda: duplicate_rows_check(frame),
            "constant_columns_check": lambda: constant_columns_check(frame, active.near_constant_ratio),
            "high_cardinality_check": lambda: high_cardinality_check(frame, active.high_cardinality_ratio, active.high_cardinality_min_non_null),
            "outlier_check": lambda: outlier_check(frame),
            "class_imbalance_check": lambda: class_imbalance_check(frame, target),
            "correlation_check": lambda: correlation_check(frame, target, active.correlation_threshold),
        }
        if name not in functions:
            raise ValueError("Unknown diagnostic.")
        checked = list(frame.columns)
        numeric = list(frame.select_dtypes(include="number").columns)
        if name == "correlation_check":
            numeric = [c for c in numeric if c != target]
        numeric_limit = getattr(active, "max_numeric_columns", 20)
        if name in {"outlier_check", "correlation_check"} and len(numeric) > numeric_limit:
            kind = "outliers" if name == "outlier_check" else "correlation"
            result = {"status": "skipped", "tool": name,
                "summary": f"Exact {kind} require at most {numeric_limit} selected numeric columns; select a bounded subset." if kind == "outliers" else f"Exact correlation requires at most {numeric_limit} selected numeric columns; select a bounded subset.",
                "data": {}, "findings": []}
            checked = []
        elif name == "duplicate_rows_check" and len(self.columns) > 50:
            result = {"status": "skipped", "tool": name,
                "summary": "Exact full-row duplicates are limited to 50 columns; this dataset is wider.", "data": {}, "findings": []}
            checked = []
        else:
            if name == "class_imbalance_check" and target in self.columns and any(
                    len(str(value).encode("utf-8")) > 256 for value in frame[target].dropna().unique()):
                result = {"status": "skipped", "tool": name,
                    "summary": "Class imbalance requires target labels of at most 256 UTF-8 bytes; shorten unusually long labels before this check.",
                    "data": {}, "findings": []}
            else:
                result = functions[name]()
            if name in {"outlier_check", "correlation_check"}:
                checked = numeric
            elif name == "class_imbalance_check":
                checked = [target] if target in self.columns else []
            elif name == "high_cardinality_check":
                checked = [c for c in self.columns if c not in self.numeric_columns or _identifier_named(c)]
            elif name == "dataset_profile":
                checked = list(self.columns[:50])
                if target in self.columns and target not in checked:
                    checked[-1] = target
                    result["data"]["dtypes"] = {c: self.dtypes[c] for c in checked}
                    result["data"]["unique_counts"] = {c: int(frame[c].nunique(dropna=True)) for c in checked}
                    result["data"]["null_counts"] = {c: self.null_counts[c] for c in checked}
        result["execution"] = {"backend": self.backend, "dataset_hash": self.fingerprint,
            "rows": self.row_count, "columns_checked": checked, "exact": True,
            "method": "pandas-reference", "elapsed_ms": round((time.perf_counter()-start)*1000, 3),
            "cache_hit": False, "contract_version": CONTRACT_VERSION,
            "coverage": {"columns_checked": checked,
                         "columns_omitted": [c for c in self.columns if c not in checked]}}
        eligible = self.columns
        if name in {"outlier_check", "correlation_check"}:
            eligible = [c for c in self.numeric_columns if name != "correlation_check" or c != target]
        elif name == "class_imbalance_check":
            eligible = [target] if target in self.columns else []
        elif name == "high_cardinality_check":
            eligible = [c for c in self.columns if c not in self.numeric_columns or _identifier_named(c)]
        omitted = [c for c in eligible if c not in checked]
        result["execution"]["coverage"] = {"columns_checked": checked,
            "columns_omitted": omitted, "eligible_columns": list(eligible),
            "ignored_columns": [c for c in self.columns if c not in eligible]}
        result["execution"]["columns_omitted"] = len(omitted)
        self._cache[key] = deepcopy(result)
        if self.storage:
            self.storage.touch()
        return result

    def interrupt(self) -> None:
        # Reference checks run synchronously; no query worker is owned here.
        pass

    def close(self) -> None:
        if not self.closed:
            self._cache.clear()
            self.frame = pd.DataFrame()
            if self.storage:
                self.storage.close()
            self.closed = True
