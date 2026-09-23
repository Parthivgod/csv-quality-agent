"""Per-request LangChain tools bound to one in-memory DataFrame."""

import json
from collections.abc import Callable

import pandas as pd
from langchain_core.tools import StructuredTool
from pydantic import BaseModel

from src.config import Settings
from src.diagnostics.profile import dataset_profile
from src.diagnostics.missing import missing_values_check
from src.diagnostics.duplicates import duplicate_rows_check
from src.diagnostics.constants import constant_columns_check
from src.diagnostics.cardinality import high_cardinality_check
from src.diagnostics.outliers import outlier_check
from src.diagnostics.imbalance import class_imbalance_check
from src.diagnostics.correlation import correlation_check
from src.services.trace import TraceCollector


DESCRIPTIONS = {
    "dataset_profile": "Use for a broad schema/shape overview. Returns rows, dtypes, uniqueness and null counts. Do not use for a narrow question if a dedicated tool suffices.",
    "missing_values_check": "Use for missing, null or incomplete data. Returns counts, percentages and severity by column. Do not use for duplicates, outliers or imbalance.",
    "duplicate_rows_check": "Use for exact duplicate rows or repeated records. Returns count and percentage. Do not assume duplicates are invalid; do not use for missing values.",
    "constant_columns_check": "Use for constant or almost unchanging features. Returns columns and dominant fractions. Do not use for high-cardinality IDs.",
    "high_cardinality_check": "Use for potential ID columns or features with many unique values. Returns unique ratios. Do not recommend removal without context; do not use for constants.",
    "outlier_check": "Use for extreme numeric values and IQR outliers. Returns bounds and counts. Do not use for categorical fields or treat all outliers as errors.",
    "class_imbalance_check": "Use only for selected classification target distributions or class imbalance. Returns counts, proportions and majority/minority ratio. Do not use without a target.",
    "correlation_check": "Use for relationships between numeric features or possible redundancy. Returns pairs with high absolute Pearson correlation. Do not claim confirmed leakage.",
}


class NoArgs(BaseModel):
    """All diagnostics operate on the DataFrame held by this request."""


def build_tools(frame: pd.DataFrame, target: str | None, settings: Settings,
                trace: TraceCollector) -> list[StructuredTool]:
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
    tools = []
    for name, diagnostic in functions.items():
        def make_run(_name: str, _diagnostic: Callable[[], dict]) -> Callable[[], str]:
            def run() -> str:
                with trace.lock:
                    if len(trace.events) >= settings.max_tool_calls:
                        result = {"status": "skipped", "tool": _name,
                                  "summary": "Diagnostic call budget reached.", "data": {}, "findings": []}
                    elif any(e["tool"] == _name for e in trace.events):
                        result = {"status": "skipped", "tool": _name,
                                  "summary": "This diagnostic already ran; use its previous observation.", "data": {}, "findings": []}
                    else:
                        try:
                            result = _diagnostic()
                        except Exception as exc:
                            result = {"status": "error", "tool": _name,
                                      "summary": f"Diagnostic failed: {type(exc).__name__}", "data": {}, "findings": []}
                    trace.add(_name, {}, result)
                return json.dumps(result, ensure_ascii=False)
            return run

        tools.append(StructuredTool.from_function(
            func=make_run(name, diagnostic), name=name, description=DESCRIPTIONS[name], args_schema=NoArgs))
    return tools
