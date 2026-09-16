"""Before/after OCR benchmark across English, Hindi, Gujarati and mixed script.

BEFORE = the configuration this project shipped: `eng` only, no preprocessing,
         no script detection (the pipeline constructed TesseractOcrEngine()
         with no language at all).
AFTER  = detected language configuration + conservative preprocessing.

Both configurations read the same fixtures with the same engine, so the
difference is attributable to the configuration change alone.

Usage (from repo root):
    backend\\.venv\\Scripts\\python -m ai.ocr.benchmark_multilingual
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ai.ocr.benchmark import error_rate  # noqa: E402
from ai.ocr.script_detect import detect_script  # noqa: E402
from ai.ocr.tesseract_adapter import TesseractOcrEngine  # noqa: E402

RAW = ROOT / "dataset" / "raw_documents"
GT = ROOT / "dataset" / "ground_truth"
OUT = ROOT / "dataset" / "evaluation" / "ocr_multilingual.json"

# (id, expected script family) — the family is what detection SHOULD choose.
DOCS = [
    ("doc01_clean", "english"),
    ("doc02_noisy", "english"),
    ("doc03_faded", "english"),
    ("doc04_hindi", "hindi"),
    ("doc05_gujarati", "gujarati"),
    ("doc06_mixed_en_hi", "mixed-hi"),
    ("doc07_mixed_en_gu", "mixed-gu"),
    ("doc08_rtc_hindi", "rtc-hi"),
    ("doc09_rtc_gujarati", "rtc-gu"),
    ("doc10_rtc_hindi_scan", "rtc-hi-scan"),
    ("doc11_rtc_gujarati_scan", "rtc-gu-scan"),
]


def _truth(doc_id: str) -> str:
    data = json.loads((GT / f"{doc_id}.json").read_text(encoding="utf-8"))
    if isinstance(data.get("text"), str):
        return data["text"]
    return "\n".join(data.get("lines", []))


def _image(doc_id: str):
    from PIL import Image

    png = RAW / f"{doc_id}.png"
    if png.is_file():
        return Image.open(png)
    from ai.ocr.pdf_render import load_pages_from_bytes

    pdf = RAW / f"{doc_id}.pdf"
    return load_pages_from_bytes(pdf.read_bytes(), ".pdf", dpi=300)[0]


def _run(doc_id: str, *, language, preprocess: bool):
    image = _image(doc_id)
    engine = TesseractOcrEngine(language=language, preprocess=preprocess)
    started = time.perf_counter()
    page, _ = engine.read_image(image, page_number=1)
    elapsed = time.perf_counter() - started
    return page, elapsed, engine.last_meta


def main() -> int:
    rows = []
    print(f"{'doc':20s} {'script':10s} {'BEFORE cer':>11s} {'AFTER cer':>10s} "
          f"{'BEFORE wer':>11s} {'AFTER wer':>10s} {'lang':9s} {'secs':>6s}")
    print("-" * 96)

    for doc_id, family in DOCS:
        truth = _truth(doc_id)

        before_page, before_s, _ = _run(doc_id, language="eng", preprocess=False)
        before_cer = error_rate(truth, before_page.text, unit="char")
        before_wer = error_rate(truth, before_page.text, unit="word")

        after_page, after_s, meta = _run(doc_id, language=None, preprocess=True)
        after_cer = error_rate(truth, after_page.text, unit="char")
        after_wer = error_rate(truth, after_page.text, unit="word")

        rows.append({
            "id": doc_id, "script": family,
            "before": {"cer": round(before_cer, 4), "wer": round(before_wer, 4),
                       "lang": "eng", "seconds": round(before_s, 2),
                       "chars": len(before_page.text)},
            "after": {"cer": round(after_cer, 4), "wer": round(after_wer, 4),
                      "lang": meta.get("language"), "seconds": round(after_s, 2),
                      "chars": len(after_page.text),
                      "detection": meta.get("detection", {}).get("source"),
                      "preprocess": meta.get("preprocess_steps")},
            "truth_chars": len(truth),
        })
        print(f"{doc_id:20s} {family:10s} {before_cer:11.4f} {after_cer:10.4f} "
              f"{before_wer:11.4f} {after_wer:10.4f} {str(meta.get('language')):9s} {after_s:6.2f}")

    def mean(key, phase):
        vals = [r[phase][key] for r in rows]
        return sum(vals) / len(vals)

    print("-" * 96)
    print(f"{'MEAN (all)':31s} {mean('cer','before'):11.4f} {mean('cer','after'):10.4f} "
          f"{mean('wer','before'):11.4f} {mean('wer','after'):10.4f}")

    eng = [r for r in rows if r["script"] == "english"]
    non = [r for r in rows if r["script"] != "english"]
    if eng:
        print(f"{'  english only':31s} "
              f"{sum(r['before']['cer'] for r in eng)/len(eng):11.4f} "
              f"{sum(r['after']['cer'] for r in eng)/len(eng):10.4f}")
    if non:
        print(f"{'  hindi/gujarati/mixed':31s} "
              f"{sum(r['before']['cer'] for r in non)/len(non):11.4f} "
              f"{sum(r['after']['cer'] for r in non)/len(non):10.4f}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "note": ("Synthetic development fixtures. See "
                 "dataset/ground_truth/MULTILINGUAL_NOTE.txt — these results do NOT "
                 "measure real scanned-document accuracy."),
        "documents": rows,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
