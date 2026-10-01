"""Contract, ownership and cache tests for actual dataset ingestion."""

from concurrent.futures import CancelledError
from io import BytesIO
from pathlib import Path
from threading import Event
import gc
import os
import time

import pandas as pd
import pytest

from src.config import Settings
from src.data.dataset import DatasetHandle
from src.data.loader import CSVLoadError, load_dataset
from src.data import upload_store


@pytest.fixture
def isolated_storage(tmp_path, monkeypatch):
    root = tmp_path / "agent-storage"
    monkeypatch.setattr(upload_store, "TEMP_ROOT", root)
    return root


def test_shared_contract_preserves_late_text_identifiers_and_nulls(isolated_storage):
    content = b'id,value,empty,label\n001,1,,NA\n002,2,"",ok\n003,late,NULL,null\n'
    handle = load_dataset(BytesIO(content), "../untrusted.csv", Settings(), backend="pandas")
    try:
        assert isinstance(handle, DatasetHandle)
        assert handle.dtypes == {"id": "object", "value": "object", "empty": "float64", "label": "object"}
        assert handle.frame["id"].tolist() == ["001", "002", "003"]
        assert handle.null_counts == {"id": 0, "value": 0, "empty": 3, "label": 2}
        assert handle.row_count == 3
        assert handle.preview(100).shape == (3, 4)
        assert handle.storage.path.parent == isolated_storage
        assert not (handle.storage.path / "source.csv").exists()
        first = handle.run_check("missing_values_check")
        first["findings"].clear()
        second = handle.run_check("missing_values_check")
        assert second["execution"]["cache_hit"]
        assert second["findings"]
        assert not handle.run_check("missing_values_check", target="label")["execution"]["cache_hit"]
    finally:
        owned = handle.storage.path
        handle.close()
        handle.close()
    assert not owned.exists()


@pytest.mark.parametrize("content,match", [
    (b"a,b\n1\n", "Malformed"),
    (b"a,b\n1,2,3\n", "Malformed"),
    (b'a,b\n1,"unterminated\n', "Malformed"),
    (b"a\n", "no data rows"),
    (b"a\n\x00\n", "binary"),
    (b"a,\n1,2\n", "empty column header"),
    (b"Name,name\n1,2\n", "unique ignoring letter case"),
])
def test_rejected_import_cleans_owned_directory(content, match, isolated_storage):
    with pytest.raises(CSVLoadError, match=match):
        load_dataset(BytesIO(content), "bad.csv", Settings())
    assert not list(isolated_storage.glob("session-*"))


def test_encoding_multiline_duplicates_and_numeric_nulls(isolated_storage):
    content = 'name,name,name.1,count\n"Café\nCity",x,y,1\nTown,z,q,\n'.encode("cp1252")
    handle = load_dataset(BytesIO(content), "valid.csv", Settings())
    try:
        assert handle.encoding == "cp1252"
        assert handle.columns == ["name", "name.2", "name.1", "count"]
        assert handle.preview().iloc[0, 0] == "Café\nCity"
        assert handle.dtypes["count"] == "float64"
        assert handle.null_counts["count"] == 1
    finally:
        handle.close()


def test_cancellation_cleans_files_and_restores_stream_position(isolated_storage):
    event = Event()
    event.set()
    stream = BytesIO(b"a\n1\n")
    stream.seek(2)
    with pytest.raises(CancelledError):
        load_dataset(stream, "cancelled.csv", Settings(), cancel_event=event)
    assert stream.tell() == 2
    assert not list(isolated_storage.glob("session-*"))


def test_storage_cannot_cleanup_unowned_path_or_exceed_quota(isolated_storage, tmp_path):
    store = upload_store.UploadStore("data.csv", quota_bytes=10)
    with pytest.raises(ValueError, match="quota"):
        store.copy_upload(BytesIO(b"a\n" + b"x" * 100), max_bytes=1024)
    owned = store.path
    unrelated = tmp_path / "unrelated"
    unrelated.mkdir()
    store.path = unrelated
    with pytest.raises(ValueError, match="Refusing"):
        store.close()
    assert unrelated.exists()
    store.path = owned
    store.close()


