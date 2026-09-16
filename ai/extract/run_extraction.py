"""OCR output -> extract_land_record() -> structured model outputs.

Flow: dataset/ocr_outputs/<id>.json -> OCR text/context -> LLM ->
dataset/model_outputs/<id>.json with provider/model/prompt/schema versions
and source metadata preserved. Provider failures are recorded per document
(failed=true + classified error code) — the batch never crashes on one bad
document, and malformed AI responses surface as PROVIDER_BAD_RESPONSE, not
as invented fields. No validation rules here (later step).

Usage (from repo root; backend venv supplies httpx/pydantic):
    .\\backend\\.venv\\Scripts\\python ai\\extract\\run_extraction.py
"""
import json
import sys
import time
from pathlib import Path


def _ensure_paths() -> Path:
    root = Path(__file__).resolve().parents[2]
    backend = root / "backend"
    for entry in (str(root), str(backend)):
        if entry not in sys.path:
            sys.path.insert(0, entry)
    return root


ROOT = _ensure_paths()

from app.ai.errors import ProviderError  # noqa: E402
from app.ai.service import extract_land_record  # noqa: E402
from app.ai.types import ExtractionInput  # noqa: E402


def build_input(ocr_payload: dict, document_type: str | None = None, language: str = "en") -> ExtractionInput:
    """Join OCR page texts in order; keep document context alongside."""
    pages = ocr_payload.get("pages", [])
    text = "\n".join(page.get("text", "") for page in pages)
    return ExtractionInput(ocr_text=text, document_type=document_type, language=language)


def extract_document(doc_id: str, ocr_payload: dict) -> dict:
    """Run one document through the provider layer. Never raises."""
    started = time.perf_counter()
    record: dict = {
        "id": doc_id,
        "source_ocr_file": ocr_payload.get("source_file", ""),
        "ocr_engine": ocr_payload.get("engine", ""),
        "ocr_engine_version": ocr_payload.get("engine_version", ""),
        "ocr_pages": len(ocr_payload.get("pages", [])),
        "failed": False,
        "error_code": None,
        "error_message": None,
    }
    try:
        result = extract_land_record(build_input(ocr_payload))
    except ProviderError as exc:
        record.update(
            {
                "failed": True,
                "error_code": exc.code,
                "error_message": exc.message,
                "elapsed_seconds": round(time.perf_counter() - started, 2),
            }
        )
        return record
    record.update(
        {
            "provider": result.provider,
            "model": result.model,
            "prompt_version": result.prompt_version,
            "schema_version": result.schema_version,
            "elapsed_seconds": round(result.elapsed_seconds, 2),
            "fields": {
                name: {
                    "value": item.value,
                    "confidence": item.confidence,
                    "status": item.extraction_status,
                }
                for name, item in result.fields.items()
            },
            "values": result.values(),
        }
    )
    return record


def main() -> int:
    manifest = json.loads((ROOT / "dataset" / "manifest.json").read_text(encoding="utf-8"))
    out_dir = ROOT / "dataset" / "model_outputs"
    out_dir.mkdir(parents=True, exist_ok=True)
    failures = 0
    for entry in manifest["documents"]:
        doc_id = entry["id"]
        ocr_path = ROOT / "dataset" / "ocr_outputs" / f"{doc_id}.json"
        ocr_payload = json.loads(ocr_path.read_text(encoding="utf-8"))
        record = extract_document(doc_id, ocr_payload)
        (out_dir / f"{doc_id}.json").write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        failures += record["failed"]
        if record["failed"]:
            print(f"{doc_id}: FAILED {record['error_code']}: {record['error_message']}")
        else:
            filled = sum(1 for v in record["values"].values() if v is not None)
            print(
                f"{doc_id}: ok, {filled}/14 fields filled, "
                f"{record['provider']}/{record['model']} in {record['elapsed_seconds']}s"
            )
    print(f"wrote {out_dir} ({failures} failures)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
