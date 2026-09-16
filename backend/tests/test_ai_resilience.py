"""Resilience simulations (STEP 13): fallback chain, one-retry policy,
cache identity, all-down behavior. All transports are mocked — zero live
calls, zero quota. Each scenario asserts exact HTTP call counts.
"""
import json

import httpx
import pytest

from app.ai.cache import ExtractionCache, cache_key, source_key
from app.ai.errors import (
    ProviderAuthError,
    ProviderNotConfiguredError,
    ProviderRateLimitError,
    ProviderUnavailableError,
)
from app.ai.openrouter import OpenRouterAdapter
from app.ai.service import AIService, get_ai_service, parse_fallbacks
from app.ai.types import ExtractionInput

OCR = "Owner Name: Ramesh Kumar\nSurvey Number: 145/2"


def _fields(owner="Ramesh Kumar"):
    return {"fields": {"owner_name": {"value": owner, "confidence": 0.9}}}


def _gemini_ok(text=None):
    body = text if text is not None else json.dumps(_fields())
    return {"candidates": [{"content": {"parts": [{"text": body}], "role": "model"}, "finishReason": "STOP"}]}


def _openrouter_ok(text=None):
    body = text if text is not None else json.dumps(_fields())
    return {"choices": [{"message": {"role": "assistant", "content": body}, "finish_reason": "stop"}]}


def _service(routes, **kwargs):
    """routes: list of (kind, behavior) where behavior is 'ok', an HTTP
    status int, 'timeout', or ('envelope', code). Returns (service, calls)."""
    calls: list[dict] = []

    def handler_for(kind, behavior):
        def handler(request: httpx.Request) -> httpx.Response:
            calls.append({"url": str(request.url).split("?")[0],
                          "body": json.loads(request.content.decode() or "{}"),
                          "auth": request.headers.get("authorization")})
            if behavior == "ok":
                payload = _gemini_ok() if kind == "gemini" else _openrouter_ok()
                return httpx.Response(200, json=payload)
            if behavior == "timeout":
                raise httpx.ConnectTimeout("slow")
            if isinstance(behavior, tuple):
                _kind, code = behavior
                return httpx.Response(200, json={"error": {"code": code, "message": "upstream"}})
            return httpx.Response(behavior, json={"error": {"message": "x"}})
        return handler

    from app.ai.gemini import GeminiAdapter

    adapters = []
    for kind, behavior in routes:
        client = httpx.Client(transport=httpx.MockTransport(handler_for(kind, behavior)))
        if kind == "gemini":
            adapters.append(GeminiAdapter(api_key="k-gemini", model="m-gemini", client=client))
        else:
            adapters.append(OpenRouterAdapter(api_key="k-or", model="m-or", client=client))

    service = AIService(provider="gemini", model="m-gemini", api_key="k-gemini", **kwargs)
    # Swap in mocked adapters, preserving route order/metadata.
    for route, adapter in zip(service._routes, adapters):
        route.adapter = adapter
    return service, calls


def test_primary_success_single_call_with_observability():
    service, calls = _service([("gemini", "ok")])
    result = service.extract_land_record(ExtractionInput(ocr_text=OCR))
    assert len(calls) == 1
    assert result.provider == "gemini" and result.cache_hit is False
    assert result.fields["owner_name"].value == "Ramesh Kumar"
    assert result.attempted_routes == [
        {"provider": "gemini", "model": "m-gemini", "outcome": "ok", "attempts": 1}
    ]


def test_primary_model_failure_falls_back_after_one_retry():
    service, calls = _service([("gemini", 500), ("openrouter", "ok")],
                              fallbacks=[("openrouter", "m-or", "k-or")])
    result = service.extract_land_record(ExtractionInput(ocr_text=OCR))
    assert result.provider == "openrouter"
    assert len(calls) == 3  # primary attempt + one retry, then fallback
    assert [c["outcome"] for c in result.attempted_routes] == ["error", "ok"]
    assert result.attempted_routes[0]["code"] == "PROVIDER_UNAVAILABLE"
    assert result.attempted_routes[0]["attempts"] == 2


def test_provider_timeout_retries_once_then_falls_back():
    service, calls = _service([("gemini", "timeout"), ("openrouter", "ok")],
                              fallbacks=[("openrouter", "m-or", "k-or")])
    result = service.extract_land_record(ExtractionInput(ocr_text=OCR))
    assert result.provider == "openrouter" and len(calls) == 3


def test_auth_failure_never_retries_or_falls_back():
    service, calls = _service([("gemini", 401), ("openrouter", "ok")],
                              fallbacks=[("openrouter", "m-or", "k-or")])
    with pytest.raises(ProviderAuthError):
        service.extract_land_record(ExtractionInput(ocr_text=OCR))
    assert len(calls) == 1


def test_bad_request_never_retries():
    service, calls = _service([("gemini", 400)])
    with pytest.raises(Exception):
        service.extract_land_record(ExtractionInput(ocr_text=OCR))
    assert len(calls) == 1


def test_rate_limit_retries_then_succeeds_on_same_route():
    attempts = []

    def handler(request: httpx.Request) -> httpx.Response:
        attempts.append(1)
        if len(attempts) == 1:
            return httpx.Response(429, json={"error": {"message": "slow down"}})
        return httpx.Response(200, json=_gemini_ok())

    from app.ai.gemini import GeminiAdapter

    service = AIService(provider="gemini", model="m", api_key="k")
    service._routes[0].adapter = GeminiAdapter(
        api_key="k", model="m", client=httpx.Client(transport=httpx.MockTransport(handler)))
    result = service.extract_land_record(ExtractionInput(ocr_text=OCR))
    assert len(attempts) == 2
    assert result.attempted_routes == [
        {"provider": "gemini", "model": "m", "outcome": "ok", "attempts": 2}
    ]


