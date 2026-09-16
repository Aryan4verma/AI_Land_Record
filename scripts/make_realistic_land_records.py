"""Generate realistic SPECIMEN land-record documents for OCR testing.

WHAT THIS IS
------------
High-fidelity synthetic Record of Rights / Pahani-style land records that
reproduce the things which actually break OCR on Indian land documents:

  * a guilloche security background that interferes with glyph strokes
  * diagonal microtext watermarking
  * a translucent rubber stamp rotated over live text
  * a handwritten-style signature crossing a printed line
  * dense small type in a ruled label:value table
  * bilingual pages (English + Devanagari, English + Gujarati)
  * a degraded variant with skew, sensor noise and reduced contrast

WHAT THIS IS NOT
----------------
It is NOT a copy of any government instrument. It deliberately carries no
state emblem, no real department name, no real certificate series, no real
notary seal and no real person's details. Every identifier and name is
fictitious, the issuing body is the fictional "Demo State", and every page is
marked SPECIMEN. None of that costs OCR realism: recognition difficulty comes
from the background, the seal, the type size and the script mix, not from
whose crest is printed at the top.

Language packs are chosen to match what this project actually has installed
(eng, hin, guj). Kannada/Marathi RTCs are intentionally not generated because
no `kan`/`mar` traineddata is present and they would simply fail.

Usage (from repo root):
    backend\\.venv\\Scripts\\python scripts\\make_realistic_land_records.py

Writes dataset/raw_documents/*.pdf + *.png, dataset/ground_truth/*.json and
merges entries into dataset/manifest.json.
"""
from __future__ import annotations

import json
import math
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from render_indic import Placer, degrade  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "dataset" / "raw_documents"
GT = ROOT / "dataset" / "ground_truth"
MANIFEST = ROOT / "dataset" / "manifest.json"

W, H = 1654, 2339          # A4 at 200 DPI
INK = (18, 22, 34)
RULE = (120, 128, 145)
SECURITY = (196, 176, 150)
SEAL_INK = (72, 46, 132)
SIG_INK = (24, 34, 92)

LATIN_BOLD = [r"C:\Windows\Fonts\arialbd.ttf", r"C:\Windows\Fonts\Arialbd.ttf"]
LATIN = [r"C:\Windows\Fonts\arial.ttf", r"C:\Windows\Fonts\Arial.ttf"]
INDIC = [r"C:\Windows\Fonts\Nirmala.ttc"]


def font(paths, size, index=0):
    for p in paths:
        if Path(p).is_file():
            try:
                return ImageFont.truetype(p, size, index=index)
            except Exception:
                continue
    return ImageFont.load_default()


# ---------------------------------------------------------------- content
def record_fields(script: str) -> list[tuple[str, str]]:
    """(label, value) pairs. Labels bilingual, values fictitious."""
    if script == "hin":
        return [
            ("District / जिला", "Demo District"),
            ("Taluk / तहसील", "Demo Tehsil"),
            ("Village / गाँव", "Demo Village"),
            ("Survey Number / सर्वे संख्या", "145/2"),
            ("Hissa Number / हिस्सा संख्या", "2B"),
            ("Khata Number / खाता संख्या", "123"),
            ("Khasra Number / खसरा संख्या", "78"),
            ("Owner Name / भू-धारक", "Ramesh Kumar Patel"),
            ("Father Name / पिता का नाम", "Suresh Kumar Patel"),
            ("Extent / क्षेत्रफल", "2.45 Hectare"),
            ("Land Class / भूमि वर्ग", "Agricultural / कृषि"),
            ("Mutation Number / उत्परिवर्तन", "M-2024-0091"),
            ("Record Date / अभिलेख दिनांक", "15-03-2024"),
        ]
    return [
        ("District / જિલ્લો", "Demo District"),
        ("Taluka / તાલુકો", "Demo Tehsil"),
        ("Village / ગામ", "Demo Village"),
        ("Survey Number / સર્વે નંબર", "145/2"),
        ("Hissa Number / હિસ્સા નંબર", "2B"),
        ("Khata Number / ખાતા નંબર", "123"),
        ("Khasra Number / ખસરા નંબર", "78"),
        ("Owner Name / માલિક", "Ramesh Kumar Patel"),
        ("Father Name / પિતાનું નામ", "Suresh Kumar Patel"),
        ("Extent / ક્ષેત્રફળ", "2.45 Hectare"),
        ("Land Class / જમીન વર્ગ", "Agricultural / ખેતી"),
        ("Mutation Number / મ્યુટેશન", "M-2024-0091"),
        ("Record Date / રેકોર્ડ તારીખ", "15-03-2024"),
    ]


