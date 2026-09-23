from pathlib import Path

import pytest

from src.data.loader import CSVLoadError, load_csv


def test_valid_sample_loads() -> None:
    path = Path("data/samples/corrupted_missing_duplicates.csv")
    loaded = load_csv(path.read_bytes(), path.name)
    assert loaded.frame.shape == (30, 4)
    assert loaded.encoding == "utf-8-sig"


@pytest.mark.parametrize("content", [b"", b"   ", b"a,b\n"])
def test_empty_or_header_only_rejected(content: bytes) -> None:
    with pytest.raises(CSVLoadError):
        load_csv(content, "bad.csv")


def test_malformed_and_oversize_rejected() -> None:
    with pytest.raises(CSVLoadError, match="Malformed"):
        load_csv(b"a,b\n1,2\n3,4,5\n", "bad.csv")
    with pytest.raises(CSVLoadError, match="upload limit"):
        load_csv(b"a\n" + b"1" * (1024 * 1024 + 1), "big.csv", max_upload_mb=1)


def test_duplicate_headers_are_preserved_with_suffix() -> None:
    loaded = load_csv(b"a,a\n1,2\n", "duplicate.csv")
    assert list(loaded.frame.columns) == ["a", "a.1"]
    assert loaded.warnings


def test_cp1252_fallback() -> None:
    loaded = load_csv("city\nCafé\n".encode("cp1252"), "encoding.csv")
    assert loaded.encoding == "cp1252"
    assert loaded.frame.iloc[0, 0] == "Café"