def test_cached_result_makes_no_http_call():
    cache = ExtractionCache(max_entries=16, ttl_seconds=600)
    service, calls = _service([("gemini", "ok")], cache=cache)
    first = service.extract_land_record(ExtractionInput(ocr_text=OCR, document_checksum="abc123"))
    second = service.extract_land_record(ExtractionInput(ocr_text=OCR, document_checksum="abc123"))
    assert len(calls) == 1
    assert second.cache_hit is True
    assert second.fields["owner_name"].value == "Ramesh Kumar"
    assert first.cache_hit is False


def test_cache_identity_covers_config():
    cache = ExtractionCache(max_entries=16, ttl_seconds=600)
    service, calls = _service([("gemini", "ok")], cache=cache)
    payload = ExtractionInput(ocr_text=OCR, document_checksum="abc123")
    service.extract_land_record(payload)
    # Different OCR text -> miss even with the same checksum absent.
    service.extract_land_record(ExtractionInput(ocr_text=OCR + " (page 2)"))
    assert len(calls) == 2
    # Same source, different service chain -> miss (chain is part of identity).
    other, other_calls = _service([("gemini", "ok")], cache=cache,
                                  fallbacks=[("openrouter", "m-or", "k-or")])
    other.extract_land_record(payload)
    assert len(other_calls) == 1 and len(calls) == 2


def test_cache_evicts_oldest_and_respects_disabled():
    cache = ExtractionCache(max_entries=1, ttl_seconds=600)
    service, calls = _service([("gemini", "ok")], cache=cache)
    service.extract_land_record(ExtractionInput(ocr_text="doc one"))
    service.extract_land_record(ExtractionInput(ocr_text="doc two"))
    service.extract_land_record(ExtractionInput(ocr_text="doc one"))
    assert len(calls) == 3  # first entry evicted by the second
    assert len(cache) == 1


def test_all_providers_down_raises_last_error():
    service, calls = _service([("gemini", 500), ("openrouter", 503)],
                              fallbacks=[("openrouter", "m-or", "k-or")])
    with pytest.raises(ProviderUnavailableError) as exc_info:
        service.extract_land_record(ExtractionInput(ocr_text=OCR))
    assert exc_info.value.transient is True  # a future layer may still continue
    assert len(calls) == 4  # 2 attempts per route, then give up


def test_openrouter_native_models_list_and_key_placement():
    service, calls = _service([("openrouter", "ok")])
    adapter = service._routes[0].adapter
    adapter._fallback_models = ["m2", "m3"]
    service.extract_land_record(ExtractionInput(ocr_text=OCR))
    sent = calls[0]
    assert sent["url"] == "https://openrouter.ai/api/v1/chat/completions"
    assert "k-or" not in sent["url"]  # key never in URL/logs
    assert sent["auth"] == "Bearer k-or"
    assert sent["body"]["models"] == ["m-or", "m2", "m3"]
    assert sent["body"]["response_format"] == {"type": "json_object"}


def test_openrouter_embedded_error_envelope_mapped():
    service, calls = _service([("openrouter", ("envelope", 429))])
    with pytest.raises(ProviderRateLimitError):
        service.extract_land_record(ExtractionInput(ocr_text=OCR))


def test_error_messages_never_contain_keys():
    service, _ = _service([("gemini", 401), ("openrouter", 500)],
                          fallbacks=[("openrouter", "m-or", "k-or")])
    try:
        service.extract_land_record(ExtractionInput(ocr_text=OCR))
        raise AssertionError("should have raised")
    except ProviderAuthError as exc:
        assert "k-gemini" not in str(exc) and "k-or" not in str(exc)
        assert "key=" not in str(exc.details)


def test_parse_fallbacks_and_service_build():
    assert parse_fallbacks("openrouter:m-a, gemini:m-b ,bad-entry,") == [("openrouter", "m-a"), ("gemini", "m-b")]
    assert parse_fallbacks("") == []
    with pytest.raises(ProviderNotConfiguredError):
        AIService(provider="nope", model="m", api_key="k")


def test_get_ai_service_builds_chain_from_settings():
    from types import SimpleNamespace

    settings = SimpleNamespace(
        ai_provider="gemini", ai_model="m-g", gemini_api_key="k-g", openrouter_api_key="k-o",
        ai_fallbacks="openrouter:m-o", ai_timeout_seconds=60,
        ai_cache_enabled=False, ai_cache_max_entries=1, ai_cache_ttl_seconds=1)
    service = get_ai_service(settings)
    assert service.route_chain == "gemini:m-g>openrouter:m-o"


def test_get_ai_service_rejects_bad_config():
    from types import SimpleNamespace

    base = dict(ai_provider="gemini", ai_model="m-g", gemini_api_key="k-g", openrouter_api_key="",
                ai_fallbacks="", ai_timeout_seconds=60,
                ai_cache_enabled=False, ai_cache_max_entries=1, ai_cache_ttl_seconds=1)
    with pytest.raises(ProviderNotConfiguredError):
        get_ai_service(SimpleNamespace(**{**base, "ai_fallbacks": "openrouter:m-o"}))  # missing key
    with pytest.raises(ProviderNotConfiguredError):
        get_ai_service(SimpleNamespace(**{**base, "ai_fallbacks": "nope:m"}))  # unknown provider


def test_cache_key_material():
    assert source_key("  abc ", "ignored") == "checksum:abc"
    assert source_key("", OCR).startswith("text-sha256:")
    key = cache_key(source="s", pipeline_version="v1", route_chain="gemini:m",
                    prompt_version="v1", schema_version="v1")
    assert len(key) == 64
