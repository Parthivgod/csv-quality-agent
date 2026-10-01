"""Measure independent imports and exact checks; retain successes and failures.

This process is the application harness, not the Streamlit/browser uploader.
RSS includes this process and its recursive children; the upload buffer is not measured.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.metadata
import json
import platform
import subprocess
import sys
import threading
import time
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import psutil

from src.config import Settings
from src.data.loader import load_dataset
import src.data.upload_store as upload_store

TOOLS = ("missing_values_check", "duplicate_rows_check", "class_imbalance_check", "constant_columns_check",
         "high_cardinality_check", "outlier_check", "correlation_check", "dataset_profile")


def environment() -> dict:
    versions = {}
    for package in ("pandas", "duckdb", "streamlit", "langchain", "langchain-groq", "psutil"):
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            versions[package] = "not installed"
    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        commit = "unavailable"
    source_files = sorted([ROOT / "app.py", *ROOT.glob("src/**/*.py"), *ROOT.glob("scripts/*.py")])
    source_digest = hashlib.sha256()
    for file in source_files:
        source_digest.update(str(file.relative_to(ROOT)).replace("\\", "/").encode("utf-8"))
        source_digest.update(file.read_bytes())
    try:
        working_tree_modified = bool(subprocess.check_output(["git", "status", "--porcelain", "--", "app.py", "src", "scripts", "requirements.txt"], cwd=ROOT, text=True).strip())
    except (OSError, subprocess.CalledProcessError):
        working_tree_modified = None
    return {"utc_time": datetime.now(timezone.utc).isoformat(), "commit": commit,
            "working_tree_modified": working_tree_modified, "source_snapshot_sha256": source_digest.hexdigest(),
            "python": sys.version.split()[0], "platform": platform.platform(), "processor": platform.processor(),
            "logical_cpus": psutil.cpu_count(), "physical_memory_bytes": psutil.virtual_memory().total,
            "packages": versions, "measurement": "process + recursive child RSS (shared pages may count more than once); no browser or uploader",
            "filesystem_cache": "OS cache uncontrolled; independent dataset imports do not imply disk-cold reads",
            "API": "none; diagnostics only"}


class ResourceMonitor:
    def __init__(self, temp_root: Path | None = None):
        self.temp_root = temp_root
        self.peak_rss = self.peak_temp = 0
        self.stop = threading.Event()
        self.thread = threading.Thread(target=self._run, daemon=True)

    def _sample(self):
        process = psutil.Process()
        processes = [process, *process.children(recursive=True)]
        total = 0
        for child in processes:
            try:
                total += child.memory_info().rss
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        self.peak_rss = max(self.peak_rss, total)
        if self.temp_root and self.temp_root.exists():
            total_temp = 0
            try:
                for file in self.temp_root.rglob("*"):
                    try:
                        if file.is_file():
                            total_temp += file.stat().st_size
                    except OSError:
                        pass
            except OSError:
                # Import failure/reset can remove an owned directory during traversal.
                pass
            self.peak_temp = max(self.peak_temp, total_temp)

    def _run(self):
        while not self.stop.is_set():
            self._sample()
            self.stop.wait(0.05)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *_):
        self.stop.set()
        self.thread.join(timeout=2)
        self._sample()


def expected_wide_guard(tool: str, observation: dict, manifest: dict) -> bool:
    summary = observation.get("summary", "").lower()
    return (manifest["profile"] == "wide_numeric" and tool in {"duplicate_rows_check", "outlier_check", "correlation_check"}
            and observation.get("status") == "skipped" and "column" in summary
            and any(term in summary for term in ("limit", "most", "select")))


def check_expected(tool: str, observation: dict, manifest: dict) -> tuple[bool | None, str]:
    """Compare independent generator invariants, never re-run the tested algorithm."""
    if observation.get("status") != "ok":
        if expected_wide_guard(tool, observation, manifest):
            return None, "Expected wide-schema guard observed; exact count/statistics unassessed: " + observation.get("summary", "")
        if tool in {"outlier_check", "correlation_check", "constant_columns_check", "high_cardinality_check"} and observation.get("status") == "skipped" and manifest["profile"] != "wide_numeric":
            return None, "Explicit resource/coverage skip; statistical correctness unassessed: " + observation.get("summary", "")
        return False, observation.get("summary", "non-ok observation")
    data = observation.get("data", {})
    expected = manifest["expected"]
    if tool == "missing_values_check":
        observed = {row["column"]: row["missing_count"] for row in data.get("affected_columns", [])}
        wanted = {key: value for key, value in expected["null_counts"].items() if value}
        return observed == wanted, "Exact per-column null counts compared with generation manifest."
    if tool == "duplicate_rows_check":
        return data.get("duplicate_count") == expected["duplicate_count"], "Exact duplicate count compared with repeated-row construction."
    if tool == "class_imbalance_check":
        counts = {row["class"]: row["count"] for row in data.get("classes", [])}
        return counts == expected["class_counts"], "Exact class counts compared with generation manifest."
    if tool == "dataset_profile":
        return data.get("rows") == manifest["rows"] and data.get("columns") == manifest["columns"], "Shape compared with generation manifest."
    return None, "Executed; numerical/statistical correctness requires separate Pandas parity tests, not generator count invariants."


def benchmark_one(path: Path, manifest: dict, settings: Settings, tools: list[str], repetition: int,
                  output: Path, backend: str = "duckdb") -> list[dict]:
    started = time.perf_counter()
    run_id = f"{manifest['profile']}_{manifest['requested_mib']:g}MiB_r{repetition}_{time.time_ns()}"
    base = {"run_id": run_id, "utc_time": datetime.now(timezone.utc).isoformat(), "profile": manifest["profile"],
            "seed": manifest["seed"], "file_bytes": manifest["file_bytes"], "rows": manifest["rows"],
            "columns": manifest["columns"], "numeric_columns": len(manifest["numeric_columns"]), "backend": backend,
            "upload_included": False, "api_report_seconds": 0, "cache_state": "new handle; OS cache uncontrolled",
            "release_ingest_limit_seconds": settings.import_timeout_seconds}
    dataset = None
    rows, original = [], {"run": base, "manifest": manifest, "observations": []}
    owned_root = tempfile.TemporaryDirectory(prefix="csv-quality-benchmark-")
    monitor = ResourceMonitor(Path(owned_root.name))
    try:
        with patch.object(upload_store, "TEMP_ROOT", Path(owned_root.name)), monitor:
            before = time.perf_counter()
            with path.open("rb") as upload:
                dataset = load_dataset(upload, path.name, settings=settings, backend=backend)
            ingest = time.perf_counter() - before
            monitor._sample()
            shape_correct = (dataset.row_count == manifest["rows"] and len(dataset.columns) == manifest["columns"]
                             and dataset.fingerprint == manifest["sha256"])
            original["ingest"] = {"seconds": ingest, "shape_correct": shape_correct, "fingerprint_match": dataset.fingerprint == manifest["sha256"]}
            for tool in tools:
                before = time.perf_counter()
                observation = dataset.run_check(tool, target="label", settings=settings)
                duration = time.perf_counter() - before
                original["observations"].append({"tool": tool, "seconds": duration, "result": observation})
                correctness, reason = check_expected(tool, observation, manifest)
                correctness = correctness and shape_correct if correctness is not None else None
                execution = observation.get("execution", observation.get("metadata", {}))
                cache_before = time.perf_counter()
                repeated = dataset.run_check(tool, target="label", settings=settings)
                cache_duration = time.perf_counter() - cache_before
                repeat_execution = repeated.get("execution", repeated.get("metadata", {}))
                original.setdefault("cache_repeats", []).append({"tool": tool, "seconds": cache_duration, "result": repeated})
                threshold = 120 if tool in {"duplicate_rows_check", "outlier_check"} else 30
                rows.append({**base, "ingest_seconds": round(ingest, 6), "tool_name": tool,
                             "initial_60s_goal_pass": ingest <= 60,
                             "tool_seconds": round(duration, 6), "total_seconds": round(time.perf_counter() - started, 6),
                             "cache_hit": execution.get("cache_hit", False), "exactness": "unassessed" if observation.get("status") != "ok" else execution.get("exactness", "exact"),
                             "repeat_cache_hit": repeat_execution.get("cache_hit", False), "repeat_tool_seconds": round(cache_duration, 6),
                             "coverage": json.dumps(execution.get("coverage", {})), "correctness_pass": correctness,
                             "guard_pass": expected_wide_guard(tool, observation, manifest),
                             "budget_pass": ingest <= settings.import_timeout_seconds and duration <= threshold and observation.get("status") != "error",
                             "status": observation.get("status", "error"), "reason": reason})
    except Exception as exc:
        # Keep the entire attempt, but avoid local paths/provider-sensitive exception strings.
        original["error_type"] = type(exc).__name__
        original["error_message"] = str(exc).replace(owned_root.name, "[benchmark-temp]").replace(str(path.resolve()), path.name)
        original["cause_type"] = type(exc.__cause__).__name__ if exc.__cause__ else None
        rows.append({**base, "ingest_seconds": round(time.perf_counter() - started, 6), "tool_name": "import_or_run",
                     "initial_60s_goal_pass": time.perf_counter() - started <= 60,
                     "status": "error", "reason": original["error_message"], "correctness_pass": False, "budget_pass": False})
    finally:
        if dataset is not None:
            dataset.close()
        owned_root.cleanup()
        for row in rows:
            row["peak_app_and_worker_rss_bytes"] = monitor.peak_rss
            row["peak_temp_bytes"] = monitor.peak_temp
            row["budget_pass"] = bool(row.get("budget_pass")) and monitor.peak_rss <= 2 * 1024**3
        original["resources"] = {"peak_process_and_child_rss_bytes": monitor.peak_rss,
                                 "peak_owned_temp_bytes": monitor.peak_temp, "temp_measured": monitor.temp_root is not None}
        output.mkdir(parents=True, exist_ok=True)
        (output / f"{run_id}.json").write_text(json.dumps(original, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return rows


def write_verification_audit(output: Path) -> dict:
    """Re-evaluate saved observations with corrected guard rules; keep originals intact."""
    source = output / "benchmark_results.csv"
    with source.open(newline="", encoding="utf-8") as stream:
        original_rows = list(csv.DictReader(stream))
    verified_rows, adjusted, manifests, attempts = [], [], {}, {}
    for row in original_rows:
        updated = dict(row)
        raw_path = output / f"{row['run_id']}.json"
        raw = json.loads(raw_path.read_text(encoding="utf-8"))
        manifests[raw["manifest"]["sha256"]] = raw["manifest"]
        attempts[row["run_id"]] = {"run_id": row["run_id"], "profile": row["profile"], "file_bytes": int(row["file_bytes"]),
                                   "evidence": raw_path.name, "ingest_failed": bool(raw.get("error_type"))}
        observation = next((o["result"] for o in raw.get("observations", []) if o["tool"] == row["tool_name"]), None)
        if observation is None:
            correctness, reason, guarded = False, raw.get("error_message", raw.get("error_type", "Missing observation")), False
        else:
            correctness, reason = check_expected(row["tool_name"], observation, raw["manifest"])
            guarded = expected_wide_guard(row["tool_name"], observation, raw["manifest"])
            if correctness is not None:
                correctness = correctness and raw.get("ingest", {}).get("shape_correct", False) and raw.get("ingest", {}).get("fingerprint_match", False)
        updated.update(verified_correctness_pass=correctness, guard_pass=guarded,
                       verified_exactness="unassessed" if observation is None or observation.get("status") != "ok" else "exact",
                       verification_reason=reason)
        verified_rows.append(updated)
        if guarded:
            adjusted.append({"run_id": row["run_id"], "tool": row["tool_name"],
                             "original_correctness_pass": row.get("correctness_pass"), "verified_correctness_pass": correctness,
                             "guard_pass": True, "reason": reason, "original_evidence": raw_path.name})
    fields = list(dict.fromkeys(key for row in verified_rows for key in row))
    with (output / "benchmark_results_verified.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(verified_rows)
    audit = {"original_csv": source.name, "original_csv_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
             "verified_csv": "benchmark_results_verified.csv", "utc_time": datetime.now(timezone.utc).isoformat(),
             "policy": "Expected wide-schema skips validate the guard; exact duplicate counts/statistics remain unassessed. Original CSV and JSON unchanged.",
             "adjusted_guards": adjusted}
    (output / "benchmark_verification_audit.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
    manifest_record = {"scope": "All saved attempts, including original timeouts and revised release/risk runs.",
                       "fixture_manifests": list(manifests.values()), "attempt_count": len(attempts),
                       "required_independent_imports_per_fixture": 3, "attempts": list(attempts.values()),
                       "environment": json.loads((output / "environment.json").read_text(encoding="utf-8")),
                       "environment_snapshots": [p.name for p in sorted(output.glob("environment*.json"))],
                       "size_units": "MiB, complete records at or below requested bytes"}
    (output / "benchmark_manifest.json").write_text(json.dumps(manifest_record, indent=2, ensure_ascii=False), encoding="utf-8")
    groups = {}
    for row in verified_rows:
        groups.setdefault((row["profile"], int(row["file_bytes"])), []).append(row)
    lines = ["# Verified benchmark summary", "", "Original failed 60-second imports and original verifier judgments remain in benchmark_results.csv. This summary uses the separate verified CSV and audit; expected wide skips are guard passes with exact count correctness unassessed. Each statistical tool still requires independent small-fixture parity tests.", "", "| Profile | MiB | Successful imports | Import failures | Max successful ingest s | Peak sampled RSS MiB | Exact count checks passed | Expected guards | Actual count/shape failures |", "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for (profile, byte_count), group in groups.items():
        successful = [r for r in group if r["status"] == "ok"]
        import_failures = {r["run_id"] for r in group if r["tool_name"] == "import_or_run"}
        passed = sum(r["verified_correctness_pass"] is True for r in group)
        guards = sum(r["guard_pass"] for r in group)
        count_failures = sum(r["verified_correctness_pass"] is False and r["tool_name"] != "import_or_run" for r in group)
        peak = max(float(r.get("peak_app_and_worker_rss_bytes") or 0) for r in group) / 1024**2
        ingest = max((float(r["ingest_seconds"]) for r in successful), default=0)
        lines.append(f"| {profile} | {byte_count / 1024**2:.3f} | {len({r['run_id'] for r in successful})} | {len(import_failures)} | {ingest:.3f} | {peak:.1f} | {passed} | {guards} | {count_failures} |")
    lines.extend(["", "Peak RSS covers harness and recursive children, excludes uploader/browser memory. Filesystem cache and other desktop load were uncontrolled. Import gate was explicitly revised to 120 seconds; initial 60-second goal flags remain. Three required release imports exist per size/profile; additional diagnostic risk runs may increase import counts.", ""])
    (output / "benchmark_verified_summary.md").write_text("\n".join(lines), encoding="utf-8")
    return audit


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixtures", type=Path, nargs="+", required=True, help="Generated CSV paths; matching .manifest.json required")
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--tools", choices=TOOLS, nargs="+", default=list(TOOLS[:3]))
    parser.add_argument("--backend", choices=["auto", "pandas", "duckdb"], default="duckdb")
    parser.add_argument("--output-dir", type=Path, default=Path("docs/evaluation/phase3/benchmarks"))
    args = parser.parse_args()
    if args.runs < 1:
        parser.error("--runs must be positive")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    env = environment()
    (args.output_dir / "environment.json").write_text(json.dumps(env, indent=2), encoding="utf-8")
    settings = Settings(max_upload_mb=250, import_timeout_seconds=120)
    env["release_settings"] = {"max_upload_mb": 250, "import_timeout_seconds": 120, "initial_import_goal_seconds": 60,
                               "duckdb_memory_limit": settings.duckdb_memory_limit, "duckdb_threads": settings.duckdb_threads,
                               "peak_rss_release_limit_bytes": 2 * 1024**3}
    (args.output_dir / "environment.json").write_text(json.dumps(env, indent=2), encoding="utf-8")
    (args.output_dir / f"environment_{time.time_ns()}.json").write_text(json.dumps(env, indent=2), encoding="utf-8")
    results_path = args.output_dir / "benchmark_results.csv"
    if results_path.exists():
        with results_path.open(newline="", encoding="utf-8") as stream:
            all_rows = list(csv.DictReader(stream))
    else:
        all_rows = []
    new_rows = []
    for path in args.fixtures:
        manifest = json.loads(path.with_suffix(".manifest.json").read_text(encoding="utf-8"))
        for repetition in range(1, args.runs + 1):
            rows = benchmark_one(path, manifest, settings, args.tools, repetition, args.output_dir, args.backend)
            for row in rows:
                row["commit"] = env["commit"]
            all_rows.extend(rows)
            new_rows.extend(rows)
            print(f"{path.name} run {repetition}: " + ", ".join(f"{r['tool_name']}={r['status']} correct={r['correctness_pass']} gate={r['budget_pass']}" for r in rows), flush=True)
            # Flush after every attempt so interrupted long ladders preserve finished records.
            fields = list(dict.fromkeys(key for row in all_rows for key in row))
            with results_path.open("w", newline="", encoding="utf-8") as stream:
                writer = csv.DictWriter(stream, fieldnames=fields)
                writer.writeheader()
                writer.writerows(all_rows)
    (args.output_dir / "benchmark_manifest.json").write_text(json.dumps({"environment": env, "fixture_manifests": [json.loads(p.with_suffix(".manifest.json").read_text(encoding="utf-8")) for p in args.fixtures], "runs_per_fixture": args.runs}, indent=2, ensure_ascii=False), encoding="utf-8")
    groups = {}
    for row in all_rows:
        groups.setdefault((row["profile"], int(row["file_bytes"])), []).append(row)
    summary = ["# Measured Phase 3 benchmarks", "", "Sizes use MiB. Three independent imports are required for release acceptance. OS filesystem cache was uncontrolled. RSS includes harness and recursive children, excludes Streamlit upload/browser buffers. Temporary storage was sampled every 50 ms during import and checks. API/report latency is excluded. The initial 60-second import goal was revised explicitly to 120 seconds after observed validation timeouts; original failed attempts remain below.", "", "## All attempts, including initial 60-second failures", "", "| Profile | Actual MiB | Imports | Max ingest s | Max check s | Peak RSS MiB | Peak temp MiB | Count correctness failures | Budget failures |", "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for (profile, byte_count), group in groups.items():
        maxima = lambda name: max(float(row.get(name) or 0) for row in group)
        correctness_failures = sum(row.get("correctness_pass") in (False, "False") for row in group)
        budget_failures = sum(row.get("budget_pass") in (False, "False") for row in group)
        summary.append(f"| {profile} | {byte_count / 1024**2:.3f} | {len({r['run_id'] for r in group})} | {maxima('ingest_seconds'):.3f} | {maxima('tool_seconds'):.3f} | {maxima('peak_app_and_worker_rss_bytes') / 1024**2:.1f} | {maxima('peak_temp_bytes') / 1024**2:.1f} | {correctness_failures} | {budget_failures} |")
    summary.extend(["", "## Revised 120-second release attempts", "", "| Profile | Actual MiB | Independent imports | Max ingest s | Initial 60-second goal misses | Correctness failures | Release budget failures |", "| --- | --- | --- | --- | --- | --- | --- |"])
    for (profile, byte_count), group in groups.items():
        release = [row for row in group if str(row.get("release_ingest_limit_seconds", "")) in {"120", "120.0"}]
        if not release:
            continue
        initial_misses = len({r['run_id'] for r in release if r.get("initial_60s_goal_pass") in (False, "False")})
        correctness_failures = sum(r.get("correctness_pass") in (False, "False") for r in release)
        budget_failures = sum(r.get("budget_pass") in (False, "False") for r in release)
        summary.append(f"| {profile} | {byte_count / 1024**2:.3f} | {len({r['run_id'] for r in release})} | {max(float(r.get('ingest_seconds') or 0) for r in release):.3f} | {initial_misses} | {correctness_failures} | {budget_failures} |")
    summary.extend(["", "Count correctness checks compare generator null, duplicate and class invariants, plus shape/hash. Other tools are executed but require separate numerical/statistical parity tests; an empty correctness field is not a pass. Cache-repeat results and original observations are retained per attempt. Failed/skipped runs remain in the CSV and JSON.", ""])
    (args.output_dir / "benchmark_summary.md").write_text("\n".join(summary), encoding="utf-8")
    write_verification_audit(args.output_dir)
    return 1 if any(row.get("correctness_pass") is False or not row.get("budget_pass") for row in new_rows) else 0


if __name__ == "__main__":
    raise SystemExit(main())
