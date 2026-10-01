"""Legacy bytes loader plus bounded disk-backed dataset ingestion."""

from dataclasses import dataclass
from io import BytesIO
from concurrent.futures import CancelledError

import pandas as pd

from src.config import Settings
from src.data.csv_contract import normalize_csv
from src.data.dataset import DatasetHandle
from src.data.upload_store import UploadStore, cleanup_abandoned


class CSVLoadError(ValueError):
    """A user-facing CSV validation error."""


@dataclass(frozen=True)
class LoadedCSV:
    filename: str
    frame: pd.DataFrame
    encoding: str
    warnings: tuple[str, ...] = ()


def load_csv(content: bytes, filename: str, max_upload_mb: int = 20) -> LoadedCSV:
    """Parse UTF-8 or Windows-1252 CSV bytes with explicit size and shape checks."""
    if not filename.lower().endswith(".csv"):
        raise CSVLoadError("Upload a .csv file.")
    if not content or not content.strip():
        raise CSVLoadError("The CSV file is empty.")
    if len(content) > max_upload_mb * 1024 * 1024:
        raise CSVLoadError(f"The CSV exceeds the {max_upload_mb} MB upload limit.")
    if b"\x00" in content:
        raise CSVLoadError("The file appears to be binary rather than CSV text.")

    last_error: Exception | None = None
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            frame = pd.read_csv(BytesIO(content), encoding=encoding, on_bad_lines="error")
            if len(frame.columns) == 0:
                raise CSVLoadError("The CSV has no columns.")
            if frame.empty:
                raise CSVLoadError("The CSV has no data rows.")
            if any(str(c).startswith("Unnamed:") for c in frame.columns):
                raise CSVLoadError("The CSV has an empty column header. Give every column a name.")
            warnings = []
            if any(str(c).rsplit(".", 1)[-1].isdigit() for c in frame.columns):
                warnings.append("Pandas may have numbered duplicate column names; review the headers.")
            if encoding == "cp1252":
                warnings.append("Decoded using Windows-1252 after UTF-8 failed.")
            return LoadedCSV(filename, frame, encoding, tuple(warnings))
        except UnicodeDecodeError as exc:
            last_error = exc
        except pd.errors.EmptyDataError as exc:
            raise CSVLoadError("The CSV has no readable columns or rows.") from exc
        except pd.errors.ParserError as exc:
            raise CSVLoadError(f"Malformed CSV: {exc}") from exc
    raise CSVLoadError("Could not decode this CSV as UTF-8 or Windows-1252.") from last_error


def load_dataset(upload, filename: str, settings: Settings | None = None,
                 backend: str = "auto", progress=None, cancel_event=None) -> DatasetHandle:
    """Copy, validate once and return a session-owned dataset.

    Streamlit keeps its original upload buffer; this function does not create a
    second full-file bytes object. Call close() on replacement/reset. Both
    backends share strict field counts, nulls, headers and full-column inference.
    """
    active = settings or Settings()
    if not filename.lower().endswith(".csv"):
        raise CSVLoadError("Upload a .csv file.")
    if backend not in {"auto", "pandas", "duckdb"}:
        raise CSVLoadError("Choose auto, pandas, or duckdb as the dataset backend.")
    cleanup_abandoned()
    store = UploadStore(filename, quota_bytes=getattr(active, "session_temp_limit_mb", 4096) * 1024**2)
    result = None
    try:
        source = store.copy_upload(upload, max_bytes=active.max_upload_mb * 1024**2,
                                   progress=progress, cancel_event=cancel_event)
        pandas_limit = getattr(active, "pandas_threshold_mb", 20)
        if backend == "pandas" and store.file_bytes > pandas_limit * 1024**2:
            raise CSVLoadError(f"The Pandas backend is limited to {pandas_limit} MB. Choose auto or DuckDB for larger files.")
        normalized, metadata = normalize_csv(source, store, progress=progress,
            cancel_event=cancel_event, timeout_seconds=getattr(active, "import_timeout_seconds", 60))
        selected = backend
        if selected == "auto":
            selected = "pandas" if store.file_bytes <= getattr(active, "pandas_threshold_mb", 20) * 1024**2 else "duckdb"
        if cancel_event is not None and cancel_event.is_set():
            raise CancelledError("Dataset import cancelled.")
        if progress:
            progress(f"Importing {selected} dataset")
        if selected == "pandas":
            from src.data.backends.pandas_backend import PandasDataset
            frame = pd.read_csv(normalized, encoding="utf-8", dtype=metadata.column_types,
                keep_default_na=False, na_values=[""], float_precision="round_trip")
            result = PandasDataset(frame, filename, storage=store, metadata=metadata, settings=active)
        else:
            from src.data.backends.duckdb_backend import DuckDBDataset
            result = DuckDBDataset.from_csv(normalized, store, metadata, active, cancel_event=cancel_event)
        if cancel_event is not None and cancel_event.is_set():
            result.close()
            raise CancelledError("Dataset import cancelled.")
        # The fingerprint and preview are retained; source duplicates no longer
        # need disk storage after either successful backend import.
        source.unlink(missing_ok=True)
        normalized.unlink(missing_ok=True)
        store.check_space()
        if progress:
            progress("Dataset ready")
        return result
    except BaseException as exc:
        if result is not None:
            result.close()
        else:
            store.close()
        if isinstance(exc, (CancelledError, KeyboardInterrupt, SystemExit)):
            raise
        if isinstance(exc, CSVLoadError):
            raise
        if isinstance(exc, (ValueError, pd.errors.ParserError, UnicodeError)):
            raise CSVLoadError(str(exc)) from exc
        raise CSVLoadError(f"Could not import CSV ({type(exc).__name__}).") from exc
