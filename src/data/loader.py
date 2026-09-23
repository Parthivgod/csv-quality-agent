"""Defensive CSV parsing without disk persistence."""

from dataclasses import dataclass
from io import BytesIO

import pandas as pd


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
