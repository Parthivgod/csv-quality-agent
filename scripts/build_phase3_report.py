"""Rebuild the four-page Phase 3 report from saved evidence, without API calls.

Requires ReportLab, Pillow and pypdf (provided by the Codex document runtime).
Run only after evaluation is finished; earlier attempts remain in the evidence.
"""

import argparse
from collections import defaultdict
import csv
from html import escape
import json
from pathlib import Path
import re

from PIL import Image as PILImage, ImageDraw, ImageFont
from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs" / "evaluation" / "phase3"
SUBMISSION = ROOT / "submission"
ASSETS = ROOT / "docs" / "assets"
BLUE = colors.HexColor("#173c62")
PALE = colors.HexColor("#edf3f8")


def latest_scenarios():
    selected = {}
    for path in sorted((EVIDENCE / "scenarios").glob("*_result.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        key = record["id"], record["mode"]
        if key not in selected or record["utc_time"] > selected[key]["utc_time"]:
            selected[key] = record
    return [selected[key] for key in sorted(selected)]


def latest_benchmarks():
    selected = {}
    for path in (EVIDENCE / "benchmarks").glob("*.json"):
        record = json.loads(path.read_text(encoding="utf-8"))
        if "run" not in record:
            continue
        run = record["run"]
        match = re.search(r"_r(\d+)_\d+$", run["run_id"])
        key = run["profile"], record["manifest"]["requested_mib"], int(match[1]) if match else run["run_id"]
        if key not in selected or run["utc_time"] > selected[key]["run"]["utc_time"]:
            selected[key] = record
    csv_path = EVIDENCE / "benchmarks" / "benchmark_results_verified.csv"
    if not csv_path.exists():
        csv_path = EVIDENCE / "benchmarks" / "benchmark_results.csv"
    rows = list(csv.DictReader(csv_path.open(encoding="utf-8", newline=""))) if csv_path.exists() else []
    grouped = defaultdict(list)
    for (profile, size, repeat), record in selected.items():
        grouped[profile, size].append(record)
    output = []
    for (profile, size), records in sorted(grouped.items(), key=lambda item: (item[0][1], item[0][0])):
        ids = {d["run"]["run_id"] for d in records}
        matched = [r for r in rows if r["run_id"] in ids]
        success = all(d.get("observations") and not d.get("error_type") for d in records)
        # Statistical observations are not independent count-truth passes. An
        # approved scope guard is also not a verified full-dataset statistic.
        judgments = [r.get("verified_correctness_pass", r.get("correctness_pass", "")) for r in matched]
        correctness = bool(matched) and any(str(v).lower() == "true" for v in judgments) and not any(str(v).lower() == "false" for v in judgments)
        guarded = any(r.get("guard_pass", "").lower() == "true" for r in matched)
        budgets = bool(matched) and all(r["budget_pass"].lower() == "true" for r in matched)
        output.append({"profile": profile, "size": size, "runs": len(records),
                       "ingest": max((d.get("ingest", {}).get("seconds", 0) for d in records), default=0),
                       "rss": max(d["resources"]["peak_process_and_child_rss_bytes"] for d in records) / 1024**2,
                       "temp": max(d["resources"]["peak_owned_temp_bytes"] for d in records) / 1024**2,
                       "status": ("guarded" if guarded else "pass") if success and correctness and budgets else "failed/limited",
                       "records": records})
    return output


def architecture():
    ASSETS.mkdir(parents=True, exist_ok=True)
    nodes = [
        (20, 25, "Streamlit upload", "Chunked copy + SHA-256"),
        (300, 25, "Strict CSV contract", "Encoding, rows, full-column types"),
        (580, 25, "DatasetHandle", "Pandas <=20 MiB / DuckDB + Parquet"),
        (580, 175, "Selected diagnostic tools", "8 exact checks + resource guards"),
        (300, 175, "Groq + LangChain agent", "gpt-oss-120b chooses checks"),
        (20, 175, "Compact schema + question", "Target / numeric subset / no raw rows"),
        (20, 325, "Observable tool trace", "Status, bounded evidence, coverage"),
        (300, 325, "LCEL + output parser", "Prompt | model | parser + one retry"),
        (580, 325, "Validated report + UI", "Exact issue matches, downloads"),
    ]
    edges = [(260, 65, 300, 65), (540, 65, 580, 65), (700, 105, 700, 175),
             (700, 105, 700, 145), (700, 145, 140, 145), (140, 145, 140, 175),
             (260, 215, 300, 215), (540, 215, 580, 215), (580, 240, 540, 240),
             (700, 255, 700, 295), (700, 295, 140, 295), (140, 295, 140, 325),
             (260, 365, 300, 365), (540, 365, 580, 365)]
    svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="840" height="430" viewBox="0 0 840 430">',
           '<rect width="840" height="430" fill="white"/>',
           '<defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8" fill="#173c62"/></marker></defs>']
    for x1, y1, x2, y2 in edges:
        svg.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#173c62" stroke-width="2" marker-end="url(#arrow)"/>')
    image = PILImage.new("RGB", (1680, 860), "white")
    draw = ImageDraw.Draw(image)
    font_path = Path("C:/Windows/Fonts/arial.ttf")
    font = ImageFont.truetype(str(font_path), 28) if font_path.exists() else ImageFont.load_default()
    small = ImageFont.truetype(str(font_path), 24) if font_path.exists() else ImageFont.load_default()
    for x1, y1, x2, y2 in edges:
        draw.line((x1*2, y1*2, x2*2, y2*2), fill="#173c62", width=4)
        if y1 == y2 and x2 > x1:
            draw.polygon([(x2*2,y2*2),(x2*2-14,y2*2-8),(x2*2-14,y2*2+8)], fill="#173c62")
        elif y1 == y2 and x2 < x1:
            draw.polygon([(x2*2,y2*2),(x2*2+14,y2*2-8),(x2*2+14,y2*2+8)], fill="#173c62")
        elif y2 > y1:
            draw.polygon([(x2*2,y2*2),(x2*2-8,y2*2-14),(x2*2+8,y2*2-14)], fill="#173c62")
    for x, y, title, subtitle in nodes:
        svg.extend([f'<rect x="{x}" y="{y}" width="240" height="80" rx="8" fill="#edf3f8" stroke="#173c62"/>',
                    f'<text x="{x+120}" y="{y+30}" text-anchor="middle" font-family="Arial,sans-serif" font-size="14" font-weight="bold" fill="#173c62">{escape(title)}</text>',
                    f'<text x="{x+120}" y="{y+54}" text-anchor="middle" font-family="Arial,sans-serif" font-size="12" fill="#253746">{escape(subtitle)}</text>'])
        draw.rounded_rectangle((x*2,y*2,(x+240)*2,(y+80)*2), radius=16, fill="#edf3f8", outline="#173c62", width=2)
        draw.text(((x+120)*2,(y+30)*2), title, font=font, fill="#173c62", anchor="mm")
        draw.text(((x+120)*2,(y+54)*2), subtitle, font=small, fill="#253746", anchor="mm")
    svg.append('</svg>')
    (ASSETS / "phase3_architecture.svg").write_text("\n".join(svg), encoding="utf-8")
    image.save(ASSETS / "phase3_architecture.png")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--test-count", type=int, required=True, help="Fresh pytest passed count, supplied after validation")
    parser.add_argument("--verified-limit-mb", type=int, required=True)
    parser.add_argument("--import-budget-seconds", type=int, default=120)
    parser.add_argument("--upload-evidence", type=Path)
    parser.add_argument("--draft", action="store_true", help="Write layout preview only under ignored tmp/pdfs")
    args = parser.parse_args()
    if args.test_count < 1:
        parser.error("A verified positive test count is required")
    if args.upload_evidence and not args.upload_evidence.is_file():
        parser.error("Upload evidence must refer to an existing saved measurement")
    upload = json.loads(args.upload_evidence.read_text(encoding="utf-8")) if args.upload_evidence else None
    if upload and not (upload.get("final") and upload.get("completed_upload") and upload.get("dataset", {}).get("rows")):
        parser.error("Upload measurement must verify a completed dataset, not an idle sampling window")
    scenarios, benchmarks = latest_scenarios(), latest_benchmarks()
    if args.verified_limit_mb >= 250 and not any(b["size"] == 250 and b["runs"] >= 3 and b["status"] == "pass" for b in benchmarks):
        parser.error("Do not advertise 250 MiB without three passing saved benchmark runs")
    architecture()
    destination = ROOT / "tmp" / "pdfs" if args.draft else SUBMISSION
    destination.mkdir(parents=True, exist_ok=True)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="ReportBody", fontName="Helvetica", fontSize=9.2, leading=12.3, spaceAfter=6, textColor=colors.HexColor("#243746")))
    styles.add(ParagraphStyle(name="ReportHeading", fontName="Helvetica-Bold", fontSize=13, leading=16, spaceBefore=9, spaceAfter=7, textColor=BLUE))
    styles.add(ParagraphStyle(name="ReportTitle", fontName="Helvetica-Bold", fontSize=21, leading=25, spaceAfter=10, textColor=BLUE))
    styles.add(ParagraphStyle(name="Cell", fontName="Helvetica", fontSize=8.2, leading=10.8, textColor=colors.HexColor("#243746")))
    story, markdown = [], []

    def heading(text, title=False):
        story.append(Paragraph(escape(text), styles["ReportTitle" if title else "ReportHeading"]))
        markdown.extend([("# " if title else "## ") + text, ""])

    def paragraph(text):
        story.append(Paragraph(escape(text), styles["ReportBody"]))
        markdown.extend([text, ""])

    def table(headers, rows, widths):
        payload = [[Paragraph(escape(str(c)), styles["Cell"]) for c in row] for row in [headers, *rows]]
        item = Table(payload, colWidths=widths, hAlign="LEFT", repeatRows=1)
        item.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,0), PALE), ("VALIGN", (0,0), (-1,-1), "TOP"),
                                  ("LINEBELOW", (0,0), (-1,0), .7, BLUE),
                                  ("LINEBELOW", (0,1), (-1,-1), .25, colors.HexColor("#d7e0e8")),
                                  ("LEFTPADDING", (0,0), (-1,-1), 6), ("RIGHTPADDING", (0,0), (-1,-1), 6),
                                  ("TOPPADDING", (0,0), (-1,-1), 5), ("BOTTOMPADDING", (0,0), (-1,-1), 5)]))
        story.extend([item, Spacer(1,8)])
        markdown.extend(["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"])
        markdown.extend("| " + " | ".join(str(c).replace("|", "/") for c in row) + " |" for row in rows)
        markdown.append("")

    def page():
        story.append(PageBreak())
        markdown.extend(["<!-- page break -->", ""])

    heading("CSV Data Quality Triage Agent", True)
    paragraph("Lab 9 - Activity 2 | Phase 3 technical report | 1 October 2026" + (" | DRAFT" if args.draft else ""))
    heading("1. Problem and implemented workflow")
    paragraph("CSV defects can distort machine-learning preparation. The application answers a user's diagnostic question using selected deterministic checks, with evidence and contextual recommendations. It does not clean datasets or train models. The local release upload limit is " + str(args.verified_limit_mb) + " MiB (MiB = 1,048,576 bytes); supported shapes and measured boundaries are reported on page 4.")
    story.append(Image(str(ASSETS / "phase3_architecture.png"), width=500, height=256))
    story.append(Paragraph("Figure 1. Local dataset access, selective LLM-tool interaction, and evidence-validated reporting.", styles["ReportBody"]))
    markdown.extend(["![Architecture](../docs/assets/phase3_architecture.png)", "", "Figure 1. Implemented selective tool workflow.", ""])
    heading("LangChain components and external API")
    table(["Component", "Implemented role"], [
        ["ChatPromptTemplate", "Agent instructions include question, schema, target, allowed tools and budgets."],
        ["Agent + StructuredTool", "create_agent asks Groq openai/gpt-oss-120b to select from eight checks."],
        ["LCEL chain", "REPORT_PROMPT | model | StrOutputParser produces candidate report JSON."],
        ["PydanticOutputParser", "Validates report shape; issue fields must exactly match emitted tool findings; one repair attempt."],
    ], [125, 375])
    paragraph("The Groq API is accessed through langchain-groq using an ignored root .env key. Raw datasets and row previews stay local. Schema, questions, aggregate evidence and categorical class labels can reach the provider; these summaries can still contain sensitive information. Observable tool events are displayed; model reasoning is not recorded.")

    page()
    heading("2. Implementation and exact diagnostics")
    paragraph("The uploader is copied and hashed in chunks once. Strict validation handles UTF-8/BOM and Windows-1252, rejects inconsistent fields and empty headers, numbers duplicate names, preserves leading-zero identifiers, and examines complete columns before type selection. Both engines share this contract. Small files use the Pandas reference; larger files use DuckDB and typed Parquet in an app-owned OS temporary directory.")
    table(["Diagnostic", "Evidence and correctness rule"], [
        ["Profile", "Rows/types/nulls and exact distinct counts; at most 50 visible columns with the selected target retained."],
        ["Missing", "Exact null counts and percentages; existing 5%/30% severity thresholds."],
        ["Duplicates", "Rows minus distinct complete rows; nulls equal; context required before removal."],
        ["Constants", "Distinct categories include null; near-constant dominant fraction at least 95%."],
        ["Cardinality", "Eligible categorical or identifier-named columns; at least 20 observations and 90% unique ratio."],
        ["Outliers", "Finite numeric values, exact Type-7 quartiles and 1.5 x IQR bounds; at least four observations."],
        ["Imbalance", "Selected target; exact class counts; ratio 3/9 thresholds; unsuitable/long-label targets skipped."],
        ["Correlation", "Exact finite pairwise Pearson r; target excluded; |r| at least 0.95; does not establish leakage."],
    ], [92,408])
    heading("Execution controls and evidence integrity")
    paragraph("An owned background job admits one heavy operation. DuckDB uses a 1 GB memory setting, two threads and 2 GiB spill allowance; the session storage quota is 4 GiB. Query cancellation interrupts the connection and waits for active work before cleanup. Reset, replacement and failed import close handles; abandoned storage cleanup checks ownership. Memory settings do not guarantee whole-process RSS.")
    paragraph("Numeric scans require at most 20 selected columns; full-row duplicates are guarded above 50 columns. Exact quartiles use one shared aggregate state plus a conservative allocation check. A resource-limited operation is skipped or fails visibly; it never silently samples. Six executed checks, twelve attempted events, twenty emitted findings and a 16 KiB observation cap bound orchestration. Full local evidence is separately downloadable.")
    paragraph("Every issue is matched to the transmitted finding's tool, type, severity, column, evidence, impact and recommendation. Missing supported findings are restored. Summary and limitations are rebuilt from observed checks, errors and coverage. Deterministic caches include dataset, selected scope and thresholds; cache hits are disclosed.")

    page()
    heading("3. Evaluation and failure handling")
    paragraph(f"The current verified automated suite contains {args.test_count} passing tests. It includes backend parity, quoting/null/infinity/leading-zero cases, actual long-query interruption, import cancellation, cleanup and cache invalidation, and scripted full LangChain graph tests for both handles. Scripted tests establish wiring and evidence enforcement; live scenarios below measure real Groq behavior. Original attempts and retries remain saved.")
    names = {"T01":"Missing values", "T02":"Broad quality", "T03":"Target imbalance", "T04":"Outlier/correlation", "T05":"Unsuitable target", "T06":"Injected tool failure", "T07":"No target selected", "T08":"Clean missing check", "T09":"Header-only upload"}
    live = [s for s in scenarios if s["mode"] == "live Groq"]
    table(["ID / case", "Latest result", "Actual evidence / elapsed"], [[
        f"{s['id']} {names.get(s['id'], '')}", s["status"],
        (", ".join(s.get("actual_calls", [])) or "No tool calls") + f"; {s.get('latency_seconds',0):.2f} s"
    ] for s in live], [130,70,300])
    heading("Observed challenge and controlled failure")
    paragraph("Early live attempts included retained triage errors, repeated diagnostic calls in the controlled-failure case, and provider throttling. Automated adversarial tests separately confirm that unsupported report issues are rejected after a repair retry. Supported findings and limitations are preserved deterministically. Provider HTTP 429 is retained as a real external failure rather than counted as a passing tool-selection case. Latest per-case results appear above; history remains in the scenario index.")
    paragraph("T06 deliberately replaces only the duplicate diagnostic in the evaluation harness with an exception. This is controlled failure injection with live orchestration, not an organic dataset defect. Its trace records error, the report includes a limitation, and no duplicate count is invented. T05 uses record_id as an unsuitable target and should return a visible skipped check. Invalid uploads stop before triage; a missing target yields a target-selection limitation.")
    paragraph("Evidence: docs/evaluation/phase3/scenarios/*_result.json records hashes, prompts, target, provider/model, calls, status and latency; companion trace/report JSON records observations. scenario_results.md retains attempt history. T09 stops during input validation and makes no provider request even though it belongs to the live-mode harness. Unit and integration files provide API-free reproduction.")

    page()
    heading("4. Measured scaling, limits and submission")
    paragraph("The generator provides independent construction-based null, duplicate and class-count manifests. Latest attempts per profile/size/repeat show slowest import and peak RSS/storage below. Pass means verified counts/shape and resource gates, not independent verification of every large-file statistic. Guarded means expected skips with those statistics unassessed. OS caching is uncontrolled. The diagnostic harness excludes browser/uploader and API calls.")
    table(["Profile / MiB", "Runs", "Max import s", "Peak RSS MiB", "Peak temp MiB", "Gate"], [[
        f"{b['profile'].replace('_',' ')} / {b['size']:g}", str(b["runs"]),
        f"{b['ingest']:.2f}" if b["ingest"] else "not completed", f"{b['rss']:.1f}", f"{b['temp']:.1f}", b["status"]
    ] for b in benchmarks], [155,32,76,78,78,81])
    large = [b for b in benchmarks if b["size"] == 250 and b["status"] == "pass"]
    measured_tools = defaultdict(list)
    for group in large:
        for record in group["records"]:
            for observation in record.get("observations", []):
                measured_tools[observation["tool"]].append(observation["seconds"])
    if measured_tools:
        paragraph("Across the latest successful 250 MiB profiles, slowest measured selected-check times were " + "; ".join(f"{name.replace('_check','').replace('_',' ')} {max(values):.2f}s" for name, values in sorted(measured_tools.items())) + ". These are diagnostic times; provider/report latency is measured separately in the live scenario table.")
    all_checks = [record for group in large for record in group["records"]
                  if len({item["tool"] for item in record.get("observations", [])}) == 8
                  and all(item["result"]["status"] == "ok" for item in record["observations"])]
    if all_checks:
        paragraph("All eight diagnostics completed in the saved 250 MiB risk runs for " + ", ".join(sorted({r["run"]["profile"].replace("_", " ") for r in all_checks})) + ". Large-file constants, cardinality, outliers and correlation lack independent full-size statistical ground truth; successful execution is distinct from measured statistical correctness. Small-fixture backend parity provides separate evidence.")
    paragraph(f"The initial 60-second full-validation goal failed on 250 MiB tall data; those failed attempts are preserved. The release import budget was revised to {args.import_budget_seconds} seconds after observing the cost of strict full-column validation. Correctness, 2 GiB application/worker RSS and other declared gates are still required; changing the time budget is explicitly documented, not a claim that the initial goal passed.")
    if upload:
        data = upload["dataset"]
        paragraph(f"Actual browser upload: {data['file_bytes']:,} bytes, {data['rows']:,} rows and {data['column_count']} columns loaded into DuckDB in {data['import_seconds']:.3f}s, excluding HTTP transfer. Sampled peak app/worker RSS was {upload['peak_app_and_worker_rss_bytes']/1024**2:.2f} MiB including the Streamlit upload buffer; browser RSS was excluded. A live Groq missing-value run took {upload['live_run_seconds']:.4f}s. This is one desktop upload, not a concurrency test. Original downloaded evidence and resource record are in docs/evaluation/phase3/ui/.")
    paragraph("Streamlit UploadedFile retains an in-memory buffer. Disk-backed analysis avoids full DataFrames and extra complete byte copies but is not an end-to-end streaming upload service. The demonstrated envelope concerns tested shapes, not every possible 250 MiB CSV. Wider schemas, huge labels, holistic quartile allocations, disk pressure and provider rate limits can lead to explicit skips/errors. Outliers, duplicates and correlations require domain interpretation.")
    heading("Reproducibility and remaining human deliverables")
    paragraph("Reproduce using README commands, saved environment/source hashes, and scripts/build_phase3_report.py with the verified test count. The user records the planned 6:30 two-case video. Confirm individual statements, the real feedback form, roster and late-submission instructions; the brief's deadline was 30 September 2026.")
    heading("Sources")
    paragraph("Assignment: docs/source/Lab 9_2026_27.docx (Activity 2, Phase 3 and rubric); Phase 1 proposal in docs/source. Technical references: docs.streamlit.io/develop/api-reference/widgets/st.file_uploader; duckdb.org/docs/current/guides/performance/how_to_tune_workloads; duckdb.org/docs/current/sql/functions/aggregates. Implementation, saved traces and benchmark manifests are the sources for measured claims.")

    def footer(canvas, doc):
        canvas.setStrokeColor(BLUE)
        canvas.line(47,40,548,40)
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(BLUE)
        canvas.drawString(47,27,"CSV Data Quality Triage Agent | Phase 3 | 1 October 2026")
        canvas.drawRightString(548,27,str(doc.page))
    pdf = destination / "Phase3_Technical_Report.pdf"
    doc = SimpleDocTemplate(str(pdf), pagesize=A4, leftMargin=47, rightMargin=47,
                            topMargin=39, bottomMargin=52, title="CSV Data Quality Triage Agent - Phase 3", author="Project team")
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    page_count = len(PdfReader(pdf).pages)
    if page_count != 4:
        raise RuntimeError(f"Technical report must be four pages; produced {page_count}")
    (destination / "Phase3_Technical_Report.md").write_text("\n".join(markdown), encoding="utf-8")
    results = ["# Phase 3 measured results", "", "Generated 1 October 2026 from saved evidence; latest attempts are summarized and original attempts retained.", "", f"Automated verification supplied after testing: **{args.test_count} passed**. [Saved test, dependency and compile results](evaluation/phase3/test_results.txt).", "", "## Live Groq scenarios", "", "| ID | Result | Calls | Seconds |", "| --- | --- | --- | --- |"]
    for s in live:
        results.append(f"| {s['id']} | {s['status']} | {', '.join(s.get('actual_calls', []))} | {s.get('latency_seconds',0):.2f} |")
    results.extend(["", "[All attempts and evidence](evaluation/phase3/scenarios/scenario_results.md)", "", "## Diagnostic benchmarks", "", "| Profile | MiB | Runs | Max import s | Peak RSS MiB | Peak temp MiB | Gate |", "| --- | --- | --- | --- | --- | --- | --- |"])
    for b in benchmarks:
        results.append(f"| {b['profile']} | {b['size']:g} | {b['runs']} | {b['ingest']:.2f} | {b['rss']:.1f} | {b['temp']:.1f} | {b['status']} |")
    results.extend(["", "[Verified benchmark CSV](evaluation/phase3/benchmarks/benchmark_results_verified.csv), [verification audit](evaluation/phase3/benchmarks/benchmark_verification_audit.json), and [original raw CSV](evaluation/phase3/benchmarks/benchmark_results.csv). Pass covers independently checked counts/shape and resource gates; statistical large-file correctness without independent truth remains unassessed. Guarded means expected scope skips, not computed exact statistics. Process plus child RSS excludes browser/uploader. OS cache uncontrolled. Latest run per profile/size/repeat selected; initial failed attempts remain in raw records.", "", f"Release upload limit recorded for this report: {args.verified_limit_mb} MiB. Release import budget: {args.import_budget_seconds}s. The original 60s import goal failed on 250MiB tall data; budget revision is documented and does not erase failure.", "", "The PDF includes latest recorded results. Video, real feedback form, roster/deadline confirmation and individually confirmed contribution statements remain human deliverables."])
    if upload:
        data = upload["dataset"]
        results.extend(["", "## Actual browser upload", "", f"Completed **{data['file_bytes']:,} bytes / {data['rows']:,} rows / {data['column_count']} columns** in DuckDB. Import **{data['import_seconds']:.3f}s**, excluding HTTP transfer; live Groq missing-value diagnosis **{upload['live_run_seconds']:.4f}s**. Sampled peak app/worker RSS **{upload['peak_app_and_worker_rss_bytes']/1024**2:.2f} MiB** includes the Streamlit buffer but excludes browser RSS. One desktop upload; OS cache and desktop load uncontrolled.", "", "[Original downloaded app evidence](evaluation/phase3/ui/large_evidence.json), [resource record](evaluation/phase3/ui/large_upload_resources.json), and [browser validation](evaluation/phase3/ui/UI_VALIDATION.md). Earlier idle/rejected sampling windows are not successful upload evidence."])
    if not args.draft:
        (ROOT / "docs" / "PHASE3_RESULTS.md").write_text("\n".join(results)+"\n", encoding="utf-8")
    print(json.dumps({"report": str(pdf), "pages": page_count, "latest_live_scenarios": len(live), "benchmark_groups": len(benchmarks)}))


if __name__ == "__main__":
    main()
