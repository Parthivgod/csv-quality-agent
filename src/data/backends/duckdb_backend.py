"""Exact, disk-backed diagnostics over a session-owned typed Parquet file.

Only aggregate results and the small preview enter Python. CSV semantics are
decided by ``csv_contract`` before import, rather than by DuckDB sampling.
"""

from copy import deepcopy
from concurrent.futures import CancelledError
from itertools import combinations
import math
from pathlib import Path
import re
import threading
import time

import duckdb
import pandas as pd

from src.diagnostics.cardinality import _identifier_named


def _ident(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def _literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _result(name: str, summary: str, data=None, findings=None, status="ok") -> dict:
    return {"status": status, "tool": name, "summary": summary,
            "data": data or {}, "findings": findings or []}


def _memory_bytes(value):
    match = re.fullmatch(r"\s*([\d.]+)\s*(B|KB|MB|GB|KiB|MiB|GiB)\s*", str(value), flags=re.I)
    if not match:
        return 1024**3
    factors = {"b": 1, "kb": 1000, "mb": 1000**2, "gb": 1000**3,
               "kib": 1024, "mib": 1024**2, "gib": 1024**3}
    return float(match[1]) * factors[match[2].lower()]


class DuckDBDataset:
    """One connection and immutable Parquet dataset; close before removing storage."""

    backend = "duckdb"

    @classmethod
    def from_csv(cls, normalized_path, storage, metadata, settings=None, cancel_event=None):
        return cls(normalized_path, storage, metadata, settings, cancel_event)

    def __init__(self, normalized_path, storage, metadata, settings=None, cancel_event=None):
        self.storage = storage
        self.filename = storage.filename
        self.fingerprint = storage.fingerprint
        self.file_bytes = storage.file_bytes
        self.encoding = metadata.encoding
        self.warnings = tuple(metadata.warnings)
        self.row_count = metadata.row_count
        self.columns = list(metadata.columns)
        if len({c.casefold() for c in self.columns}) != len(self.columns):
            raise ValueError("Column names must also be unique ignoring case for disk-backed analysis.")
        self.dtypes = dict(metadata.column_types)
        self.null_counts = dict(metadata.null_counts)
        self.numeric_columns = [c for c in self.columns if self.dtypes[c] in ("int64", "float64")]
        self._preview_rows = metadata.preview_rows
        self._settings = settings
        self._lock = threading.RLock()
        self._closed = False
        self._cache = {}
        self._cancelled = threading.Event()
        self._connection = None
        owned = Path(normalized_path).parent
        self.parquet_path = owned / "dataset.parquet"
        self.spill_path = owned / "spill"
        self.spill_path.mkdir(exist_ok=True)
        self._connection = duckdb.connect(config={
            "memory_limit": getattr(settings, "duckdb_memory_limit", "1GB"),
            "threads": str(getattr(settings, "duckdb_threads", 2)),
            "temp_directory": str(self.spill_path),
            "max_temp_directory_size": f"{getattr(settings, 'duckdb_spill_limit_mb', 2048)}MiB",
            "enable_external_access": "true",
        })
        timeout = getattr(settings, "import_timeout_seconds", 60)
        expired = threading.Event()
        timer = self._timer(timeout, expired)
        watcher_stop = threading.Event()
        def watch_cancel():
            while not watcher_stop.wait(.05):
                if cancel_event is not None and cancel_event.is_set():
                    self.interrupt()
                    return
        watcher = threading.Thread(target=watch_cancel, daemon=True)
        watcher.start()
        try:
            if cancel_event is not None and cancel_event.is_set():
                raise CancelledError("Dataset import cancelled.")
            # Import is strict, with externally validated names and full-column types.
            # The shared contract canonicalizes every null token to an empty field.
            declared = "{" + ", ".join(f"{_literal(c)}: 'VARCHAR'" for c in self.columns) + "}"
            self._connection.execute(
                f"CREATE VIEW source_csv AS SELECT * FROM read_csv({_literal(str(normalized_path))}, "
                f"columns={declared}, header=true, delim=',', quote='\"', escape='\"', "
                "nullstr=[''], allow_quoted_nulls=true, strict_mode=true, ignore_errors=false, parallel=false, auto_detect=false)"
            )
            sql_types = {"int64": "BIGINT", "float64": "DOUBLE", "object": "VARCHAR"}
            projection = ", ".join(
                f"CAST({_ident(c)} AS {sql_types[self.dtypes[c]]}) AS {_ident(c)}"
                for c in self.columns
            )
            self._connection.execute(
                f"COPY (SELECT {projection} FROM source_csv) TO {_literal(str(self.parquet_path))} "
                "(FORMAT PARQUET, COMPRESSION ZSTD, ROW_GROUP_SIZE 122880)"
            )
            self._connection.execute("DROP VIEW source_csv")
            self._connection.read_parquet(str(self.parquet_path)).create_view("dataset")
            if self._one("SELECT count(*) FROM dataset") != self.row_count:
                raise ValueError("Imported row count does not match validated CSV")
            storage.check_space()
            if expired.is_set():
                raise TimeoutError("CSV import exceeded its time budget")
        except Exception as exc:
            timer.cancel()
            timer.join()
            self._connection.close()
            self._connection = None
            self._closed = True
            if cancel_event is not None and cancel_event.is_set():
                raise CancelledError("Dataset import cancelled.") from exc
            raise
        finally:
            watcher_stop.set()
            watcher.join()
            timer.cancel()
            timer.join()

    def _timer(self, seconds, expired):
        def stop():
            expired.set()
            self.interrupt()
        timer = threading.Timer(max(0.001, float(seconds)), stop)
        timer.daemon = True
        timer.start()
        return timer

    def _one(self, sql, parameters=None):
        if self._cancelled.is_set():
            raise CancelledError("Diagnostic interrupted.")
        return self._connection.execute(sql, parameters or []).fetchone()[0]

    def _rows(self, sql, parameters=None):
        if self._cancelled.is_set():
            raise CancelledError("Diagnostic interrupted.")
        return self._connection.execute(sql, parameters or []).fetchall()

    def preview(self, limit=10):
        """Source-order preview is capped, irrespective of Parquet scan ordering."""
        return pd.DataFrame(self._preview_rows[:max(0, min(int(limit), 10))], columns=self.columns)

    def metadata(self):
        return {"backend": self.backend, "filename": self.filename,
                "dataset_hash": self.fingerprint, "file_bytes": self.file_bytes,
                "rows": self.row_count, "columns": list(self.columns), "dtypes": dict(self.dtypes),
                "null_counts": dict(self.null_counts), "encoding": self.encoding, "warnings": list(self.warnings)}

    def _eligible(self, name, target):
        if name == "correlation_check":
            return [c for c in self.numeric_columns if c != target]
        if name == "outlier_check":
            return list(self.numeric_columns)
        if name == "high_cardinality_check":
            return [c for c in self.columns if c not in self.numeric_columns or _identifier_named(c)]
        if name == "class_imbalance_check":
            return [target] if target in self.columns else []
        return list(self.columns)

    def interrupt(self):
        """Thread-safe interrupt; query callers synchronously wait for completion."""
        self._cancelled.set()
        connection = self._connection
        if connection is not None and not self._closed:
            connection.interrupt()

    def close(self):
        self.interrupt()
        with self._lock:
            if self._connection is not None:
                self._connection.close()
                self._connection = None
            self._closed = True
            self._cache.clear()
            self.storage.close()

    def run_check(self, name, target=None, settings=None, columns=None):
        settings = settings or self._settings
        handlers = {
            "dataset_profile": self._profile, "missing_values_check": self._missing,
            "duplicate_rows_check": self._duplicates, "constant_columns_check": self._constants,
            "high_cardinality_check": self._cardinality, "outlier_check": self._outliers,
            "class_imbalance_check": self._imbalance, "correlation_check": self._correlation,
        }
        if name not in handlers:
            raise ValueError("Unknown diagnostic")
        selected = tuple(columns) if columns is not None else None
        if selected is not None and (len(set(selected)) != len(selected) or any(c not in self.columns for c in selected)):
            raise ValueError("Select existing, distinct columns")
        # Include thresholds and resource scope in immutable dataset cache keys.
        keys = ("missing_medium_pct", "missing_high_pct", "near_constant_ratio", "high_cardinality_ratio",
                "high_cardinality_min_non_null", "correlation_threshold", "max_numeric_columns", "duckdb_memory_limit")
        key = (name, target, selected, tuple(getattr(settings, k, None) for k in keys))
        start = time.perf_counter()
        with self._lock:
            if self._closed:
                raise RuntimeError("Dataset has been closed")
            if key in self._cache:
                result = deepcopy(self._cache[key])
                result["execution"]["cache_hit"] = True
                result["execution"]["elapsed_ms"] = round((time.perf_counter() - start) * 1000, 3)
                return result
            self._cancelled.clear()
            expired = threading.Event()
            timer = self._timer(getattr(settings, "query_timeout_seconds", 120), expired)
            try:
                result, checked = handlers[name](target, settings, selected)
                if expired.is_set() or self._cancelled.is_set():
                    result = _result(name, "Diagnostic interrupted or exceeded its time budget.", status="error")
                    checked = []
            except (duckdb.Error, CancelledError) as exc:
                summary = ("Diagnostic interrupted or exceeded its time budget." if expired.is_set() or self._cancelled.is_set()
                           else f"Diagnostic failed: {type(exc).__name__}. Resource limits may require a narrower request.")
                result, checked = _result(name, summary, status="error"), []
            finally:
                timer.cancel()
                timer.join()
            eligible = self._eligible(name, target)
            omitted = [c for c in eligible if c not in checked]
            result["execution"] = {
                "backend": self.backend, "dataset_hash": self.fingerprint,
                "rows": self.row_count, "exact": True,
                "method": "exact SQL aggregates over typed Parquet",
                "elapsed_ms": round((time.perf_counter() - start) * 1000, 3), "cache_hit": False,
                "columns_checked": list(checked), "columns_omitted": len(omitted),
                "coverage": {"columns_checked": list(checked),
                             "columns_omitted": omitted, "eligible_columns": eligible,
                             "ignored_columns": [c for c in self.columns if c not in eligible]},
            }
            if result["status"] in {"error", "skipped"}:
                result["execution"]["reason"] = result["summary"]
            if result["status"] != "error":
                self._cache[key] = deepcopy(result)
            self.storage.touch()
            return result

    def _profile(self, target, settings, columns):
        visible = list(self.columns[:50])
        if target in self.columns and target not in visible:
            visible[-1] = target
        unique = {c: self._one(f"SELECT count(DISTINCT {_ident(c)}) FROM dataset") for c in visible}
        data = {"rows": self.row_count, "columns": len(self.columns),
                "dtypes": {c: self.dtypes[c] for c in visible},
                "numeric_columns": self.numeric_columns[:50],
                "categorical_columns": [c for c in self.columns if c not in self.numeric_columns][:50],
                "unique_counts": unique, "null_counts": {c: self.null_counts[c] for c in visible},
                "truncated": len(self.columns) > 50}
        return _result("dataset_profile", f"Dataset has {self.row_count} rows and {len(self.columns)} columns.", data), visible

    def _missing(self, target, settings, columns):
        affected, findings = [], []
        medium, high = getattr(settings, "missing_medium_pct", 5), getattr(settings, "missing_high_pct", 30)
        for c in self.columns:
            n = self.null_counts[c]
            if not n:
                continue
            pct = round(n * 100 / self.row_count, 2)
            severity = "high" if pct > high else "medium" if pct >= medium else "low"
            affected.append({"column": c, "missing_count": n, "missing_pct": pct, "severity": severity})
            findings.append({"issue": "Missing values", "severity": severity, "column": c,
                             "evidence": f"{n}/{self.row_count} values missing ({pct}%)",
                             "impact": "Training may fail or estimates may be biased without appropriate handling.",
                             "recommendation": "Investigate why values are missing, then choose justified imputation or removal."})
        return _result("missing_values_check", f"{len(affected)} columns contain missing values.",
                       {"affected_columns": affected, "thresholds_pct": {"medium": medium, "high": high}}, findings), self.columns

    def _duplicates(self, target, settings, columns):
        if len(self.columns) > 50:
            return _result("duplicate_rows_check", "Exact full-row duplicates are limited to 50 columns; this dataset is wider.", status="skipped"), []
        unique = self._one("SELECT count(*) FROM (SELECT DISTINCT * FROM dataset)")
        n = self.row_count - unique
        pct = round(100 * n / self.row_count, 2)
        findings = ([{"issue": "Duplicate rows", "severity": "medium", "column": None,
                      "evidence": f"{n}/{self.row_count} rows duplicate earlier rows ({pct}%)",
                      "impact": "Repeated observations may overweight patterns; some repeats may be legitimate.",
                      "recommendation": "Review duplicate records in domain context before deduplication."}] if n else [])
        return _result("duplicate_rows_check", f"{n} duplicate rows ({pct}%). Contextual review is needed.",
                       {"duplicate_count": n, "duplicate_pct": pct}, findings), self.columns

    def _constants(self, target, settings, columns):
        constants, near, findings = [], [], []
        threshold = getattr(settings, "near_constant_ratio", .95)
        for c in self.columns:
            unique, maximum = self._rows(f"SELECT count(*), max(n) FROM (SELECT count(*) n FROM dataset GROUP BY {_ident(c)})")[0]
            ratio = round(maximum / self.row_count, 4)
            item = {"column": c, "unique_count_including_null": unique, "dominant_ratio": ratio}
            if unique <= 1:
                constants.append(item)
                kind, severity = "Constant column", "medium"
            elif ratio >= threshold:
                near.append(item)
                kind, severity = "Near-constant column", "low"
            else:
                continue
            findings.append({"issue": kind, "severity": severity, "column": c,
                             "evidence": f"{unique} distinct values including null; dominant fraction {ratio:.2%}",
                             "impact": "This feature may provide little predictive information.",
                             "recommendation": "Review its role before excluding it from model inputs."})
        return _result("constant_columns_check", f"{len(constants)} constant and {len(near)} near-constant columns.",
                       {"constant_columns": constants, "near_constant_columns": near, "near_constant_threshold": threshold}, findings), self.columns

    def _cardinality(self, target, settings, columns):
        candidates, findings, checked = [], [], []
        threshold = getattr(settings, "high_cardinality_ratio", .90)
        minimum = getattr(settings, "high_cardinality_min_non_null", 20)
        for c in self.columns:
            if c in self.numeric_columns and not _identifier_named(c):
                continue
            checked.append(c)
            n = self.row_count - self.null_counts[c]
            if n < minimum:
                continue
            unique = self._one(f"SELECT count(DISTINCT {_ident(c)}) FROM dataset")
            ratio = round(unique / n, 4)
            if ratio < threshold:
                continue
            candidates.append({"column": c, "unique_count": unique, "non_null_count": n, "unique_ratio": ratio,
                               "possible_interpretation": "Potential identifier-like or high-cardinality feature; review context."})
            findings.append({"issue": "High-cardinality feature", "severity": "low", "column": c,
                             "evidence": f"{unique}/{n} non-null values unique (ratio {ratio})",
                             "impact": "Identifiers may encourage memorization or misleading numeric ordering; categories can expand encodings.",
                             "recommendation": "Determine whether the field is an identifier or useful predictor before changing it."})
        return _result("high_cardinality_check", f"{len(candidates)} potential high-cardinality columns.",
                       {"candidates": candidates, "ratio_threshold": threshold, "min_non_null": minimum}, findings), checked

    def _outliers(self, target, settings, columns):
        numeric = [c for c in self.numeric_columns if columns is None or c in columns]
        if not numeric:
            return _result("outlier_check", "No numeric columns to assess.", status="skipped"), []
        limit = getattr(settings, "max_numeric_columns", 20)
        if len(numeric) > limit:
            return _result("outlier_check", f"Exact outliers require at most {limit} selected numeric columns; select a bounded subset.", status="skipped"), []
        data, findings = [], []
        counts = {c: self._one(f"SELECT count(*) FROM dataset WHERE isfinite({_ident(c)})") for c in numeric}
        # Holistic exact quantiles need their own value/sort buffers, beyond spill.
        # Keep conservative headroom; this is a guard, not a process RSS guarantee.
        memory = _memory_bytes(getattr(settings, "duckdb_memory_limit", "1GB"))
        if any(n * 24 > memory * .5 for n in counts.values()):
            return _result("outlier_check", "Exact quartile allocation estimate exceeds the memory budget; this check was not executed.",
                           {"memory_guard": "24 bytes per finite value, at most half configured engine memory"}, status="skipped"), []
        for c in numeric:
            q = _ident(c)
            n = counts[c]
            if n < 4:
                continue
            q1, q3 = self._one(f"SELECT quantile_cont({q}, [.25, .75]) FROM dataset WHERE isfinite({q})")
            lower, upper = float(q1 - 1.5 * (q3 - q1)), float(q3 + 1.5 * (q3 - q1))
            count = self._one(f"SELECT count(*) FROM dataset WHERE isfinite({q}) AND ({q} < ? OR {q} > ?)", [lower, upper])
            pct = round(count * 100 / n, 2)
            data.append({"column": c, "outlier_count": count, "outlier_pct": pct,
                         "lower_bound": round(lower, 4), "upper_bound": round(upper, 4), "non_null_count": n})
            if count:
                findings.append({"issue": "IQR outliers", "severity": "medium", "column": c,
                                 "evidence": f"{count}/{n} values outside [{lower:.4g}, {upper:.4g}] ({pct}%)",
                                 "impact": "Extreme values may affect some models or preprocessing steps; they can also be valid.",
                                 "recommendation": "Inspect these observations and the domain before any capping or removal."})
        return _result("outlier_check", f"{len(findings)} numeric columns have IQR outliers.",
                       {"columns": data, "method": "1.5 x IQR"}, findings), numeric

    def _imbalance(self, target, settings, columns):
        name = "class_imbalance_check"
        if not target or target not in self.columns:
            return _result(name, "Select a valid target column to assess class imbalance.", status="skipped"), []
        q = _ident(target)
        maximum_bytes = self._one(f"SELECT max(octet_length(encode(CAST({q} AS VARCHAR)))) FROM dataset") or 0
        if maximum_bytes > 256:
            return _result(name, "Selected target has class labels longer than 256 UTF-8 bytes; select a compact categorical target.",
                           {"maximum_label_bytes": maximum_bytes, "maximum_supported_label_bytes": 256}, status="skipped"), [target]
        unique = self._one(f"SELECT count(DISTINCT {q}) FROM dataset")
        if unique < 2:
            return _result(name, "Target needs at least two observed classes.", status="skipped"), [target]
        if unique > 50 or unique > max(10, self.row_count * .2):
            return _result(name, "Selected target has too many distinct values for a class-imbalance check.",
                           {"unique_classes": unique}, status="skipped"), [target]
        # Tie order is first source occurrence, matching Pandas value_counts.
        # Parquet preserves import order; ordinality is computed only for this bounded grouping.
        counts = self._rows(f"SELECT {q}, count(*) n FROM (SELECT *, row_number() OVER () source_order FROM dataset) "
                            f"WHERE {q} IS NOT NULL GROUP BY {q} ORDER BY n DESC, min(source_order)")
        total = self.row_count - self.null_counts[target]
        classes = [{"class": str(label), "count": n, "proportion": round(n / total, 4),
                    "percentage": round(n / total * 100, 4)} for label, n in counts]
        ratio = round(counts[0][1] / counts[-1][1], 4)
        findings = []
        if ratio >= 3:
            findings.append({"issue": "Class imbalance", "severity": "high" if ratio >= 9 else "medium", "column": target,
                             "evidence": f"Majority/minority ratio {ratio}:1; counts {classes}",
                             "impact": "A classifier can favor common classes and hide poor minority recall.",
                             "recommendation": "Use stratified splits and per-class metrics; consider weighting or resampling."})
        data = {"target": target, "classes": classes, "majority_class": classes[0]["class"],
                "minority_class": classes[-1]["class"], "majority_minority_ratio": ratio,
                "thresholds_ratio": {"medium": 3.0, "high": 9.0},
                "missing_target_count": self.null_counts[target]}
        return _result(name, f"Target {target} has {len(classes)} classes; majority/minority ratio {ratio}:1.", data, findings), [target]

    def _correlation(self, target, settings, columns):
        numeric = [c for c in self.numeric_columns if c != target and (columns is None or c in columns)]
        name = "correlation_check"
        if len(numeric) < 2:
            return _result(name, "At least two numeric feature columns are needed.", status="skipped"), numeric
        limit = getattr(settings, "max_numeric_columns", 20)
        if len(numeric) > limit:
            return _result(name, f"Exact correlation requires at most {limit} selected numeric columns; select a bounded subset.", status="skipped"), []
        threshold = getattr(settings, "correlation_threshold", .95)
        pairs, findings = [], []
        eligible = list(combinations(numeric, 2))
        # All pairs in one scan; each aggregate has its own finite-value filter.
        projection = ", ".join(
            f"corr({_ident(left)}, {_ident(right)}) FILTER (WHERE isfinite({_ident(left)}) AND isfinite({_ident(right)}))"
            for left, right in eligible
        )
        values = self._rows(f"SELECT {projection} FROM dataset")[0]
        for (left, right), value in zip(eligible, values):
            if value is None or not math.isfinite(value) or abs(value) < threshold:
                continue
            rounded = round(value, 4)
            pairs.append({"left": left, "right": right, "correlation": rounded})
            findings.append({"issue": "Strong feature correlation", "severity": "medium", "column": f"{left}, {right}",
                             "evidence": f"Pearson r({left}, {right}) = {rounded}",
                             "impact": "Possible redundancy or leakage candidate; correlation alone does not prove leakage.",
                             "recommendation": "Review feature provenance and model assumptions before dropping either feature."})
        return _result(name, f"{len(pairs)} numeric feature pairs meet |r| >= {threshold}.",
                       {"pairs": pairs, "threshold": threshold}, findings), numeric
