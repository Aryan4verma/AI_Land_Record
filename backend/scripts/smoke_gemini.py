"""One controlled live request to the configured AI provider (STEP 06 check).

Reads credentials from backend `.env` / environment only. Prints extracted
field values + confidences and provider metadata. NEVER prints any key.

Usage (from backend/):
    .\\.venv\\Scripts\\python scripts\\smoke_gemini.py

Exit 2 when no provider key is configured (nothing to test against).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.ai.errors import ProviderError  # noqa: E402
from app.ai.service import get_ai_service  # noqa: E402
from app.ai.types import KNOWN_FIELDS, ExtractionInput  # noqa: E402
from app.config import get_settings  # noqa: E402

CONTROLLED_OCR = (
    "SAMPLE LAND RECORD - FOR TESTING ONLY\n"
    "District: Demo District\n"
    "Tehsil: Demo Tehsil\n"
    "Village: Demo Village\n"
    "Khata Number: 123\n"
    "Khasra Number: 78\n"
    "Survey Number: 145/2\n"
    "Owner Name: Ramesh Kumar\n"
    "Father Name: Suresh Kumar\n"
    "Area: 2.45 Hectare\n"
    "Land Classification: Agricultural\n"
    "Mutation Number: M-2024-0091\n"
    "Record Date: 2024-03-15"
)


def main() -> int:
    settings = get_settings()
    provider = (settings.ai_provider or "").strip().lower()
    key_attr = {"gemini": "gemini_api_key"}.get(provider, "")
    if not key_attr or not getattr(settings, key_attr, ""):
        print(f"no API key configured for provider '{provider or '(unset)'}'; skipping live check")
        return 2
    try:
        result = get_ai_service(settings).extract_land_record(
            ExtractionInput(ocr_text=CONTROLLED_OCR, document_type="khata", language="en")
        )
    except ProviderError as exc:
        print(f"provider error: {exc.code}: {exc.message}")
        for key in ("http_status", "endpoint", "model", "key_configured", "body", "exception", "code_path"):
            print(f"  {key}={exc.details.get(key)}")
        return 1
    for name in KNOWN_FIELDS:
        item = result.fields[name]
        print(f"{name:<22} value={item.value!r} conf={item.confidence} status={item.extraction_status}")
    print(
        f"provider={result.provider} model={result.model} "
        f"prompt={result.prompt_version} schema={result.schema_version} "
        f"elapsed={result.elapsed_seconds:.1f}s"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
