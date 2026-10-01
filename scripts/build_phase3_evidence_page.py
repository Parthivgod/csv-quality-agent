"""Build an offline screenshot page from the saved, verified benchmark evidence."""

from __future__ import annotations

import argparse
import csv
from html import escape
import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def build(input_dir: Path, output: Path) -> Path:
    summary_path = input_dir / "benchmark_verified_summary.md"
    csv_path = input_dir / "benchmark_results_verified.csv"
    audit_path = input_dir / "benchmark_verification_audit.json"
    summary = summary_path.read_text(encoding="utf-8")
    table = []
    for line in summary.splitlines():
        if not line.startswith("| ") or line.startswith("| Profile") or line.startswith("| ---"):
            continue
        values = [value.strip() for value in line.strip().strip("|").split("|")]
        if len(values) == 9:
            table.append(values)
    if not table:
        raise ValueError("Verified summary has no benchmark table.")
    with csv_path.open(encoding="utf-8", newline="") as source:
        records = list(csv.DictReader(source))
    csv_groups = {(row["profile"], f"{round(int(row['file_bytes']) / 1024**2, 3):.3f}")
                  for row in records}
    table_groups = {(row[0], row[1]) for row in table}
    if csv_groups != table_groups:
        raise ValueError("Verified summary profile/size groups do not match the verified CSV.")
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    verified_date = escape(audit["utc_time"].split("T", 1)[0])
    rows = []
    for profile, mib, imported, failed, ingest, rss, counts, guards, incorrect in table:
        cells = [profile.replace("_", " "), mib, imported, failed,
                 f"{float(ingest):.2f} s", f"{float(rss):,.1f}", counts, guards, incorrect]
        rendered = []
        for index, value in enumerate(cells):
            attributes = ' class="failure"' if index == 3 and int(failed) else ""
            rendered.append(f"<td{attributes}>{escape(value)}</td>")
        rows.append("<tr>" + "".join(rendered) + "</tr>")
    groups_250 = sum(float(row[1]) == 250 for row in table)
    maximum_rss = max(float(row[5]) for row in table)
    relative_dir = Path(os.path.relpath(input_dir, output.parent)).as_posix()
    links = [("Verified summary", summary_path.name), ("Verified CSV", csv_path.name),
             ("Verification audit", audit_path.name), ("Original results", "benchmark_results.csv")]
    source_links = " · ".join(f'<a href="{escape(relative_dir + "/" + filename)}">{label}</a>'
                              for label, filename in links)
    page = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Phase 3 — measured backend benchmark evidence</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#f4f6fa;color:#17243a;font:13px/1.45 system-ui,Segoe UI,sans-serif}
main{max-width:1120px;margin:auto;padding:20px 22px}h1{font-size:24px;line-height:1.2;margin:0 0 5px}
.subtitle{margin:0;color:#53657c}.stats{display:flex;gap:24px;flex-wrap:wrap;margin:14px 0 12px}
.stat strong{display:inline-block;font-size:20px;color:#17509c;margin-right:5px}.stat{color:#526178}
.notice{border-left:4px solid #cf9120;background:#fff4d9;padding:9px 12px;margin:0 0 12px;color:#583f12}
.notice strong{color:#46300b}.table-wrap{overflow:auto;border:1px solid #d6dfeb;border-radius:8px;background:white}
table{border-collapse:collapse;width:100%;font-size:12px}th,td{padding:8px 9px;border-bottom:1px solid #e7ecf3;text-align:right;white-space:nowrap}
th{background:#e8eef7;color:#304560;font-weight:650;font-size:11px;line-height:1.25}th:first-child,td:first-child{text-align:left}
tbody tr:last-child td{border-bottom:0}tbody tr:nth-child(even){background:#f8fafd}.failure{color:#944d04;font-weight:700;background:#fff0d2}
.notes{margin:12px 0 6px;color:#465973;font-size:12px}.notes p{margin:5px 0}.sources{font-size:11px;color:#627289}a{color:#1b56a1}
@media(max-width:700px){main{padding:16px}.stats{gap:10px 20px}h1{font-size:21px}}
</style></head><body><main>
<h1>Measured CSV backend results</h1>
<p class="subtitle">Phase 3 · DuckDB CLI benchmark · verified __DATE__ · saved evidence, no simulated metrics</p>
<div class="stats"><span class="stat"><strong>__GROUPS__</strong> size/profile groups</span>
<span class="stat"><strong>__LARGE__</strong> profiles at 250 MiB</span>
<span class="stat"><strong>__RSS__ MiB</strong> maximum sampled process RSS</span></div>
<div class="notice"><strong>Import budget: 120 seconds for release; initial goal: 60 seconds.</strong>
Six initial tall-data import failures remain in the evidence. Successful ingest maxima include later release and risk runs.</div>
<div class="table-wrap"><table><thead><tr><th>Profile</th><th>Size<br>MiB</th><th>Successful<br>imports</th><th>Failed<br>imports</th>
<th>Slowest successful<br>ingest</th><th>Peak sampled<br>RSS MiB</th><th>Exact count<br>checks passed</th><th>Expected<br>guards</th><th>Count/shape<br>failures</th></tr></thead>
<tbody>__ROWS__</tbody></table></div>
<div class="notes"><p><strong>Memory scope:</strong> harness process and recursive children. Streamlit uploader and browser memory are excluded;
this table does not establish end-to-end upload memory. Filesystem cache and other desktop load were uncontrolled.</p>
<p><strong>Correctness scope:</strong> expected wide-schema skips validate guards; the skipped duplicate count remains unassessed.
Statistical tools have independent small-fixture parity tests; these scale runs do not independently prove their statistics.
At least three release imports per size/profile were recorded; extra risk runs can increase the count.</p></div>
<p class="sources">Source evidence: __LINKS__</p>
</main></body></html>"""
    replacements = {"__DATE__": verified_date, "__GROUPS__": str(len(table)),
        "__LARGE__": str(groups_250), "__RSS__": f"{maximum_rss:,.1f}",
        "__ROWS__": "\n".join(rows), "__LINKS__": source_links}
    for key, value in replacements.items():
        page = page.replace(key, value)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(page, encoding="utf-8")
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=ROOT / "docs/evaluation/phase3/benchmarks")
    parser.add_argument("--output", type=Path, default=ROOT / "docs/evaluation/phase3/benchmark_view.html")
    args = parser.parse_args()
    print(build(args.input_dir, args.output))
