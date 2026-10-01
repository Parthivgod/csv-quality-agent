"""Per-request LangChain tools bound to a local dataset with bounded observations."""

import json
import copy
import time
from dataclasses import replace
from collections.abc import Callable

import pandas as pd
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, ConfigDict, Field, StrictStr, field_validator

from src.config import Settings
from src.diagnostics.profile import dataset_profile
from src.diagnostics.missing import missing_values_check
from src.diagnostics.duplicates import duplicate_rows_check
from src.diagnostics.constants import constant_columns_check
from src.diagnostics.cardinality import high_cardinality_check
from src.diagnostics.outliers import outlier_check
from src.diagnostics.imbalance import class_imbalance_check
from src.diagnostics.correlation import correlation_check
from src.services.trace import TraceCollector, normalize_selection_reason
from src.services.evidence import sanitize_statistics


DESCRIPTIONS = {
    "dataset_profile": "Use for a broad schema/shape overview. Returns rows, dtypes, uniqueness and null counts. Do not use for a narrow question if a dedicated tool suffices.",
    "missing_values_check": "Use for missing, null or incomplete data. Returns counts, percentages and severity by column. Do not use for duplicates, outliers or imbalance.",
    "duplicate_rows_check": "Use for exact duplicate rows or repeated records. Returns count and percentage. Do not assume duplicates are invalid; do not use for missing values.",
    "constant_columns_check": "Use for constant or almost unchanging features. Returns columns and dominant fractions. Do not use for high-cardinality IDs.",
    "high_cardinality_check": "Use for potential ID columns or high-cardinality categories. Returns unique ratios for categorical fields and identifier-named numeric fields. Do not flag ordinary continuous numeric features or recommend removal without context; do not use for constants.",
    "outlier_check": "Use for extreme numeric values and IQR outliers. Returns bounds and counts. Do not use for categorical fields or treat all outliers as errors.",
    "class_imbalance_check": "Use only for selected classification target distributions or class imbalance. Returns counts, proportions and majority/minority ratio. Do not use without a target.",
    "correlation_check": "Use for relationships between numeric features or possible redundancy. Returns pairs with high absolute Pearson correlation. Do not claim confirmed leakage.",
}


class DiagnosticArgs(BaseModel):
    """Dataset, target and coverage remain fixed by the current request."""

    model_config = ConfigDict(extra="forbid")
    reason: StrictStr = Field(default="", max_length=300,
        description="Optional brief user-facing explanation of why this check answers the question. No private reasoning or unverified findings.")

    @field_validator("reason", mode="before")
    @classmethod
    def normalize_reason(cls, value):
        if isinstance(value, str):
            return normalize_selection_reason(value)
        return value  # StrictStr rejects numbers, bools, collections and null.


