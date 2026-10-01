"""Backend parity, actual interruption, quoting and coverage guards."""

from dataclasses import replace
from concurrent.futures import CancelledError
from io import BytesIO
from pathlib import Path
import threading

import pytest

import src.data.backends.duckdb_backend as backend_module
from src.config import Settings
from src.data.csv_contract import normalize_csv
from src.data.backends.duckdb_backend import DuckDBDataset
from src.data.loader import load_dataset
from src.data.upload_store import UploadStore


SAMPLES = Path(__file__).resolve().parents[2] / "data" / "samples"
CHECKS = ["dataset_profile", "missing_values_check", "duplicate_rows_check",
          "constant_columns_check", "high_cardinality_check", "outlier_check",
          "class_imbalance_check", "correlation_check"]


def diagnostic_payload(result):
    return {k: result[k] for k in ("status", "tool", "summary", "data", "findings")}


@pytest.mark.parametrize("filename", ["clean_small.csv", "corrupted_missing_duplicates.csv",
                                     "corrupted_class_imbalance.csv", "corrupted_outliers_corr.csv"])
@pytest.mark.parametrize("check", CHECKS)
def test_all_eight_diagnostics_match_reference(filename, check):
    content = (SAMPLES / filename).read_bytes()
    pandas = load_dataset(BytesIO(content), filename, backend="pandas")
    duck = load_dataset(BytesIO(content), filename, backend="duckdb")
    try:
        target = "label" if "label" in duck.columns else None
        assert diagnostic_payload(duck.run_check(check, target)) == diagnostic_payload(pandas.run_check(check, target))
    finally:
        pandas.close()
        duck.close()


@pytest.mark.parametrize("check", CHECKS)
def test_sql_identifiers_nulls_finite_values_and_ties(check):
    content = ('"odd\"\"name",x,id,label,text,empty\n'
               '1,2,001,B,"café, first",\n'
               '2,4,002,A,"two\nlines",NA\n'
               '3,6,003,B,"quoted \"\"cell\"\"",NULL\n'
               '4,8,004,A,"two\nlines",\n'
               '5,10,005,B,last,\n'
               '100,200,006,A,end,\n'
               'inf,inf,007,B,end,\n'
               '-inf,-inf,008,A,last,\n'
               '1,2,001,B,"café, first",\n').encode("utf-8")
    pandas = load_dataset(BytesIO(content), "adversarial.csv", backend="pandas")
    duck = load_dataset(BytesIO(content), "adversarial.csv", backend="duckdb")
    try:
        assert diagnostic_payload(duck.run_check(check, "label")) == diagnostic_payload(pandas.run_check(check, "label"))
        assert duck.dtypes["id"] == "object"
        assert duck.preview().iloc[0]["id"] == "001"
    finally:
        pandas.close()
        duck.close()


def test_cache_is_isolated_and_invalidates_thresholds_and_target():
    duck = load_dataset(BytesIO((SAMPLES / "corrupted_outliers_corr.csv").read_bytes()), "x.csv", backend="duckdb")
    try:
        first = duck.run_check("correlation_check")
        assert first["execution"]["cache_hit"] is False
        first["data"]["pairs"].clear()  # caller mutation must not corrupt cache
        assert duck.run_check("correlation_check")["data"]["pairs"]
        assert duck.run_check("correlation_check")["execution"]["cache_hit"] is True
        changed = replace(Settings(), correlation_threshold=.5)
        assert duck.run_check("correlation_check", settings=changed)["execution"]["cache_hit"] is False
        assert duck.run_check("correlation_check", target="x")["execution"]["cache_hit"] is False
    finally:
        duck.close()


def test_wide_guards_and_explicit_subset_do_not_claim_full_scan():
    headers = ",".join(f"v{i}" for i in range(51))
    rows = "\n".join(",".join(str(j+i) for i in range(51)) for j in range(6))
    duck = load_dataset(BytesIO((headers + "\n" + rows + "\n").encode()), "wide.csv", backend="duckdb")
    owned = duck.storage.path
    try:
        for name in ("duplicate_rows_check", "outlier_check", "correlation_check"):
            result = duck.run_check(name)
            assert result["status"] == "skipped"
            assert result["execution"]["coverage"]["columns_checked"] == []
        subset = duck.run_check("correlation_check", columns=["v0", "v50"])
        assert subset["status"] == "ok"
        assert len(subset["data"]["pairs"]) == 1
        assert subset["execution"]["coverage"]["columns_checked"] == ["v0", "v50"]
        profile = duck.run_check("dataset_profile", target="v50")
        assert profile["data"]["truncated"] is True
        assert "v50" in profile["data"]["dtypes"]
        with pytest.raises(ValueError):
            duck.run_check("correlation_check", columns=["absent"])
    finally:
        duck.close()
    assert not owned.exists()
    duck.close()  # idempotent
    with pytest.raises(RuntimeError):
        duck.run_check("missing_values_check")


def test_real_query_timeout_interrupts_and_connection_remains_usable():
    duck = load_dataset(BytesIO(b"x\n1\n2\n"), "x.csv", backend="duckdb")
    normal = duck._duplicates
    try:
        def slow(target, settings, columns):
            duck._one("SELECT sum(sin(i)) FROM range(1000000000000) t(i)")
            return {}, []
        duck._duplicates = slow
        result = duck.run_check("duplicate_rows_check", settings=replace(Settings(), query_timeout_seconds=.01))
        assert result["status"] == "error"
        assert "interrupted" in result["summary"]
        duck._duplicates = normal
        result = duck.run_check("duplicate_rows_check")
        assert result["status"] == "ok"
        assert result["execution"]["cache_hit"] is False
    finally:
        duck.close()


