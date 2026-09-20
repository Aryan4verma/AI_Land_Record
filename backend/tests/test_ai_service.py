"""Provider layer checks with a mocked HTTP transport (no live calls)."""
import json

import httpx
import pytest

from app.ai.errors import (
    ProviderAuthError,
    ProviderBadRequestError,
    ProviderBadResponseError,
    ProviderNotConfiguredError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from app.ai.gemini import GeminiAdapter
from app.ai.prompt import build_prompt
from app.ai.service import AIService, _REGISTRY
from app.ai.types import KNOWN_FIELDS, ExtractionInput

SAMPLE_OCR = (
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


def _fields(**overrides):
    base = {
        "owner_name": {"value": "Ramesh Kumar", "confidence": 0.97},
        "survey_number": {"value": "145/2", "confidence": 0.9},
        "area": {"value": 2.45, "confidence": 0.88},
        "village": {"value": None, "confidence": None},
    }
    base.update(overrides)
    return {"fields": base}


def _gemini_envelope(text: str, status: int = 200) -> httpx.Response:
    return httpx.Response(
        status,
        json={
            "candidates": [
                {"content": {"parts": [{"text": text}], "role": "model"}, "finishReason": "STOP"}
            ]
        },
    )


def _adapter(handler, **kwargs) -> GeminiAdapter:
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return GeminiAdapter(api_key="test-key", model="test-model", client=client, **kwargs)


def test_prompt_covers_schema_and_marks_text_untrusted():
    prompt = build_prompt(ExtractionInput(ocr_text=SAMPLE_OCR, document_type="khata"))
    for name in KNOWN_FIELDS:
        assert name in prompt
    assert SAMPLE_OCR in prompt
    assert "null" in prompt and "NEVER invent" in prompt


def test_success_mapping_and_metadata():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        seen["body"] = json.loads(request.content.decode())
        return _gemini_envelope(json.dumps(_fields()))

    result = _adapter(handler).extract(ExtractionInput(ocr_text=SAMPLE_OCR))
    assert seen["path"].endswith(":generateContent")
    assert seen["body"]["generationConfig"]["responseMimeType"] == "application/json"
    assert result.provider == "gemini"
    assert result.model == "test-model"
    assert result.prompt_version and result.schema_version
    assert result.elapsed_seconds >= 0
    assert result.fields["owner_name"].value == "Ramesh Kumar"
    assert result.fields["owner_name"].confidence == pytest.approx(0.97)
    assert result.fields["owner_name"].extraction_status == "EXTRACTED"
    assert result.fields["area"].value == "2.45"  # numbers coerced to strings
    assert result.fields["village"].value is None
    assert result.fields["village"].extraction_status == "MISSING"
    assert result.fields["district"].value is None  # absent keys are MISSING
    assert set(result.fields) == set(KNOWN_FIELDS)  # unknown keys dropped


def test_code_fences_stripped():
    handler = lambda request: _gemini_envelope("```json\n" + json.dumps(_fields()) + "\n```")  # noqa: E731
    result = _adapter(handler).extract(ExtractionInput(ocr_text=SAMPLE_OCR))
    assert result.fields["owner_name"].value == "Ramesh Kumar"


def test_confidence_clamped_and_bad_values_nulled():
    payload = _fields(owner_name={"value": "X", "confidence": 7.5}, survey_number={"value": "Y"})
    result = _adapter(lambda request: _gemini_envelope(json.dumps(payload))).extract(
        ExtractionInput(ocr_text=SAMPLE_OCR)
    )
    assert result.fields["owner_name"].confidence == 1.0
    assert result.fields["survey_number"].confidence is None


@pytest.mark.parametrize(
    ("status", "error"),
    [
        (429, ProviderRateLimitError),
        (401, ProviderAuthError),
        (403, ProviderAuthError),
        (400, ProviderBadRequestError),
        (500, ProviderUnavailableError),
        (503, ProviderUnavailableError),
    ],
)
def test_http_statuses_classified(status, error):
    adapter = _adapter(lambda request: httpx.Response(status, json={"error": {"message": "x"}}))
    with pytest.raises(error):
        adapter.extract(ExtractionInput(ocr_text=SAMPLE_OCR))


def test_timeout_classified():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("slow")

    with pytest.raises(ProviderTimeoutError):
        _adapter(handler).extract(ExtractionInput(ocr_text=SAMPLE_OCR))


def test_catch_all_carries_redacted_diagnostics():
    def handler(request: httpx.Request) -> httpx.Response:
        assert "key=" in str(request.url)  # key travels in query: must be redacted below
        return httpx.Response(
            404, json={"error": {"code": 404, "message": "models/x not found", "status": "NOT_FOUND"}}
        )

    with pytest.raises(ProviderUnavailableError) as exc_info:
        _adapter(handler).extract(ExtractionInput(ocr_text=SAMPLE_OCR))
    details = exc_info.value.details
    assert details["http_status"] == 404
    assert details["model"] == "test-model"
    assert details["key_configured"] is True
    assert "key=" not in details["endpoint"]
    assert details["endpoint"].endswith(":generateContent")
    assert "body" not in details
    assert "catch-all" in details["code_path"]


@pytest.mark.parametrize("text", ["not json at all", json.dumps({"nope": 1}), json.dumps({"fields": [1, 2]})])
def test_malformed_model_output_rejected(text):
    adapter = _adapter(lambda request: _gemini_envelope(text))
    with pytest.raises(ProviderBadResponseError):
        adapter.extract(ExtractionInput(ocr_text=SAMPLE_OCR))


def test_empty_candidates_rejected():
    adapter = _adapter(lambda request: httpx.Response(200, json={"candidates": []}))
    with pytest.raises(ProviderBadResponseError):
        adapter.extract(ExtractionInput(ocr_text=SAMPLE_OCR))


def test_missing_key_and_unknown_provider():
    with pytest.raises(ProviderNotConfiguredError):
        GeminiAdapter(api_key="", model="m")
    with pytest.raises(ProviderNotConfiguredError):
        AIService(provider="nope", model="m", api_key="k")


def test_service_dispatch_is_provider_independent(monkeypatch):
    calls = []

    class FakeProvider:
        name = "fake"

        def __init__(self, *, api_key, model, timeout_seconds=60):
            calls.append((api_key, model, timeout_seconds))

        def extract(self, payload):
            from app.ai.types import ExtractionResult

            return ExtractionResult(provider="fake", model="m", raw_response=f"extracted:{payload.ocr_text[:3]}")

    monkeypatch.setitem(_REGISTRY, "fake", FakeProvider)
    service = AIService(provider="fake", model="m", api_key="k", timeout_seconds=5)
    assert service.provider_name == "fake"
    result = service.extract_land_record(ExtractionInput(ocr_text=SAMPLE_OCR))
    assert result.raw_response == "extracted:SAM"
    assert result.attempted_routes[0]["outcome"] == "ok"
    assert calls == [("k", "m", 5)]
    assert "gemini" in _REGISTRY  # first provider registered
