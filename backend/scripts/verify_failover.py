"""Live failover proof (STEP 13 verification, minimal quota).

Proves: gemini lane fails transiently (MOCKED transport: 2x HTTP 500, zero
Gemini network) -> one retry -> OpenRouter lane serves ONE live request ->
second identical call served from cache with zero provider calls.

Reads OPENROUTER_API_KEY from backend .env only. Prints metadata and
redacted attempted_routes. NEVER prints keys.

Usage (from backend/):
    .\\.venv\\Scripts\\python scripts\\verify_failover.py
Exit codes: 0 proved, 1 failover did not succeed, 2 no OpenRouter key.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx  # noqa: E402

from app.ai.cache import ExtractionCache  # noqa: E402
from app.ai.gemini import GeminiAdapter  # noqa: E402
from app.ai.openrouter import OpenRouterAdapter  # noqa: E402
from app.ai.service import AIService  # noqa: E402
from app.ai.types import ExtractionInput  # noqa: E402
from app.config import get_settings  # noqa: E402

OCR_TEXT = (
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

GEMINI_NETWORK_CALLS = []


def _mock_gemini_500(request: httpx.Request) -> httpx.Response:
    GEMINI_NETWORK_CALLS.append(1)  # counts mock invocations, not network
    return httpx.Response(500, json={"error": {"message": "simulated transient failure"}})


def main() -> int:
    settings = get_settings()
    if not (settings.openrouter_api_key or "").strip():
        print("no OPENROUTER_API_KEY configured; cannot prove the live lane")
        return 2

    mock_gemini = GeminiAdapter(
        api_key="mock-not-a-key",
        model="gemini-3.6-flash",
        client=httpx.Client(transport=httpx.MockTransport(_mock_gemini_500)),
    )
    live_openrouter = OpenRouterAdapter(
        api_key=settings.openrouter_api_key,
        model="meta-llama/llama-3.3-70b-instruct",
    )
    cache = ExtractionCache(max_entries=16, ttl_seconds=600)
    service = AIService(
        provider="gemini", model="gemini-3.6-flash", api_key="mock-not-a-key",
        timeout_seconds=settings.ai_timeout_seconds,
        fallbacks=[("openrouter", "meta-llama/llama-3.3-70b-instruct", "real-key-via-adapter")],
        cache=cache,
    )
    # Swap in the two lanes: mocked failing Gemini, live OpenRouter.
    # (Dummy keys above are never used; adapters are replaced wholesale.)
    service._routes[0].adapter = mock_gemini
    service._routes[1].adapter = live_openrouter
    assert service.route_chain == (
        "gemini:gemini-3.6-flash>openrouter:meta-llama/llama-3.3-70b-instruct"
    ), service.route_chain
    print("chain:", service.route_chain)

    payload = ExtractionInput(ocr_text=OCR_TEXT, document_type="khata", language="en",
                              document_checksum="verify-failover-doc01")
    try:
        first = service.extract_land_record(payload)
    except Exception as exc:
        print("FAILOVER FAILED:", type(exc).__name__ + ":", getattr(exc, "code", "?"))
        return 1
    print("gemini mock invocations (no network):", len(GEMINI_NETWORK_CALLS))
    print("attempted_routes:", first.attempted_routes)
    print("served by:", first.provider, "/", first.model)
    print("owner_name:", repr(first.fields["owner_name"].value),
          "survey_number:", repr(first.fields["survey_number"].value))
    print("cache_hit:", first.cache_hit)
    if first.provider != "openrouter":
        print("FAILOVER FAILED: fallback lane did not serve")
        return 1

    second = service.extract_land_record(payload)
    print("second call cache_hit:", second.cache_hit)
    print("second call attempted_routes:", second.attempted_routes)
    if not second.cache_hit:
        print("CACHE FAILED: second identical call missed")
        return 1
    print("FAILOVER_PROVED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