def test_external_cancellation_and_configured_engine_limits():
    duck = load_dataset(BytesIO(b"x\n1\n2\n"), "x.csv", backend="duckdb")
    start = threading.Event()
    output = []
    try:
        assert duck._one("SELECT current_setting('threads')") == 2
        assert duck._one("SELECT current_setting('memory_limit')") == "953.6 MiB"
        assert duck._one("SELECT current_setting('max_temp_directory_size')") == "2.0 GiB"
        def slow(target, settings, columns):
            start.set()
            duck._one("SELECT sum(sin(i)) FROM range(1000000000000) t(i)")
            return {}, []
        duck._duplicates = slow
        worker = threading.Thread(target=lambda: output.append(duck.run_check("duplicate_rows_check")))
        worker.start()
        assert start.wait(timeout=2)
        # Ensure the engine entered its long query before delivering interruption.
        threading.Event().wait(.02)
        duck.interrupt()
        worker.join(timeout=5)
        assert not worker.is_alive()
        assert output[0]["status"] == "error"
        assert duck.run_check("missing_values_check")["status"] == "ok"
    finally:
        duck.close()


def test_numeric_coverage_ignores_categories_and_reports_selected_omissions():
    duck = load_dataset(BytesIO(b"x,y,z,label\n1,2,3,A\n2,4,6,B\n3,6,9,A\n4,8,12,B\n"), "x.csv", backend="duckdb")
    try:
        whole = duck.run_check("correlation_check")["execution"]
        assert whole["columns_omitted"] == 0
        assert whole["coverage"]["ignored_columns"] == ["label"]
        chosen = duck.run_check("correlation_check", columns=["x", "y"])["execution"]
        assert chosen["columns_omitted"] == 1
        assert chosen["coverage"]["columns_omitted"] == ["z"]
        target = duck.run_check("correlation_check", target="z")["execution"]
        assert target["columns_omitted"] == 0
        assert target["coverage"]["ignored_columns"] == ["z", "label"]
    finally:
        duck.close()


def test_exact_quantiles_preflight_a_holistic_allocation_limit():
    duck = load_dataset(BytesIO(b"x\n1\n2\n3\n100\n"), "x.csv", backend="duckdb")
    try:
        # Small synthetic engine budget exercises the same row-count admission rule.
        result = duck.run_check("outlier_check", settings=replace(Settings(), duckdb_memory_limit="100B"))
        assert result["status"] == "skipped"
        assert result["findings"] == []
        assert "memory budget" in result["summary"]
        assert result["execution"]["columns_omitted"] == 1
        assert duck.run_check("outlier_check")["status"] == "ok"
    finally:
        duck.close()


def test_import_cancellation_interrupts_owned_query_before_return(monkeypatch, tmp_path):
    store = UploadStore("x.csv", root=tmp_path)
    source = store.copy_upload(BytesIO(b"x\n1\n2\n"), max_bytes=1000)
    normalized, metadata = normalize_csv(source, store)
    connect = backend_module.duckdb.connect
    entered = threading.Event()
    cancellation = threading.Event()
    outcomes = []
    connections = []

    class SlowImportConnection:
        def __init__(self, real):
            self.real = real
            self.closed = False

        def execute(self, sql, *args):
            if sql.startswith("COPY ("):
                entered.set()
                return self.real.execute("SELECT sum(sin(i)) FROM range(1000000000000) t(i)")
            return self.real.execute(sql, *args)

        def interrupt(self):
            self.real.interrupt()

        def close(self):
            self.real.close()
            self.closed = True

    def wrapped_connect(*args, **kwargs):
        result = SlowImportConnection(connect(*args, **kwargs))
        connections.append(result)
        return result

    monkeypatch.setattr(backend_module.duckdb, "connect", wrapped_connect)

    def import_dataset():
        try:
            DuckDBDataset.from_csv(normalized, store, metadata, cancel_event=cancellation)
        except BaseException as exc:
            outcomes.append(exc)

    worker = threading.Thread(target=import_dataset)
    worker.start()
    try:
        assert entered.wait(timeout=2)
        cancellation.set()
        worker.join(timeout=5)
        assert not worker.is_alive()
        assert isinstance(outcomes[0], CancelledError)
        assert connections[0].closed
    finally:
        cancellation.set()
        worker.join(timeout=5)
        store.close()


def test_long_target_labels_skip_before_fetching_values_into_evidence():
    private = "é" * 200  # 400 UTF-8 bytes; character count alone is insufficient.
    content = ("label,x\n" + "\n".join(f"{private if i < 9 else 'other'},{i}" for i in range(10)) + "\n").encode()
    duck = load_dataset(BytesIO(content), "labels.csv", backend="duckdb")
    try:
        result = duck.run_check("class_imbalance_check", target="label")
        assert result["status"] == "skipped"
        assert result["data"]["maximum_label_bytes"] == 400
        assert result["findings"] == []
        assert private not in str(result)
        constants = duck.run_check("constant_columns_check")
        assert constants["status"] == "ok"
        # Constants never fetch dominant raw values, only counts and ratios.
        assert private not in str(constants)
    finally:
        duck.close()
