"""Independent fixture invariants and full agent failure handling, without API calls."""

import hashlib
import json
import csv
from dataclasses import replace

import pandas as pd
import pytest

from scripts.generate_benchmarks import PROFILES, generate_fixture
from scripts.evaluate_phase3 import SCENARIOS, evaluate_scenario, sanitize_error
from scripts.benchmark_phase3 import check_expected, write_verification_audit


@pytest.mark.parametrize("profile", PROFILES)
def test_generator_ground_truth_matches_independent_reference(tmp_path, profile):
    path = tmp_path / f"{profile}.csv"
    manifest = generate_fixture(path, profile=profile, rows=301)
    frame = pd.read_csv(path)
    assert manifest["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert manifest["rows"] == len(frame) == 301
    assert manifest["expected"]["duplicate_count"] == int(frame.duplicated().sum()) == 3
    assert manifest["expected"]["null_counts"] == frame.isna().sum().to_dict()
    assert manifest["expected"]["class_counts"] == frame["label"].value_counts().to_dict()


def test_generator_size_ceiling_and_complete_quoted_rows(tmp_path):
    path = tmp_path / "quoted.csv"
    manifest = generate_fixture(path, size_mib=0.02, profile="quoted_unicode")
    assert 0 < path.stat().st_size <= 0.02 * 1024**2
    assert len(pd.read_csv(path)) == manifest["rows"]


def test_controlled_tool_error_completes_actual_agent_and_report(tmp_path):
    scenario = next(s for s in SCENARIOS if s.identifier == "T06")
    record = evaluate_scenario(scenario, tmp_path)
    assert record["status"] == "pass", record
    trace = json.loads((tmp_path / record["trace_file"]).read_text(encoding="utf-8"))
    report = json.loads((tmp_path / record["report_file"]).read_text(encoding="utf-8"))
    assert trace[0]["status"] == "error"
    assert "RuntimeError" in trace[0]["summary"]
    assert report["limitations"]
    assert not report["issues"]
    # Patch is removed; the subsequent ordinary run must return two duplicate rows.
    healthy = next(s for s in SCENARIOS if s.identifier == "T02")
    assert evaluate_scenario(healthy, tmp_path)["status"] == "pass"


def test_repeated_skipped_call_does_not_erase_controlled_failure(tmp_path):
    original = next(s for s in SCENARIOS if s.identifier == "T06")
    scenario = replace(original, tools=("duplicate_rows_check", "duplicate_rows_check"))
    record = evaluate_scenario(scenario, tmp_path)
    assert record["status"] == "pass", record
    trace = json.loads((tmp_path / record["trace_file"]).read_text(encoding="utf-8"))
    assert [event["status"] for event in trace] == ["error", "skipped"]


def test_error_export_redacts_credentials_without_damaging_urls(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-private-credential")
    text = 'test-private-credential gsk_123456789012 org_abcdef https://console.groq.com/docs C:\\Users\\Owner\\file.csv'
    safe = sanitize_error(text)
    assert "test-private-credential" not in safe and "gsk_123456789012" not in safe
    assert "org_abcdef" not in safe and "C:\\Users" not in safe
    assert "https://console.groq.com/docs" in safe


def test_wide_resource_guard_does_not_claim_exact_count_correctness():
    manifest = {"profile": "wide_numeric", "expected": {"duplicate_count": 3}}
    result = {"status": "skipped", "summary": "Select at most50columns for duplicate grouping."}
    correctness, reason = check_expected("duplicate_rows_check", result, manifest)
    assert correctness is None
    assert "unassessed" in reason


def test_verification_audit_preserves_original_failed_guard_judgment(tmp_path):
    original = tmp_path / "benchmark_results.csv"
    row = {"run_id": "wide1", "profile": "wide_numeric", "file_bytes": 100,
           "tool_name": "duplicate_rows_check", "correctness_pass": False, "status": "skipped",
           "ingest_seconds": 1, "peak_app_and_worker_rss_bytes": 1000}
    with original.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(row))
        writer.writeheader()
        writer.writerow(row)
    original_bytes = original.read_bytes()
    raw = {"manifest": {"profile": "wide_numeric", "sha256": "fixture-sha", "expected": {}},
           "observations": [{"tool": "duplicate_rows_check", "result": {
               "status": "skipped", "summary": "Exact full-row duplicates are limited to50columns; dataset wider."}}]}
    (tmp_path / "wide1.json").write_text(json.dumps(raw), encoding="utf-8")
    (tmp_path / "environment.json").write_text("{}", encoding="utf-8")
    audit = write_verification_audit(tmp_path)
    assert original.read_bytes() == original_bytes
    assert audit["adjusted_guards"][0]["guard_pass"] is True
    assert audit["adjusted_guards"][0]["verified_correctness_pass"] is None
    assert audit["original_csv_sha256"] == hashlib.sha256(original_bytes).hexdigest()
