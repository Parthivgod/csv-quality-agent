"""Regenerate the committed architecture diagram (requires Pillow)."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


OUT = Path(__file__).resolve().parents[1] / "docs/assets/csv_agent_architecture.png"
image = Image.new("RGB", (1800, 620), "#f8fafc")
draw = ImageDraw.Draw(image)
font_path = Path("C:/Windows/Fonts/arial.ttf")
font = ImageFont.truetype(str(font_path), 25) if font_path.exists() else ImageFont.load_default()
small = ImageFont.truetype(str(font_path), 18) if font_path.exists() else ImageFont.load_default()
title = ImageFont.truetype(str(font_path), 34) if font_path.exists() else ImageFont.load_default()
draw.text((70, 34), "CSV Data Quality Triage Agent", fill="#102a43", font=title)


def box(x: int, y: int, w: int, lines: list[str], color: str = "#e4eef7") -> None:
    draw.rounded_rectangle((x, y, x + w, y + 122), radius=15, fill=color, outline="#52718c", width=2)
    for i, line in enumerate(lines):
        draw.text((x + 18, y + 22 + i * 31), line, fill="#102a43", font=font if i == 0 else small)


def arrow(x1: int, y1: int, x2: int, y2: int) -> None:
    draw.line((x1, y1, x2, y2), fill="#32688a", width=4)
    draw.polygon([(x2, y2), (x2 - 13, y2 - 8), (x2 - 13, y2 + 8)], fill="#32688a")


box(70, 170, 250, ["Streamlit UI", "CSV + question + target"])
box(390, 170, 270, ["CSV loader", "In-memory DataFrame"])
box(730, 170, 300, ["Context + agent", "PromptTemplate", "LangChain create_agent"])
box(1100, 170, 280, ["Diagnostic tools", "Pandas / NumPy", "Observable trace"])
box(1450, 170, 280, ["LCEL report chain", "PydanticOutputParser", "Validated report"])
for x1, x2 in [(320, 390), (660, 730), (1030, 1100), (1380, 1450)]:
    arrow(x1 + 5, 231, x2 - 8, 231)
draw.rounded_rectangle((730, 380, 1000, 514), radius=15, fill="#fff5dc", outline="#b17b31", width=2)
draw.text((749, 402), "Schema only to LLM", fill="#704a17", font=font)
draw.text((749, 443), "No raw CSV rows", fill="#704a17", font=small)
draw.line((870, 292, 870, 378), fill="#b17b31", width=3)
draw.text((78, 550), "Tools supply facts; the model selects checks and explains their results.", fill="#486581", font=small)
OUT.parent.mkdir(parents=True, exist_ok=True)
image.save(OUT)
