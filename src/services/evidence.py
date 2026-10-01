"""Portable evidence without upload contents, credentials, or local paths."""
import json
import math
from datetime import datetime, timezone

def sanitize_statistics(value):
    """Return strict-JSON-compatible statistics and the count of non-finite replacements."""
    count = 0
    def clean(item):
        nonlocal count
        if isinstance(item, float) and not math.isfinite(item):
            count += 1
            return None
        if isinstance(item, dict):
            return {key: clean(child) for key, child in item.items()}
        if isinstance(item, (list, tuple)):
            return [clean(child) for child in item]
        return item
    return clean(value), count

def evidence_bundle(result, question: str, dataset, target=None):
    return {"schema_version": 1, "exported_utc": datetime.now(timezone.utc).isoformat(),
        "dataset": {"filename": dataset.filename, "sha256": dataset.fingerprint,
                    "file_bytes": dataset.file_bytes, "rows": dataset.row_count,
                    "column_count": len(dataset.columns), "backend": dataset.backend,
                    "encoding": dataset.encoding, "import_seconds": getattr(dataset, "import_seconds", None)},
        "question": question, "target": target, "run": result.metadata,
        "trace": result.trace, "full_tool_results": result.full_results,
        "report": result.report.model_dump()}

def evidence_json(result, question: str, dataset, target=None):
    bundle, count = sanitize_statistics(evidence_bundle(result, question, dataset, target))
    if count:
        bundle["serialization_note"] = f"{count} non-finite statistics were represented as null."
    return json.dumps(bundle, ensure_ascii=False, allow_nan=False,
                      indent=2, default=str).encode("utf-8")
