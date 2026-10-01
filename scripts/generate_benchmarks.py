"""Generate deterministic CSVs in bounded chunks; ground truth comes from construction.

Sizes are MiB ceilings: writing ends at the last complete row fitting the target.
No Pandas or diagnostic implementation is used to derive manifests.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from pathlib import Path

PROFILES = ("tall_numeric", "high_unique_strings", "null_heavy", "quoted_unicode", "wide_numeric")
GENERATOR_VERSION = "phase3-v1"


def schema(profile: str) -> list[str]:
    if profile == "wide_numeric":
        return ["record_id", *[f"feature_{i:03d}" for i in range(200)], "label"]
    if profile == "null_heavy":
        return ["record_id", *[f"feature_{i:02d}" for i in range(12)], "label"]
    if profile == "high_unique_strings":
        return ["record_id", "category", "payload", "value", "nullable", "label"]
    if profile == "quoted_unicode":
        return ["record_id", "description", "city", "value", "nullable", "label"]
    return ["record_id", *[f"feature_{i:02d}" for i in range(10)], "nullable", "label"]


def construction_row(profile: str, index: int, seed: int) -> list[str]:
    """Every hundredth row repeats its predecessor; all other IDs are unique."""
    source = index - 1 if index % 100 == 99 else index
    label = "positive" if source % 10 == 9 else "negative"
    value = (source * 37 + seed) % 10007
    nullable = "" if source % 10 == 0 else str(value)
    if profile == "wide_numeric":
        return [str(source), *[str((source * (i + 3) + seed) % 100003) for i in range(200)], label]
    if profile == "null_heavy":
        return [str(source), *["" if (source + i) % 3 == 0 else str(value + i) for i in range(12)], label]
    if profile == "high_unique_strings":
        category = f"category_{source:012d}"
        payload = f"row_{source:012d}_seed_{seed}_" + "abcdefghijklmnopqrstuvwxyz" * 5
        return [str(source), category, payload, str(value), nullable, label]
    if profile == "quoted_unicode":
        description = f'Observation {source}: "quoted", café\nsecond line — विद्यार्थी'
        return [str(source), description, "मुंबई" if source % 2 else "Zürich", str(value), nullable, label]
    return [str(source), *[str((source * (i + 3) + seed) % 100003) for i in range(10)], nullable, label]


def generate_fixture(path: Path, size_mib: float = 1, profile: str = "tall_numeric", seed: int = 2026,
                     rows: int | None = None) -> dict:
    if profile not in PROFILES or size_mib <= 0 or (rows is not None and rows < 1):
        raise ValueError("Use a known profile, positive size, and positive explicit row count.")
    path.parent.mkdir(parents=True, exist_ok=True)
    header = schema(profile)
    nulls = dict.fromkeys(header, 0)
    classes = {"negative": 0, "positive": 0}
    digest = hashlib.sha256()
    target_bytes = int(size_mib * 1024 * 1024)
    byte_count = row_count = duplicates = 0
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(header)
    with path.open("wb") as stream:
        while True:
            batch = buffer.getvalue().encode("utf-8")
            if rows is None and row_count and byte_count + len(batch) > target_bytes:
                # Trim only complete CSV records, including quoted multiline records.
                while row_count and byte_count + len(batch) > target_bytes:
                    row_count -= 1
                    values = construction_row(profile, row_count, seed)
                    one = io.StringIO(newline="")
                    csv.writer(one, lineterminator="\n").writerow(values)
                    batch = batch[:-len(one.getvalue().encode("utf-8"))]
                    for column, value in zip(header, values):
                        nulls[column] -= value == ""
                    classes[values[-1]] -= 1
                    duplicates -= row_count % 100 == 99
                if batch:
                    stream.write(batch)
                    digest.update(batch)
                    byte_count += len(batch)
                break
            if batch:
                stream.write(batch)
                digest.update(batch)
                byte_count += len(batch)
            buffer.seek(0)
            buffer.truncate(0)
            if (rows is not None and row_count >= rows) or (rows is None and byte_count >= target_bytes and row_count):
                break
            # Flush at 512 rows: bounded memory even for wide or multiline fixtures.
            for _ in range(min(512, rows - row_count) if rows is not None else 512):
                values = construction_row(profile, row_count, seed)
                for column, value in zip(header, values):
                    nulls[column] += value == ""
                classes[values[-1]] += 1
                duplicates += row_count % 100 == 99
                writer.writerow(values)
                row_count += 1
    numeric = [name for name in header if name == "record_id" or name == "value" or name == "nullable" or name.startswith("feature_")]
    manifest = {
        "generator_version": GENERATOR_VERSION, "profile": profile, "seed": seed,
        "requested_mib": size_mib, "size_unit": "MiB = 1,048,576 bytes; last complete record at or below target",
        "file": path.name, "file_bytes": byte_count, "sha256": digest.hexdigest(),
        "rows": row_count, "columns": len(header), "column_names": header, "numeric_columns": numeric,
        "expected": {"null_counts": nulls, "duplicate_count": duplicates, "target": "label", "class_counts": classes},
        "ground_truth_source": "Deterministic row construction, counted while generating; independent of application diagnostics.",
    }
    path.with_suffix(".manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("data/benchmarks"))
    parser.add_argument("--sizes", type=float, nargs="+", default=[1], help="Maximum MiB. Full ladder: 1 20 50 100 250")
    parser.add_argument("--profiles", choices=PROFILES, nargs="+", default=["tall_numeric"])
    parser.add_argument("--seed", type=int, default=2026)
    args = parser.parse_args()
    for profile in args.profiles:
        for size in args.sizes:
            path = args.output_dir / f"{profile}_{size:g}MiB.csv"
            manifest = generate_fixture(path, size, profile, args.seed)
            print(f"{path}: {manifest['rows']:,} rows, {manifest['file_bytes']:,} bytes; manifest saved", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
