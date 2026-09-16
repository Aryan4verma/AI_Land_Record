"""Build the Demo Mode fixture from the canonical demonstration PDF.

DEVELOPMENT-TIME ONLY. This is the one place where the demo document is put
through the real OCR engine and the real AI provider. Demo Mode at runtime
reads the JSON this produces and never contacts an external service.

Run it once (or after deliberately changing the canonical document):

    backend\\.venv\\Scripts\\python scripts\\build_demo_fixture.py

It writes demo/fixtures/<fixture_id>/{document.pdf, ocr_result.json,
extraction_result.json, README.md} and refreshes demo/fixtures/manifest.json.

Passing --ocr-only skips the AI provider entirely and reuses any existing
extraction_result.json, so the OCR half can be rebuilt at zero cost.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

SOURCE = ROOT / "dataset" / "raw_documents" / "doc10_rtc_hindi_scan.pdf"
FIXTURE_ID = "doc10_rtc_hindi_scan"
DEMO_DIR = ROOT / "demo" / "fixtures"
FIXTURE_DIR = DEMO_DIR / FIXTURE_ID

MANIFEST_VERSION = "1"
FIXTURE_SCHEMA_VERSION = "1"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ocr-only", action="store_true",
                        help="rebuild OCR only; reuse existing extraction (no AI call)")
    args = parser.parse_args()

    if not SOURCE.is_file():
        print(f"STOP: canonical demo PDF missing at {SOURCE}", file=sys.stderr)
        return 2

    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    raw = SOURCE.read_bytes()
    digest = sha256(raw)

    # The fixture owns its own copy so the demo never depends on dataset/.
    target_pdf = FIXTURE_DIR / "document.pdf"
    shutil.copyfile(SOURCE, target_pdf)

    # ---- OCR: local engine, no external service -------------------------
    from ai.ocr.pdf_render import load_pages_from_bytes
    from ai.ocr.tesseract_adapter import TesseractOcrEngine, engine_version

    images = load_pages_from_bytes(raw, ".pdf", dpi=300)
    engine = TesseractOcrEngine(language=None)
    pages, meta = [], {}
    started = time.perf_counter()
    for number, image in enumerate(images, start=1):
        page, _elapsed = engine.read_image(image, page_number=number)
        meta = engine.last_meta
        pages.append({
            "page_number": page.page_number,
            "text": page.text,
            "confidence": page.confidence,
            "width": page.width,
            "height": page.height,
            "lines": [{"text": ln.text, "confidence": ln.confidence, "box": list(ln.box)}
                      for ln in page.lines],
        })
    ocr_seconds = round(time.perf_counter() - started, 3)

    ocr_payload = {
        "fixture_id": FIXTURE_ID,
        "schema_version": FIXTURE_SCHEMA_VERSION,
        "engine": "tesseract",
        "engine_version": engine_version(),
        "language": meta.get("language"),
        "detection": meta.get("detection"),
        "preprocess_steps": meta.get("preprocess_steps"),
        "seconds": ocr_seconds,
        "pages": pages,
    }
    (FIXTURE_DIR / "ocr_result.json").write_text(
        json.dumps(ocr_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  OCR      : {len(pages)} page(s), lang={meta.get('language')}, "
          f"{sum(len(p['lines']) for p in pages)} lines, {ocr_seconds}s  (local, no API)")

    # ---- Extraction: the ONE external AI call, development-time only ----
    extraction_path = FIXTURE_DIR / "extraction_result.json"
    if args.ocr_only and extraction_path.is_file():
        print("  Extract  : reused existing extraction_result.json (no AI call)")
        extraction = json.loads(extraction_path.read_text(encoding="utf-8"))
    else:
        from app.ai.service import get_ai_service
        from app.ai.types import ExtractionInput

        ocr_text = "\n".join(p["text"] for p in pages)
        service = get_ai_service()
        result = service.extract_land_record(ExtractionInput(
            ocr_text=ocr_text, document_type=None, language=meta.get("language"),
            document_checksum=digest))
        extraction = {
            "fixture_id": FIXTURE_ID,
            "schema_version": FIXTURE_SCHEMA_VERSION,
            "provider": result.provider,
            "model": result.model,
            "prompt_version": result.prompt_version,
            "schema_version_provider": result.schema_version,
            "elapsed_seconds": result.elapsed_seconds,
            "attempted_routes": result.attempted_routes,
            "fields": {
                name: {
                    "value": fr.value,
                    "confidence": fr.confidence,
                    "source_text": fr.source_text,
                    "extraction_status": fr.extraction_status,
                }
                for name, fr in result.fields.items()
            },
        }
        extraction_path.write_text(
            json.dumps(extraction, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  Extract  : provider={result.provider} model={result.model} "
              f"({len(result.fields)} fields)  <- ONE development-time AI call")

    # ---- Manifest -------------------------------------------------------
    manifest = {
        "manifest_version": MANIFEST_VERSION,
        "note": ("Demo Mode fixtures. A document is recognised by SHA-256 of its bytes, "
                 "never by filename, so a renamed copy still matches and an unrelated "
                 "file never does."),
        "fixtures": [{
            "fixture_id": FIXTURE_ID,
            "sha256": digest,
            "original_filename": SOURCE.name,
            "byte_size": len(raw),
            "page_count": len(pages),
            "fixture_version": FIXTURE_SCHEMA_VERSION,
            "schema_version": FIXTURE_SCHEMA_VERSION,
            "document": f"{FIXTURE_ID}/document.pdf",
            "ocr_result": f"{FIXTURE_ID}/ocr_result.json",
            "extraction_result": f"{FIXTURE_ID}/extraction_result.json",
            "description": ("SPECIMEN Record of Rights (Hindi/English), rendered as a worn "
                            "scan. Fictitious authority, names and identifiers."),
        }],
    }
    (DEMO_DIR / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    (FIXTURE_DIR / "README.md").write_text(
        f"# Demo fixture: {FIXTURE_ID}\n\n"
        f"Canonical demonstration document for Demo Mode.\n\n"
        f"- SHA-256: `{digest}`\n"
        f"- Size: {len(raw)} bytes\n"
        f"- Pages: {len(pages)}\n"
        f"- OCR language resolved: `{meta.get('language')}`\n"
        f"- Extraction provider (development-time): "
        f"`{extraction.get('provider')}` / `{extraction.get('model')}`\n\n"
        "## What this is\n\n"
        "A SPECIMEN land record. The issuing authority, names and identifiers are\n"
        "fictitious; the page is marked SPECIMEN. It is not a copy of any government\n"
        "instrument.\n\n"
        "## How it is used\n\n"
        "At runtime Demo Mode reads `ocr_result.json` and `extraction_result.json` and\n"
        "feeds them into the ordinary pipeline. Validation, confidence, persistence,\n"
        "review, approval and audit all run exactly as in Live Mode. **No external AI\n"
        "or OCR service is contacted.**\n\n"
        "## Rebuilding\n\n"
        "```\nbackend\\.venv\\Scripts\\python scripts\\build_demo_fixture.py\n```\n\n"
        "That is the only step that calls an external provider, and only once.\n"
        "`--ocr-only` rebuilds the OCR half at zero cost.\n",
        encoding="utf-8")

    print(f"  Manifest : {DEMO_DIR / 'manifest.json'}")
    print(f"  SHA-256  : {digest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