def build_tools(frame: pd.DataFrame, target: str | None, settings: Settings,
                trace: TraceCollector, columns: list[str] | None = None,
                cancel_event=None, progress=None) -> list[StructuredTool]:
    """Build isolated tools whose closures own the current request's DataFrame."""
    functions: dict[str, Callable[[], dict]] = {
        "dataset_profile": lambda: dataset_profile(frame),
        "missing_values_check": lambda: missing_values_check(frame, settings.missing_medium_pct, settings.missing_high_pct),
        "duplicate_rows_check": lambda: duplicate_rows_check(frame),
        "constant_columns_check": lambda: constant_columns_check(frame, settings.near_constant_ratio),
        "high_cardinality_check": lambda: high_cardinality_check(frame, settings.high_cardinality_ratio, settings.high_cardinality_min_non_null),
        "outlier_check": lambda: outlier_check(frame),
        "class_imbalance_check": lambda: class_imbalance_check(frame, target),
        "correlation_check": lambda: correlation_check(frame, target, settings.correlation_threshold),
    }
    if not isinstance(frame, pd.DataFrame):
        def handle_check(name):
            remaining = max(0.001, settings.max_local_compute_seconds - trace.local_compute_seconds)
            active = replace(settings, query_timeout_seconds=min(settings.query_timeout_seconds, remaining))
            return frame.run_check(name, target=target, settings=active, columns=columns)
        functions = {name: (lambda n=name: handle_check(n)) for name in DESCRIPTIONS}
    tools = []
    for name, diagnostic in functions.items():
        def make_run(_name: str, _diagnostic: Callable[[], dict]) -> Callable[..., str]:
            def run(reason: str = "") -> str:
                reason = normalize_selection_reason(reason)
                with trace.lock:
                    if len(trace.events) >= settings.max_tool_attempts:
                        raise RuntimeError("Maximum attempted diagnostic events reached.")
                    if cancel_event is not None and cancel_event.is_set():
                        raise RuntimeError("Analysis cancelled.")
                    if trace.executed_calls >= settings.max_tool_calls:
                        result = {"status": "skipped", "tool": _name,
                                  "summary": "Diagnostic call budget reached.", "data": {}, "findings": []}
                    elif any(e["tool"] == _name for e in trace.events):
                        result = {"status": "skipped", "tool": _name,
                                  "summary": "This diagnostic already ran; use its previous observation.", "data": {}, "findings": []}
                    elif trace.local_compute_seconds >= settings.max_local_compute_seconds:
                        result = {"status": "skipped", "tool": _name,
                                  "summary": "Local computation budget reached.", "data": {}, "findings": []}
                    else:
                        trace.executed_calls += 1
                        started = time.perf_counter()
                        try:
                            if progress:
                                progress(f"Running {_name}" + (f" — {reason}" if reason else ""))
                            result = _diagnostic()
                        except Exception as exc:
                            result = {"status": "error", "tool": _name,
                                      "summary": f"Diagnostic failed: {type(exc).__name__}", "data": {}, "findings": []}
                        trace.local_compute_seconds += time.perf_counter() - started
                        result.setdefault("execution", {}).setdefault("elapsed_ms", round((time.perf_counter()-started)*1000, 2))
                        result["execution"].setdefault("exact", True)
                        result["execution"].setdefault("cache_hit", False)
                        result["execution"].setdefault("backend", "pandas" if isinstance(frame, pd.DataFrame) else frame.backend)
                    trace.full_results.append(result)
                    result = bound_observation(result, settings)
                    trace.add(_name, {"reason": reason} if reason else {}, result)
                return json.dumps(result, ensure_ascii=False)
            return run

        tools.append(StructuredTool.from_function(
            func=make_run(name, diagnostic), name=name,
            description=DESCRIPTIONS[name] + " Supply a brief optional reason explaining relevance to the user's question before running the check.",
            args_schema=DiagnosticArgs))
    return tools


def bound_observation(result: dict, settings: Settings) -> dict:
    """Keep complete findings and valid JSON; expose every omitted result."""
    bounded = copy.deepcopy(result)
    bounded, nonfinite = sanitize_statistics(bounded)
    if nonfinite:
        bounded.setdefault("execution", {})["coverage_limitation"] = "Non-finite computed statistics are represented as null; inspect numerical range before interpreting them."
    original_count = len(bounded.get("findings", []))
    bounded["findings"] = bounded.get("findings", [])[:settings.max_findings_per_tool]
    execution = bounded.setdefault("execution", {})
    execution["findings_total"] = original_count
    execution["findings_omitted"] = original_count - len(bounded["findings"])
    # Per-column arrays/dictionaries may grow with wide schemas; do not transmit every entry.
    for key, value in list(bounded.get("data", {}).items()):
        if isinstance(value, list) and len(value) > settings.max_findings_per_tool:
            bounded["data"][key] = value[:settings.max_findings_per_tool]
            execution.setdefault("data_entries_omitted", {})[key] = len(value) - settings.max_findings_per_tool
        elif isinstance(value, dict) and len(value) > settings.max_schema_columns:
            bounded["data"][key] = dict(list(value.items())[:settings.max_schema_columns])
            execution.setdefault("data_entries_omitted", {})[key] = len(value) - settings.max_schema_columns
    def size():
        return len(json.dumps(bounded, ensure_ascii=False, allow_nan=False).encode("utf-8"))
    if size() > settings.max_observation_bytes:
        bounded["data"] = {}
        execution["data_omitted_for_size"] = True
    while size() > settings.max_observation_bytes and bounded["findings"]:
        bounded["findings"].pop()
        execution["findings_omitted"] += 1
    if execution.get("findings_omitted") or execution.get("data_entries_omitted") or execution.get("data_omitted_for_size"):
        execution["output_limited"] = True
        execution["output_limitation"] = "Tool output is bounded; inspect coverage and the full local evidence export for omitted entries."
    if size() > settings.max_observation_bytes:
        # Extremely long column names or diagnostic summaries must not bypass the cap.
        minimal = {key: execution[key] for key in ("backend", "dataset_hash", "rows", "exact", "columns_omitted") if key in execution}
        bounded = {"status": "skipped", "tool": result["tool"], "summary": "Diagnostic observation exceeds the model context limit.",
                   "data": {}, "findings": [], "execution": {"output_limited": True, "findings_total": original_count,
                   "findings_omitted": original_count, "output_limitation": "The complete result is available only in the local evidence export.", **minimal}}
    return bounded
