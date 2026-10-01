"""Owned temporary upload storage, bounded copying, and conservative cleanup."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
import time
from typing import BinaryIO, Callable
import uuid
import weakref

import psutil


TEMP_ROOT = Path(tempfile.gettempdir()) / "csv-quality-agent"
_ACTIVE: weakref.WeakValueDictionary = weakref.WeakValueDictionary()


class UploadStore:
    """Only this object's generated directory can be removed by close()."""

    def __init__(self, filename: str, *, root: Path | None = None,
                 quota_bytes: int = 4 * 1024**3) -> None:
        self.root = Path(root or TEMP_ROOT).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / ("session-" + uuid.uuid4().hex)
        self.path.mkdir()
        self._owned_path = self.path.resolve()
        self._ownership_verified = False
        self.filename = filename
        self.quota_bytes = quota_bytes
        self.fingerprint = ""
        self.file_bytes = 0
        self.closed = False
        self.marker = self.path / "owner.json"
        self.marker.write_text(json.dumps({"pid": os.getpid(), "created": time.time()}), encoding="utf-8")
        _ACTIVE[self.path] = self

    def copy_upload(self, stream: BinaryIO, *, max_bytes: int,
                    progress: Callable[[str], None] | None = None, cancel_event=None) -> Path:
        if progress:
            progress("Copying upload")
        source = self.path / "source.csv"
        digest = hashlib.sha256()
        original_position = stream.tell() if hasattr(stream, "tell") else None
        try:
            if hasattr(stream, "seek"):
                stream.seek(0)
            with source.open("wb") as output:
                while chunk := stream.read(1024 * 1024):
                    if cancel_event is not None and cancel_event.is_set():
                        from concurrent.futures import CancelledError
                        raise CancelledError("Dataset import cancelled.")
                    if not isinstance(chunk, bytes):
                        raise ValueError("Upload must be a binary stream.")
                    self.file_bytes += len(chunk)
                    if self.file_bytes > max_bytes:
                        raise ValueError("The CSV exceeds the upload limit.")
                    if b"\x00" in chunk:
                        raise ValueError("The file appears to be binary rather than CSV text.")
                    self.check_space(len(chunk))
                    output.write(chunk)
                    digest.update(chunk)
                    if progress:
                        progress("Copying upload")
            self.fingerprint = digest.hexdigest()
            self.touch()
            return source
        finally:
            if original_position is not None:
                stream.seek(original_position)

    def disk_bytes(self) -> int:
        return sum(p.stat().st_size for p in self.path.rglob("*") if p.is_file())

    def check_space(self, additional_bytes: int = 0) -> None:
        if self.disk_bytes() + additional_bytes > self.quota_bytes:
            raise ValueError("Session temporary-storage quota exceeded. Reset the dataset and try a smaller file.")
        if shutil.disk_usage(self.path).free < additional_bytes + 32 * 1024**2:
            raise ValueError("Insufficient free temporary disk space.")

    def touch(self) -> None:
        if not self.closed:
            self.marker.touch()

    def close(self) -> None:
        if self.closed:
            return
        # A concurrent read-only storage monitor can briefly hold a Windows
        # handle without FILE_SHARE_DELETE. Retry only transient access errors;
        # never broaden the verified cleanup target or declare success early.
        for attempt in range(11):
            resolved = self.path.resolve()
            if resolved != self._owned_path or resolved.parent != self.root or not resolved.name.startswith("session-"):
                raise ValueError("Refusing cleanup outside owned dataset storage.")
            if not self._ownership_verified:
                if not self.marker.is_file():
                    raise ValueError("Refusing cleanup outside owned dataset storage.")
                self._ownership_verified = True
            try:
                shutil.rmtree(resolved)
                break
            except FileNotFoundError:
                # Another close may have completed the same owned directory.
                if resolved.exists():
                    raise
                break
            except PermissionError:
                if attempt == 10:
                    raise
                time.sleep(0.05)
        _ACTIVE.pop(self.path, None)
        self.closed = True


def cleanup_abandoned(root: Path | None = None, ttl_seconds: int = 24 * 3600) -> int:
    """Clean abandoned same-process leases or directories with dead owners.

    Process inspection is read-only on Windows as well as POSIX. In particular,
    os.kill(pid, 0) is deliberately avoided: its Windows behavior is unsafe.
    """
    parent = Path(root or TEMP_ROOT).resolve()
    if not parent.exists():
        return 0
    removed = 0
    for candidate in parent.glob("session-*"):
        if candidate in _ACTIVE or candidate.is_symlink() or not candidate.is_dir():
            continue
        marker = candidate / "owner.json"
        if not marker.is_file() or time.time() - marker.stat().st_mtime < ttl_seconds:
            continue
        try:
            owner = json.loads(marker.read_text(encoding="utf-8"))
            pid = int(owner["pid"])
            if pid <= 0:
                continue
            if pid != os.getpid() and psutil.pid_exists(pid):
                continue
            if candidate.resolve().parent != parent:
                continue
            shutil.rmtree(candidate)
            removed += 1
        except (OSError, ValueError, KeyError, TypeError):
            continue
    return removed
