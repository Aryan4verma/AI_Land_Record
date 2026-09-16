"""Generate synthetic Hindi / Gujarati / mixed-script land-record fixtures.

DEVELOPMENT FIXTURES — NOT AN EVALUATION SET.

All content is fictitious and labelled FOR TESTING ONLY (05 section 11:
prefer synthetic examples). Ground truth is exact *by construction*: the same
strings that are rendered are written to the ground-truth file, so these
fixtures measure whether the OCR configuration can read a clean rendering of
each script. They do NOT measure real-world accuracy on scanned or
photographed land records, and must not be used to claim it — see
dataset/ground_truth/MULTILINGUAL_NOTE.txt.

Variants:
  doc04_hindi.png       Devanagari land record, clean print
  doc05_gujarati.png    Gujarati land record, clean print
  doc06_mixed_en_hi.png English labels + Hindi values
  doc07_mixed_en_gu.png English labels + Gujarati values

Usage (from repo root):
    backend\\.venv\\Scripts\\python scripts\\make_multilingual_docs.py

Deterministic. Writes dataset/raw_documents/*, dataset/ground_truth/*.json
and merges entries into dataset/manifest.json.
"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "dataset" / "raw_documents"
GT = ROOT / "dataset" / "ground_truth"
MANIFEST = ROOT / "dataset" / "manifest.json"

# Nirmala UI ships with Windows and covers Devanagari AND Gujarati.
FONT_CANDIDATES = [
    r"C:\Windows\Fonts\Nirmala.ttc",
    r"C:\Windows\Fonts\NirmalaS.ttc",
]

# --- Hindi / Devanagari -------------------------------------------------
HINDI_LINES = [
    "नमूना भूमि अभिलेख - केवल परीक्षण हेतु",
    "खाता संख्या: 123",
    "खसरा संख्या: 78",
    "सर्वेक्षण संख्या: 145/2",
    "स्वामी का नाम: रमेश कुमार",
    "पिता का नाम: सुरेश कुमार",
    "क्षेत्रफल: 2.45 हेक्टेयर",
    "गाँव: डेमो गाँव",
    "तहसील: डेमो तहसील",
    "जिला: डेमो जिला",
    "भूमि वर्ग: कृषि",
    "उत्परिवर्तन संख्या: M-2024-0091",
    "अभिलेख दिनांक: 15-03-2024",
]

# --- Gujarati -----------------------------------------------------------
GUJARATI_LINES = [
    "નમૂનો જમીન રેકોર્ડ - ફક્ત પરીક્ષણ માટે",
    "ખાતા નંબર: 123",
    "ખસરા નંબર: 78",
    "સર્વે નંબર: 145/2",
    "માલિકનું નામ: રમેશ કુમાર",
    "પિતાનું નામ: સુરેશ કુમાર",
    "ક્ષેત્રફળ: 2.45 હેક્ટર",
    "ગામ: ડેમો ગામ",
    "તાલુકો: ડેમો તાલુકો",
    "જિલ્લો: ડેમો જિલ્લો",
    "જમીન વર્ગ: ખેતી",
    "મ્યુટેશન નંબર: M-2024-0091",
    "રેકોર્ડ તારીખ: 15-03-2024",
]

# --- Mixed: English labels, local-script values -------------------------
MIXED_EN_HI_LINES = [
    "SAMPLE LAND RECORD - FOR TESTING ONLY",
    "Khata Number: 123",
    "Khasra Number: 78",
    "Survey Number: 145/2",
    "Owner Name: रमेश कुमार",
    "Father Name: सुरेश कुमार",
    "Area: 2.45 हेक्टेयर",
    "Village: डेमो गाँव",
    "Tehsil: डेमो तहसील",
    "District: डेमो जिला",
    "Land Classification: कृषि",
    "Mutation Number: M-2024-0091",
    "Record Date: 15-03-2024",
]

MIXED_EN_GU_LINES = [
    "SAMPLE LAND RECORD - FOR TESTING ONLY",
    "Khata Number: 123",
    "Khasra Number: 78",
    "Survey Number: 145/2",
    "Owner Name: રમેશ કુમાર",
    "Father Name: સુરેશ કુમાર",
    "Area: 2.45 હેક્ટર",
    "Village: ડેમો ગામ",
    "Tehsil: ડેમો તાલુકો",
    "District: ડેમો જિલ્લો",
    "Land Classification: ખેતી",
    "Mutation Number: M-2024-0091",
    "Record Date: 15-03-2024",
]

DOCS = [
    ("doc04_hindi", HINDI_LINES, "hin", ["printed", "devanagari"]),
    ("doc05_gujarati", GUJARATI_LINES, "guj", ["printed", "gujarati"]),
    ("doc06_mixed_en_hi", MIXED_EN_HI_LINES, "eng+hin", ["printed", "mixed-script"]),
    ("doc07_mixed_en_gu", MIXED_EN_GU_LINES, "eng+guj", ["printed", "mixed-script"]),
]

WIDTH, MARGIN, LINE_H, FONT_SIZE = 1240, 70, 58, 30


def _font(size: int) -> ImageFont.FreeTypeFont:
    for path in FONT_CANDIDATES:
        if Path(path).is_file():
            # index 0 of Nirmala.ttc is the regular face.
            return ImageFont.truetype(path, size, index=0)
    raise SystemExit(
        "No Indic-capable font found. Install Nirmala UI (ships with Windows) "
        "or point FONT_CANDIDATES at a font covering Devanagari + Gujarati."
    )


def render(lines: list[str], font=None) -> Image.Image:
    """Render via MuPDF so Devanagari/Gujarati are SHAPED correctly.

    Pillow has no complex-text-shaping engine here (features.check("raqm")
    is False), so it placed pre-base matras after their consonant and broke
    conjuncts. The ground truth would then disagree with the rendered page and
    the benchmark would measure the renderer, not the OCR engine.
    """
    import sys as _sys
    _sys.path.insert(0, str(Path(__file__).resolve().parent))
    from render_indic import Placer

    height = MARGIN * 2 + LINE_H * len(lines)
    p = Placer(WIDTH, height, dpi=200)
    from PIL import Image as _I
    p.image(_I.new("RGB", (WIDTH, height), "white"))
    y = MARGIN
    for line in lines:
        esc = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        p.text(MARGIN, y, WIDTH - 2 * MARGIN, LINE_H, esc, size=15)
        y += LINE_H
    _pdf, img = p.finish()
    return img


def main() -> int:
    RAW.mkdir(parents=True, exist_ok=True)
    GT.mkdir(parents=True, exist_ok=True)
    font = _font(FONT_SIZE)

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.is_file() else {
        "version": "dataset_v1", "documents": []
    }
    existing = {d["id"] for d in manifest.get("documents", [])}

    for doc_id, lines, lang, attrs in DOCS:
        img = render(lines, font)
        png = RAW / f"{doc_id}.png"
        img.save(png, "PNG")

        (GT / f"{doc_id}.json").write_text(
            json.dumps(
                {
                    "id": doc_id,
                    "language": lang,
                    "lines": lines,
                    "text": "\n".join(lines),
                    "source": "synthetic-render",
                    "note": (
                        "Ground truth is exact by construction (rendered from these "
                        "exact strings). Development fixture only — does NOT measure "
                        "real-world scanned-document accuracy."
                    ),
                },
                ensure_ascii=False, indent=2,
            ),
            encoding="utf-8",
        )

        if doc_id not in existing:
            manifest["documents"].append({
                "id": doc_id,
                "file": f"raw_documents/{doc_id}.png",
                "ground_truth": f"ground_truth/{doc_id}.json",
                "difficulty": "EASY",
                "language": lang,
                "attributes": attrs,
                "purpose": "development-fixture",
            })
        print(f"  {doc_id:20s} {lang:8s} {len(lines)} lines  {png.name}")

    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    (GT / "MULTILINGUAL_NOTE.txt").write_text(
        "MULTILINGUAL FIXTURES — SCOPE AND LIMITATIONS\n"
        "=============================================\n\n"
        "doc04_hindi, doc05_gujarati, doc06_mixed_en_hi and doc07_mixed_en_gu are\n"
        "SYNTHETIC DEVELOPMENT FIXTURES generated by scripts/make_multilingual_docs.py.\n"
        "Ground truth is exact by construction: the generator writes the same strings\n"
        "it renders.\n\n"
        "WHAT THEY MEASURE\n"
        "  Whether the OCR engine + language configuration can read a CLEAN, digitally\n"
        "  rendered page in each script, and whether script detection routes it to the\n"
        "  right language pack.\n\n"
        "WHAT THEY DO NOT MEASURE\n"
        "  Real-world accuracy. They contain no scanning noise, no skew from a real\n"
        "  scanner bed, no paper texture, no ink bleed, no faded stamps, no handwriting,\n"
        "  and no regional typography variation. A near-zero CER on these fixtures is\n"
        "  therefore NOT evidence of production readiness for Hindi or Gujarati.\n\n"
        "REQUIRED BEFORE ANY ACCURACY CLAIM\n"
        "  A held-out evaluation set of real (or realistically degraded) Hindi and\n"
        "  Gujarati land records with human-verified ground truth, kept separate from\n"
        "  these tuning fixtures. Target 30-50 documents per script per\n"
        "  05_DATASET_AND_ANNOTATION.\n",
        encoding="utf-8",
    )
    print("\nwrote dataset/ground_truth/MULTILINGUAL_NOTE.txt (scope + limitations)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
