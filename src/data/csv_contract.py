"""Shared strict CSV semantics; stream all rows before choosing column types."""

from __future__ import annotations

import codecs
import csv
from dataclasses import dataclass
from pathlib import Path
import math
import time
from typing import Callable

from src.data.upload_store import UploadStore


CONTRACT_VERSION = "phase3-v1"
NULL_TOKENS = frozenset({"", "#N/A", "#N/A N/A", "#NA", "-1.#IND", "-1.#QNAN",
    "-NaN", "-nan", "1.#IND", "1.#QNAN", "<NA>", "N/A", "NA", "NULL", "NaN",
    "None", "n/a", "nan", "null"})


@dataclass(frozen=True)
class CSVMetadata:
    columns: tuple[str, ...]
    encoding: str
    row_count: int
    null_counts: dict[str, int]
    column_types: dict[str, str]
    preview_rows: tuple[tuple[str | None, ...], ...]
    warnings: tuple[str, ...] = ()


def detect_encoding(path: Path) -> str:
    for encoding in ("utf-8-sig", "cp1252"):
        decoder = codecs.getincrementaldecoder(encoding)(errors="strict")
        try:
            with path.open("rb") as source:
                while chunk := source.read(1024 * 1024):
                    decoder.decode(chunk)
                decoder.decode(b"", final=True)
            return encoding
        except UnicodeDecodeError:
            pass
    raise ValueError("Could not decode this CSV as UTF-8 or Windows-1252.")


def _headers(original: list[str]) -> tuple[tuple[str, ...], bool]:
    if not original or any(not value.strip() or value.startswith("Unnamed:") for value in original):
        raise ValueError("The CSV has an empty column header. Give every column a name.")
    if len(original) > 1000:
        raise ValueError("The CSV exceeds the 1,000-column schema limit.")
    if any(len(value.encode("utf-8")) > 256 for value in original):
        raise ValueError("Column headers must be at most 256 UTF-8 bytes.")
    used = set(original)
    seen: set[str] = set()
    output = []
    duplicate = False
    for value in original:
        if value in seen:
            duplicate = True
            number = 1
            while f"{value}.{number}" in used:
                number += 1
            renamed = f"{value}.{number}"
            used.add(renamed)
            output.append(renamed)
        else:
            seen.add(value)
            output.append(value)
    if len({value.casefold() for value in output}) != len(output):
        raise ValueError("Column headers must be unique ignoring letter case; rename the conflicting columns.")
    return tuple(output), duplicate


def normalize_csv(source: Path, store: UploadStore,
                  progress: Callable[[str], None] | None = None, cancel_event=None,
                  timeout_seconds: float | None = None) -> tuple[Path, CSVMetadata]:
    """Normalize null lexemes and headers with bounded Python row memory.

    Short rows are rejected just like long rows. Blank physical records are
    skipped. Quoted empty cells share empty-field null semantics. Numeric-looking
    identifiers with leading zeros and any mixed column remain text.
    """
    if progress:
        progress("Validating CSV and column types")
    encoding = detect_encoding(source)
    started = time.monotonic()
    normalized = store.path / "normalized.csv"
    warnings: list[str] = []
    if encoding == "cp1252":
        warnings.append("Decoded using Windows-1252 after UTF-8 failed.")
    # stdlib's default 128 KiB is too small for valid long text cells.
    csv.field_size_limit(16 * 1024 * 1024)
    try:
        with source.open("r", encoding=encoding, newline="") as incoming, normalized.open("w", encoding="utf-8", newline="") as outgoing:
            reader = csv.reader(incoming, strict=True)
            original = next((row for row in reader if row), None)
            if original is None:
                raise ValueError("The CSV file is empty.")
            columns, duplicate = _headers(original)
            if duplicate:
                warnings.append("Duplicate column names were numbered; review the headers.")
            writer = csv.writer(outgoing, lineterminator="\n")
            writer.writerow(columns)
            null_counts = [0] * len(columns)
            types = ["int64"] * len(columns)
            non_null = [0] * len(columns)
            preserve_zero = set()
            mixed_columns = set()
            preview = []
            count = 0
            for row in reader:
                if count % 1000 == 0:
                    if cancel_event is not None and cancel_event.is_set():
                        from concurrent.futures import CancelledError
                        raise CancelledError("Dataset import cancelled.")
                    if timeout_seconds is not None and time.monotonic() - started > timeout_seconds:
                        raise ValueError("CSV validation exceeded its time limit. Try a smaller dataset.")
                if not row:
                    continue
                if len(row) != len(columns):
                    raise ValueError(f"Malformed CSV: record {count + 2} has {len(row)} fields; expected {len(columns)}.")
                values: list[str | None] = []
                for index, value in enumerate(row):
                    if value in NULL_TOKENS:
                        null_counts[index] += 1
                        values.append(None)
                        continue
                    values.append(value)
                    non_null[index] += 1
                    if types[index] == "object":
                        continue
                    token = value.strip()
                    unsigned = token[1:] if token.startswith(("+", "-")) else token
                    ascii_token = token.isascii()
                    if ascii_token and unsigned.isdigit():
                        if len(unsigned) > 1 and unsigned[0] == "0":
                            types[index] = "object"
                            preserve_zero.add(columns[index])
                        # Every integer with <=18 digits fits signed64. Only
                        # boundary lexemes need the comparatively costly int().
                        elif len(unsigned) > 19 or (len(unsigned) == 19 and not -(2**63) <= int(token) < 2**63):
                            types[index] = "object"
                    elif ascii_token and "_" not in token:
                        try:
                            number = float(token)
                            # Only the exact contract null tokens become null;
                            # whitespace-wrapped NaN remains a textual lexeme.
                            types[index] = "object" if math.isnan(number) else "float64"
                        except ValueError:
                            types[index] = "object"
                    else:
                        types[index] = "object"
                    if types[index] == "object" and non_null[index] > 1 and columns[index] not in preserve_zero:
                        mixed_columns.add(columns[index])
                writer.writerow(["" if value is None else value for value in values])
                if count < 10:
                    preview.append(tuple(values))
                count += 1
                if count % 10000 == 0:
                    outgoing.flush()
                    store.check_space()
                    if progress:
                        progress(f"Validating CSV: {count:,} rows")
            if count == 0:
                raise ValueError("The CSV has no data rows.")
            for index in range(len(columns)):
                if not non_null[index] or (types[index] == "int64" and null_counts[index]):
                    types[index] = "float64"
            if preserve_zero:
                warnings.append("Preserved leading-zero numeric identifiers as text: " + ", ".join(sorted(preserve_zero)[:10]))
            if mixed_columns:
                warnings.append("Retained numeric/text mixed columns as text without coercing values: " + ", ".join(sorted(mixed_columns)[:10]))
            store.check_space()
            metadata = CSVMetadata(columns, encoding, count, dict(zip(columns, null_counts)),
                dict(zip(columns, types)), tuple(preview), tuple(warnings))
            return normalized, metadata
    except csv.Error as exc:
        raise ValueError(f"Malformed CSV: {exc}") from exc
