"""Sample an explicitly selected Streamlit process during real browser upload.

Does not include browser memory. Stop by creating --stop-file, or --seconds expiry.
The sampling window is not an ingestion-duration measurement.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import time

import psutil


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pid", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--stop-file", type=Path, required=True)
    parser.add_argument("--seconds", type=float, default=300)
    args = parser.parse_args()
    process = psutil.Process(args.pid)
    baseline = process.memory_info().rss
    started = time.monotonic()
    peak = baseline
    peak_temp = 0
    samples = 0
    temp_root = Path(tempfile.gettempdir()) / "csv-quality-agent"
    def record(final=False):
        output = {"utc_time": datetime.now(timezone.utc).isoformat(), "pid": args.pid,
                  "mode": "actual Streamlit browser upload and local backend; browser RSS excluded",
                  "sampling_interval_seconds": .05, "sampling_window_seconds": round(time.monotonic()-started,3),
                  "baseline_app_rss_bytes": baseline, "peak_app_and_worker_rss_bytes": peak,
                  "peak_owned_temp_bytes": peak_temp, "samples": samples, "final": final,
                  "rss_budget_bytes": 2*1024**3, "rss_budget_pass": peak <= 2*1024**3}
        args.output.parent.mkdir(parents=True, exist_ok=True)
        temp = args.output.with_suffix(".tmp")
        temp.write_text(json.dumps(output,indent=2),encoding="utf-8")
        temp.replace(args.output)
    while time.monotonic()-started < args.seconds and not args.stop_file.exists():
        try:
            children = process.children(recursive=True)
            active = [process, *children]
            pids = {item.pid for item in active}
            rss = 0
            for item in active:
                try:
                    rss += item.memory_info().rss
                except psutil.NoSuchProcess:
                    pass
            peak = max(peak,rss)
            disk = 0
            for marker in temp_root.glob("session-*/owner.json"):
                try:
                    if json.loads(marker.read_text(encoding="utf-8"))["pid"] in pids:
                        for file in marker.parent.rglob("*"):
                            if file.is_file():
                                disk += file.stat().st_size
                except (FileNotFoundError, OSError, json.JSONDecodeError):
                    pass
            peak_temp = max(peak_temp,disk)
            samples += 1
            if samples % 20 == 0:
                record()
        except psutil.NoSuchProcess:
            break
        time.sleep(.05)
    record(final=True)
    print(f"Saved {args.output}; peak RSS {peak/1024**2:.1f} MiB; budget pass={peak<=2*1024**3}")
    return 0 if peak<=2*1024**3 else 1

if __name__ == "__main__":
    raise SystemExit(main())