def test_large_headers_and_wide_schema_rejected(isolated_storage):
    for content, match in [(b"x" * 257 + b"\n1\n", "256"),
                           ((",".join(f"c{i}" for i in range(1001)) + "\n").encode(), "1,000")]:
        with pytest.raises(CSVLoadError, match=match):
            load_dataset(BytesIO(content), "wide.csv", Settings())


def test_literal_spaced_nan_is_text_but_infinities_are_numeric(isolated_storage):
    handle = load_dataset(BytesIO(b"text,number\n NaN ,inf\nword,-inf\n"), "finite.csv", Settings())
    try:
        assert handle.dtypes == {"text": "object", "number": "float64"}
        assert handle.null_counts == {"text": 0, "number": 0}
        assert handle.frame.iloc[0, 0] == " NaN "
    finally:
        handle.close()


def test_python_specific_numeric_lexemes_remain_text(isolated_storage):
    handle = load_dataset(BytesIO("number,other\n1_000,١٢\n2000,٣\n".encode()), "lexemes.csv", Settings())
    try:
        assert handle.dtypes == {"number": "object", "other": "object"}
        assert handle.frame["number"].tolist() == ["1_000", "2000"]
    finally:
        handle.close()


def test_ttl_cleanup_preserves_active_lease_and_unmarked_paths(isolated_storage):
    store = upload_store.UploadStore("active.csv")
    owned = store.path
    old = time.time() - 100
    os.utime(store.marker, (old, old))
    unmarked = isolated_storage / "session-unmarked"
    unmarked.mkdir()
    assert upload_store.cleanup_abandoned(ttl_seconds=1) == 0
    assert owned.exists()
    del store
    gc.collect()
    assert upload_store.cleanup_abandoned(ttl_seconds=1) == 1
    assert not owned.exists()
    assert unmarked.exists()


def test_forced_pandas_cannot_bypass_large_dataset_resource_policy(isolated_storage):
    content = b"text\n" + b"valid long field" * 70000 + b"\n"
    with pytest.raises(CSVLoadError, match="Choose auto or DuckDB"):
        load_dataset(BytesIO(content), "large.csv", Settings(pandas_threshold_mb=1), backend="pandas")
    assert not list(isolated_storage.glob("session-*"))


def test_close_retries_transient_windows_sharing_lock_without_false_success(isolated_storage, monkeypatch):
    store = upload_store.UploadStore("locked.csv")
    owned = store.path
    real_remove = upload_store.shutil.rmtree
    attempts = []
    sleeps = []

    def temporarily_locked(path):
        attempts.append(path)
        assert not store.closed
        if len(attempts) <= 2:
            # Model a partially completed rmtree: the marker may already be
            # gone, while another child is transiently locked by a reader.
            store.marker.unlink(missing_ok=True)
            raise PermissionError(13, "Sharing violation", str(owned))
        real_remove(path)

    monkeypatch.setattr(upload_store.shutil, "rmtree", temporarily_locked)
    monkeypatch.setattr(upload_store.time, "sleep", sleeps.append)
    store.close()
    assert attempts == [owned, owned, owned]
    assert sleeps == [0.05, 0.05]
    assert store.closed
    assert not owned.exists()


def test_close_persistent_lock_is_bounded_and_preserves_open_state(isolated_storage, monkeypatch):
    store = upload_store.UploadStore("locked.csv")
    owned = store.path
    real_remove = upload_store.shutil.rmtree
    attempts = []
    sleeps = []

    def persistently_locked(path):
        attempts.append(path)
        store.marker.unlink(missing_ok=True)
        raise PermissionError(13, "Sharing violation", str(owned))

    monkeypatch.setattr(upload_store.shutil, "rmtree", persistently_locked)
    monkeypatch.setattr(upload_store.time, "sleep", sleeps.append)
    with pytest.raises(PermissionError):
        store.close()
    assert len(attempts) == 11
    assert len(sleeps) == 10
    assert not store.closed
    assert owned.exists()
    monkeypatch.setattr(upload_store.shutil, "rmtree", real_remove)
    store.close()
