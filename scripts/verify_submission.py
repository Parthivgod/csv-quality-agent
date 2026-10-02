"""Check the repository submission package without provider calls or benchmarks.

Uses only the Python standard library. Optional --output saves an audit record;
the default invocation is read-only. Human hand-in steps remain explicitly open.
"""

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[1]


def digest(path, mode="bytes"):
    if mode == "lf_normalized":
        return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    if mode != "bytes":
        raise ValueError("Unknown manifest hash mode")
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def package_path(relative):
    path = (ROOT / relative).resolve()
    if not path.is_relative_to(ROOT):
        raise ValueError("Package path must stay inside the repository")
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=ROOT / "submission/SUBMISSION_MANIFEST.json")
    parser.add_argument("--output", type=Path, help="Optional JSON audit destination")
    args = parser.parse_args()
    errors = []
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    tracked = set(subprocess.check_output(
        ["git", "ls-files", "-z"], cwd=ROOT).decode("utf-8").split("\0")) - {""}

    for item in manifest["files"]:
        relative = item["path"]
        path = package_path(relative)
        if relative not in tracked:
            errors.append(f"Deliverable is not staged/tracked: {relative}")
        if not path.is_file():
            errors.append(f"Missing deliverable: {relative}")
        elif (digest(path, item.get("hash_mode", "bytes")) != item["sha256"]
                or (item.get("hash_mode", "bytes") == "bytes" and path.stat().st_size != item["bytes"])):
            errors.append(f"Deliverable differs from verified manifest: {relative}")

    markdown_count = 0
    link_count = 0
    for relative in sorted(tracked):
        if not relative.endswith(".md") or relative.startswith("submission/archive/"):
            continue
        markdown_count += 1
        text = package_path(relative).read_text(encoding="utf-8")
        for destination in re.findall(r"\]\(([^)]+)\)", text):
            destination = unquote(destination.strip("<>").split("#", 1)[0])
            if not destination or re.match(r"^[a-zA-Z]+://", destination) or destination.startswith("mailto:"):
                continue
            link_count += 1
            target = (package_path(relative).parent / destination).resolve()
            if not target.is_relative_to(ROOT) or not target.exists():
                errors.append(f"Missing local link in {relative}: {destination}")
            elif target.is_file() and target.relative_to(ROOT).as_posix() not in tracked:
                errors.append(f"Local link points to an untracked file in {relative}: {destination}")

    # Compare configured keys privately; never include their values in output.
    configured_secrets = []
    env_path = ROOT / ".env"
    if env_path.is_file():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if "=" not in line or line.lstrip().startswith("#"):
                continue
            name, value = line.split("=", 1)
            value = value.strip().strip('"').strip("'")
            if any(word in name.upper() for word in ("KEY", "TOKEN", "SECRET")) and len(value) > 8:
                configured_secrets.append((name, value.encode("utf-8")))
    forbidden_parts = {".venv", "tmp", "__pycache__", ".pytest_cache"}
    for relative in sorted(tracked):
        path = Path(relative)
        if (relative in {".env", ".streamlit/secrets.toml"}
                or path.name.startswith("~$")
                or forbidden_parts.intersection(path.parts)
                or relative.startswith("data/benchmarks/")):
            errors.append(f"Local-only file is tracked: {relative}")
        content = package_path(relative).read_bytes()
        for name, value in configured_secrets:
            if value in content:
                errors.append(f"Configured secret {name} occurs in {relative}")
        if re.search(rb"\bgsk_[A-Za-z0-9]{20,}|\bsk-(?:proj-)?[A-Za-z0-9_-]{30,}", content):
            errors.append(f"Credential-shaped value occurs in {relative}")

    record = json.loads(package_path(manifest["video_validation"]).read_text(encoding="utf-8"))
    video = package_path("submission/Phase3_CSV_Data_Quality_Demo.mp4")
    if (not video.is_file() or digest(video) != record["sha256"]
            or video.stat().st_size != record["bytes"]
            or record["duration_seconds"] != 390.0 or record["tracks"] != ["vide"]
            or record["full_decode_exit"] != 0):
        errors.append("Silent demo differs from its original successful 6:30 validation")
    for item in record["fresh_run_evidence"]:
        path = package_path("submission/recording_evidence_20261001/" + item["file"])
        if not path.is_file() or digest(path) != item["sha256"]:
            errors.append(f"Recorded run export differs from original validation: {item['file']}")

    result = {
        "status": "pass" if not errors else "fail",
        "manifest": str(args.manifest.relative_to(ROOT)) if args.manifest.is_relative_to(ROOT) else args.manifest.name,
        "verified_artifacts": len(manifest["files"]),
        "checked_markdown_files": markdown_count,
        "checked_local_links": link_count,
        "credential_and_local_file_check": "completed",
        "video": {"duration_seconds": record["duration_seconds"], "audio_tracks": 0,
                  "integrity_matches_original_validation": not any("demo" in e for e in errors)},
        "pending_human_actions": manifest["pending_human_actions"],
        "errors": errors,
    }
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