CROP_TABLE = [
    ("Season", "Crop", "Area (Ha)", "Irrigation"),
    ("Kharif 2023", "Paddy", "1.20", "Canal"),
    ("Rabi 2023", "Wheat", "0.85", "Tube well"),
    ("Summer 2024", "Groundnut", "0.40", "Rain fed"),
]

STATUTORY = [
    "1. This is a SPECIMEN document generated for software testing. It is not a legal",
    "   instrument and confers no right, title or interest in any property.",
    "2. All names, identifiers and particulars appearing above are fictitious.",
    "3. Issued by a fictional authority for the purpose of OCR evaluation only.",
]


# ------------------------------------------------------------- decoration
def guilloche(img: Image.Image, seed: int) -> None:
    """Interfering security lattice — the main real-world OCR obstacle."""
    rng = random.Random(seed)
    layer = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(layer)
    for band in range(3):
        amp = 16 + band * 7
        period = 150 + band * 55
        phase = rng.uniform(0, math.tau)
        step = 20
        for y0 in range(150, H - 150, step):
            pts = []
            for x in range(60, W - 60, 8):
                y = y0 + amp * math.sin(x / period * math.tau + phase + y0 / 240)
                pts.append((x, y))
            d.line(pts, fill=SECURITY, width=1)
    layer = layer.filter(ImageFilter.GaussianBlur(0.4))
    img.paste(Image.blend(img, layer, 0.30))


