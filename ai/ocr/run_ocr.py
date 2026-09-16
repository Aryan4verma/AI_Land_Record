"""CLI: run the POC OCR engine over one PDF/image file.

Usage (from repo root):
    .\\ai\\.venv\\Scripts\\python -m ai.ocr.run_ocr dataset/raw_documents/doc01_clean.pdf
    .\\ai\\.venv\\Scripts\\python -m ai.ocr.run_ocr <file> --out dataset/ocr_outputs/<name>.json

Output JSON: {engine, engine_version, source_file, elapsed_seconds, pages[]}
with text + confidence + boxes + page info per page. No LLM, no validation.
"""
import argparse
import json
import sys
import time
from pathlib import Path


def _ensure_root() -> None:
    root = Path(__file__).resolve().parents[2]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))


_ensure_root()

from ai.ocr.base import OcrResult  # noqa: E402
from ai.ocr.pdf_render import load_pages  # noqa: E402
from ai.ocr.tesseract_adapter import ENGINE_NAME, TesseractOcrEngine, engine_version  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="OCR POC runner")
    parser.add_argument("input", help="PDF or image file to read")
    parser.add_argument("--dpi", type=int, default=300, help="PDF render resolution")
    parser.add_argument("--out", default=None, help="Where to write the result JSON")
    args = parser.parse_args()

    # language=None -> per-page script detection, matching the pipeline.
    engine = TesseractOcrEngine(language=None)
    started = time.perf_counter()
    try:
        images = load_pages(args.input, dpi=args.dpi)
    except Exception as exc:
        print(f"FAILED to load {args.input}: {exc}")
        return 2

    pages = []
    for number, image in enumerate(images, start=1):
        try:
            page, elapsed = engine.read_image(image, page_number=number)
        except Exception as exc:
            print(f"page {number}: OCR FAILED ({exc})")
            return 3
        conf = f"{page.confidence:.3f}" if page.confidence is not None else "n/a"
        print(f"page {number}: {len(page.lines)} lines, {len(page.text)} chars, conf={conf}, {elapsed:.2f}s")
        pages.append(page)

    result = OcrResult(
        engine=ENGINE_NAME,
        engine_version=engine_version(),
        source_file=str(args.input),
        pages=pages,
        elapsed_seconds=time.perf_counter() - started,
    )
    payload = json.dumps(result.to_dict(), ensure_ascii=False, indent=2)
    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(payload, encoding="utf-8")
        print(f"wrote {out_path}")
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
