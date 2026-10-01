"""Session-owned background work; one shared slot bounds heavy app jobs."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from threading import BoundedSemaphore, Event, Lock
import time

_HEAVY_SLOT = BoundedSemaphore(1)

@dataclass
class BackgroundJob:
    kind: str
    cancel_event: Event = field(default_factory=Event)
    stage: str = "Starting"
    started: float = field(default_factory=time.monotonic)
    finished: float | None = None
    lock: Lock = field(default_factory=Lock, repr=False)
    future: object = None
    executor: object = None
    cancel_hook: object = None

    def progress(self, stage, *_args, **_kwargs):
        if self.cancel_event.is_set():
            raise RuntimeError("Operation cancelled.")
        with self.lock:
            self.stage = str(stage)

    def cancel(self):
        self.cancel_event.set()
        with self.lock:
            self.stage = "Cancelling; waiting for active work to stop"
        if self.cancel_hook:
            self.cancel_hook()

    @classmethod
    def start(cls, kind, work, cancel_hook=None):
        if not _HEAVY_SLOT.acquire(blocking=False):
            raise RuntimeError("Another analysis or import is active. Wait for it to finish, then try again.")
        job = cls(kind=kind, cancel_hook=cancel_hook)
        job.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="csv-triage")
        def execute():
            try:
                return work(job)
            finally:
                job.finished = time.monotonic()
                _HEAVY_SLOT.release()
        try:
            job.future = job.executor.submit(execute)
            job.future.add_done_callback(lambda _: job.executor.shutdown(wait=False))
        except Exception:
            _HEAVY_SLOT.release()
            job.executor.shutdown(wait=False)
            raise
        return job

    def wait(self, timeout=None):
        return self.future.result(timeout=timeout)