def microtext(img: Image.Image, text: str) -> None:
    f = font(LATIN, 13)
    layer = Image.new("RGBA", (W * 2, H * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for y in range(0, H * 2, 46):
        d.text((0, y), (text + "  ") * 40, font=f, fill=(150, 160, 178, 92))
    layer = layer.rotate(-30, resample=Image.BICUBIC, center=(W, H))
    img.paste(layer.crop((W // 2, H // 2, W // 2 + W, H // 2 + H)),
              (0, 0), layer.crop((W // 2, H // 2, W // 2 + W, H // 2 + H)))


def arc_text(d: ImageDraw.ImageDraw, cx, cy, r, text, f, fill, start_deg, sweep_deg):
    n = max(len(text), 1)
    for i, ch in enumerate(text):
        ang = math.radians(start_deg + sweep_deg * (i + 0.5) / n)
        x = cx + r * math.cos(ang)
        y = cy + r * math.sin(ang)
        glyph = Image.new("RGBA", (46, 46), (0, 0, 0, 0))
        ImageDraw.Draw(glyph).text((23, 23), ch, font=f, fill=fill, anchor="mm")
        glyph = glyph.rotate(-(math.degrees(ang) + 90), resample=Image.BICUBIC)
        d._image.paste(glyph, (int(x) - 23, int(y) - 23), glyph)


def rubber_stamp(img: Image.Image, cx: int, cy: int) -> None:
    """Translucent circular stamp rotated over live text."""
    size = 430
    layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    c = size // 2
    ink = SEAL_INK + (205,)
    d.ellipse([8, 8, size - 8, size - 8], outline=ink, width=6)
    d.ellipse([26, 26, size - 26, size - 26], outline=ink, width=3)
    d.ellipse([96, 96, size - 96, size - 96], outline=ink, width=2)
    arc_text(d, c, c, c - 52, "DEMO STATE LAND RECORDS", font(LATIN_BOLD, 27), ink, 150, 240)
    arc_text(d, c, c, c - 52, "SPECIMEN - NOT VALID", font(LATIN_BOLD, 25), ink, 20, 110)
    d.text((c, c - 26), "VILLAGE", font=font(LATIN_BOLD, 30), fill=ink, anchor="mm")
    d.text((c, c + 6), "ACCOUNTANT", font=font(LATIN_BOLD, 26), fill=ink, anchor="mm")
    d.text((c, c + 40), "15 MAR 2024", font=font(LATIN_BOLD, 24), fill=ink, anchor="mm")
    layer = layer.rotate(-13, resample=Image.BICUBIC)
    img.paste(layer, (cx - c, cy - c), layer)


def signature(img: Image.Image, x: int, y: int, seed: int) -> None:
    rng = random.Random(seed)
    layer = Image.new("RGBA", (420, 150), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    pts, px = [], 20
    for i in range(46):
        px += rng.randint(6, 10)
        py = 78 + math.sin(i / 2.6) * 26 + rng.randint(-9, 9)
        pts.append((px, py))
    d.line(pts, fill=SIG_INK + (235,), width=3, joint="curve")
    d.line([(30, 116), (330, 108)], fill=SIG_INK + (200,), width=2)
    img.paste(layer, (x, y), layer)


def qr_block(img: Image.Image, x: int, y: int, seed: int) -> None:
    """Decorative verification block. Encodes nothing; labelled specimen."""
    rng = random.Random(seed)
    cell, n = 6, 29
    layer = Image.new("RGB", (cell * n, cell * n), "white")
    d = ImageDraw.Draw(layer)
    for r in range(n):
        for c in range(n):
            if rng.random() < 0.46:
                d.rectangle([c * cell, r * cell, (c + 1) * cell - 1, (r + 1) * cell - 1], fill=INK)
    for ox, oy in ((0, 0), (n - 7, 0), (0, n - 7)):
        d.rectangle([ox * cell, oy * cell, (ox + 7) * cell, (oy + 7) * cell], fill="white")
        d.rectangle([ox * cell, oy * cell, (ox + 7) * cell, (oy + 7) * cell], outline=INK, width=cell)
        d.rectangle([(ox + 2) * cell, (oy + 2) * cell, (ox + 5) * cell, (oy + 5) * cell], fill=INK)
    img.paste(layer, (x, y))


# ------------------------------------------------------------------ build
def _esc(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build(script: str, degraded: bool, seed: int):
    """Compose one specimen page.

    Raster layers come from Pillow; every glyph comes from MuPDF at an
    explicit rectangle, so Devanagari and Gujarati shape correctly and the
    label/value columns cannot collide.
    """
    background = Image.new("RGB", (W, H), (253, 252, 249))
    guilloche(background, seed)
    microtext(background, "SPECIMEN NOT A LEGAL DOCUMENT")
    d = ImageDraw.Draw(background)
    d.rectangle([60, 60, W - 60, H - 60], outline=RULE, width=3)
    d.rectangle([74, 74, W - 74, H - 74], outline=RULE, width=1)

    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    rubber_stamp(overlay, W - 380, H - 620)
    signature(overlay, W - 660, H - 400, seed)
    qr_block(overlay, 140, H - 470, seed)

    native = "भूमि अधिकार अभिलेख" if script == "hin" else "જમીન અધિકાર રેકોર્ડ"
    spec = "S P E C I M E N   \u2014   F O R   T E S T I N G   O N L Y"
    ref = "RTC/DEMO/2024/000145"
    fields = record_fields(script)
    lines: list[str] = []

    p = Placer(W, H, dpi=200)
    p.image(background)

    inner = W - 260
    y = 108
    p.text(130, y, inner, 60, "DEMO STATE &#8212; DEPARTMENT OF LAND RECORDS",
           size=15, bold=True, align="center")
    lines.append("DEMO STATE \u2014 DEPARTMENT OF LAND RECORDS")
    y += 52
    p.text(130, y, inner, 74, "RECORD OF RIGHTS, TENANCY AND CROPS",
           size=23, bold=True, align="center")
    lines.append("RECORD OF RIGHTS, TENANCY AND CROPS")
    y += 74
    p.text(130, y, inner, 60, _esc(native), size=17, align="center")
    lines.append(native)
    y += 58
    p.text(130, y, inner, 44, f"( {_esc(spec)} )", size=10, align="center", color="#8c2828")
    lines.append(f"( {spec} )")
    y += 44
    d.line([(150, y), (W - 150, y)], fill=RULE, width=2)

    y += 26
    p.text(130, y, 900, 44, f"Reference No.: {ref}", size=12)
    p.text(W - 500, y, 370, 44, "Page 1 of 1", size=12, align="right")
    lines.append(f"Reference No.: {ref}")
    y += 58

    # ---- label : value rows, each cell in its own rectangle ----
    LABEL_X, LABEL_W = 132, 660
    VALUE_X, VALUE_W = 850, 660
    ROW_H = 62
    for label, value in fields:
        p.text(LABEL_X, y, LABEL_W, ROW_H, _esc(label), size=12.5)
        p.text(VALUE_X - 26, y, 20, ROW_H, ":", size=12.5)
        p.text(VALUE_X, y, VALUE_W, ROW_H, _esc(value), size=12.5, bold=True)
        d.line([(LABEL_X, y + ROW_H - 12), (W - 132, y + ROW_H - 12)],
               fill=(212, 216, 224), width=1)
        lines.append(f"{label}: {value}")
        y += ROW_H

    # ---- cultivation table ----
    y += 24
    p.text(LABEL_X, y, 900, 50, "CULTIVATION PARTICULARS", size=14, bold=True)
    lines.append("CULTIVATION PARTICULARS")
    y += 54
    cols = [(132, 400), (540, 320), (880, 260), (1160, 360)]
    header, *body = CROP_TABLE
    for i, cell in enumerate(header):
        p.text(cols[i][0], y, cols[i][1], 48, _esc(cell), size=12, bold=True)
    d.line([(132, y + 44), (W - 132, y + 44)], fill=RULE, width=2)
    lines.append("  ".join(header))
    y += 56
    for row in body:
        for i, cell in enumerate(row):
            p.text(cols[i][0], y, cols[i][1], 48, _esc(cell), size=12)
        d.line([(132, y + 44), (W - 132, y + 44)], fill=(216, 220, 228), width=1)
        lines.append("  ".join(row))
        y += 56

    # ---- statutory notes ----
    y += 26
    for text in STATUTORY:
        p.text(132, y, 1100, 40, _esc(text.strip()), size=9.5, color="#464c5a")
        lines.append(text.strip())
        y += 34

    p.text(140, H - 300, 500, 40, "Verification block &#8212; specimen",
           size=9.5, color="#6e7482")
    lines.append("Verification block \u2014 specimen")
    p.text(W - 760, H - 250, 620, 44, "Signature of Village Accountant", size=11.5)
    lines.append("Signature of Village Accountant")

    p.image(overlay, overlay=True)
    pdf_bytes, image = p.finish()

    if degraded:
        image = degrade(image, seed)
        pdf_bytes = None
    return pdf_bytes, image, lines


DOCS = [
    ("doc08_rtc_hindi", "hin", False, 401),
    ("doc09_rtc_gujarati", "guj", False, 402),
    ("doc10_rtc_hindi_scan", "hin", True, 403),
    ("doc11_rtc_gujarati_scan", "guj", True, 404),
]


def main() -> int:
    RAW.mkdir(parents=True, exist_ok=True)
    GT.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.is_file() else {
        "version": "dataset_v1", "documents": []}
    existing = {doc["id"] for doc in manifest.get("documents", [])}

    for doc_id, script, degraded, seed in DOCS:
        pdf_bytes, image, lines = build(script, degraded, seed)
        image.save(RAW / f"{doc_id}.png", "PNG")
        if pdf_bytes:
            (RAW / f"{doc_id}.pdf").write_bytes(pdf_bytes)
        else:
            image.convert("RGB").save(RAW / f"{doc_id}.pdf", "PDF", resolution=200.0)

        lang = "hin+eng" if script == "hin" else "guj+eng"
        (GT / f"{doc_id}.json").write_text(json.dumps({
            "id": doc_id,
            "language": lang,
            "lines": lines,
            "text": "\n".join(lines),
            "source": "synthetic-specimen",
            "degraded": degraded,
            "shaping": "mupdf-harfbuzz",
            "note": ("SPECIMEN. Fictitious authority, names and identifiers. Ground truth is "
                     "exact by construction and the page is rendered with correct Indic text "
                     "shaping. Reproduces OCR-relevant difficulty (security lattice, microtext, "
                     "stamp occlusion, skew, noise) but is NOT a copy of any government "
                     "instrument."),
        }, ensure_ascii=False, indent=2), encoding="utf-8")

        if doc_id not in existing:
            manifest["documents"].append({
                "id": doc_id,
                "file": f"raw_documents/{doc_id}.pdf",
                "ground_truth": f"ground_truth/{doc_id}.json",
                "difficulty": "HARD" if degraded else "MEDIUM",
                "language": lang,
                "attributes": ["printed", "security-background", "stamp-overlay", "bilingual"]
                + (["skewed", "noisy", "low-contrast"] if degraded else []),
                "purpose": "development-fixture",
            })
        print(f"  {doc_id:26s} {lang:8s} {'degraded' if degraded else 'clean   '} "
              f"{len(lines):3d} lines  -> {doc_id}.pdf + .png")

    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\nWrote PDFs + PNGs + ground truth. Every page is marked SPECIMEN.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
