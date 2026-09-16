"""Provider-independent entrypoint (06 section 4, 07 sections 6-9).

Application code calls `extract_land_record(payload)` and stays ignorant
of providers. AIService walks an ordered route chain (primary +
AI_FALLBACKS "provider:model" entries): each route gets ONE attempt, plus
ONE retry on transient failures (rate limit, timeout, provider
unavailable) per 07 section 9. Terminal failures (auth, bad request, bad
response, misconfiguration) raise immediately — never retried, never
hidden by failover. Repeat extractions hit the shared result cache keyed
by source + pipeline + route chain + prompt/schema versions. Every result
records which routes handled it.
"""
from collections.abc import Callable
from typing import Any

from .base import ExtractionProvider
from .cache import ExtractionCache, cache_key, source_key
from .errors import ProviderError, ProviderNotConfiguredError
from .gemini import GeminiAdapter
from .openrouter import OpenRouterAdapter
from .prompt import PROMPT_VERSION, SCHEMA_VERSION
from .types import ExtractionInput, ExtractionResult

_FACTORY = Callable[..., ExtractionProvider]

PIPELINE_VERSION = "v1"

_REGISTRY: dict[str, _FACTORY] = {
    GeminiAdapter.name: GeminiAdapter,
    OpenRouterAdapter.name: OpenRouterAdapter,
}

_KEY_BY_PROVIDER = {
    "gemini": "gemini_api_key",
    "openrouter": "openrouter_api_key",
}

_SHARED_CACHE: ExtractionCache | None = None


def parse_fallbacks(raw: str | None) -> list[tuple[str, str]]:
    """Parse AI_FALLBACKS ("provider:model, ...") into ordered routes."""
    routes: list[tuple[str, str]] = []
    for chunk in (raw or "").split(","):
        chunk = chunk.strip()
        if not chunk or ":" not in chunk:
            continue
        provider, model = chunk.split(":", 1)
        provider, model = provider.strip().lower(), model.strip()
        if provider and model:
            routes.append((provider, model))
    return routes


def get_shared_cache(settings: Any) -> ExtractionCache | None:
    """Process-wide cache so repeat calls (new AIService each time) hit it."""
    global _SHARED_CACHE
    if not getattr(settings, "ai_cache_enabled", False):
        return None
    if _SHARED_CACHE is None:
        _SHARED_CACHE = ExtractionCache(
            max_entries=settings.ai_cache_max_entries,
            ttl_seconds=settings.ai_cache_ttl_seconds,
        )
    else:
        _SHARED_CACHE.configure(
            max_entries=settings.ai_cache_max_entries,
            ttl_seconds=settings.ai_cache_ttl_seconds,
        )
    return _SHARED_CACHE


class _Route:
    """One provider+model attempt lane with its own adapter instance."""

    def __init__(self, provider: str, model: str, api_key: str, timeout_seconds: int,
                 fallback_models: list[str] | None = None) -> None:
        try:
            factory = _REGISTRY[provider]
        except KeyError:
            raise ProviderNotConfiguredError(provider, f"Unknown AI provider: {provider}.") from None
        if not api_key:
            raise ProviderNotConfiguredError(provider, f"No API key configured for provider '{provider}'.")
        if not model:
            raise ProviderNotConfiguredError(provider, "AI model is not configured.")
        self.provider = provider
        self.model = model
        if provider == OpenRouterAdapter.name:
            self.adapter = factory(api_key=api_key, model=model, timeout_seconds=timeout_seconds,
                                   fallback_models=list(fallback_models or []))
        else:
            self.adapter = factory(api_key=api_key, model=model, timeout_seconds=timeout_seconds)


class AIService:
    def __init__(self, *, provider: str, model: str, api_key: str, timeout_seconds: int = 60,
                 fallbacks: list[tuple] | None = None,
                 cache: ExtractionCache | None = None) -> None:
        # Backward-compatible: provider/model/api_key form the first route;
        # fallbacks entries are (provider, model, api_key[, fallback_models]).
        entries: list[tuple] = [(provider, model, api_key, [])]
        entries.extend(tuple(entry) for entry in (fallbacks or []))
        self._routes = [
            _Route(entry[0], entry[1], entry[2], timeout_seconds,
                   list(entry[3]) if len(entry) > 3 else [])
            for entry in entries
        ]
        self._cache = cache

    @property
    def provider_name(self) -> str:
        return self._routes[0].provider

    @property
    def model(self) -> str:
        return self._routes[0].model

    @property
    def route_chain(self) -> str:
        return ">".join(f"{route.provider}:{route.model}" for route in self._routes)

    def _cache_lookup_key(self, payload: ExtractionInput) -> str | None:
        if self._cache is None:
            return None
        return cache_key(
            source=source_key(payload.document_checksum, payload.ocr_text),
            pipeline_version=PIPELINE_VERSION,
            route_chain=self.route_chain,
            prompt_version=PROMPT_VERSION,
            schema_version=SCHEMA_VERSION,
        )

    def extract_land_record(self, payload: ExtractionInput) -> ExtractionResult:
        key = self._cache_lookup_key(payload)
        if key is not None:
            hit = self._cache.get(key)
            if hit is not None:
                return hit
        attempted: list[dict] = []
        last_error: ProviderError | None = None
        for route in self._routes:
            try:
                result = self._attempt(route, payload, attempted)
            except ProviderError as exc:
                if not exc.transient:
                    raise
                last_error = exc
                continue
            result.attempted_routes = attempted
            if key is not None and self._cache is not None:
                self._cache.put(key, result)
            return result
        assert last_error is not None  # routes non-empty by construction
        raise last_error

    @staticmethod
    def _attempt(route: _Route, payload: ExtractionInput, attempted: list[dict]) -> ExtractionResult:
        attempts = 1
        try:
            result = route.adapter.extract(payload)
        except ProviderError as exc:
            if not exc.transient:
                attempted.append({"provider": route.provider, "model": route.model,
                                  "outcome": "error", "code": exc.code, "attempts": 1})
                raise
            # One appropriate retry on the same route (07 section 9).
            attempts = 2
            try:
                result = route.adapter.extract(payload)
            except ProviderError as exc2:
                attempted.append({"provider": route.provider, "model": route.model,
                                  "outcome": "error", "code": exc2.code, "attempts": attempts})
                raise exc2 from None
        attempted.append({"provider": route.provider, "model": route.model,
                          "outcome": "ok", "attempts": attempts})
        return result


def get_ai_service(settings: Any = None) -> AIService:
    from ..config import get_settings

    active = settings or get_settings()

    def key_for(name: str) -> str:
        attr = _KEY_BY_PROVIDER.get(name)
        return (getattr(active, attr, "") or "") if attr else ""

    chain: list[tuple[str, str, str]] = []
    primary_provider = (active.ai_provider or "").strip().lower()
    chain.append((primary_provider, (active.ai_model or "").strip(), key_for(primary_provider)))
    for fallback_provider, fallback_model in parse_fallbacks(active.ai_fallbacks):
        chain.append((fallback_provider, fallback_model, key_for(fallback_provider)))

    # Validate everything upfront: misconfiguration fails fast, never silently.
    for entry_provider, entry_model, entry_key in chain:
        if entry_provider not in _REGISTRY:
            raise ProviderNotConfiguredError(entry_provider, f"Unknown AI provider: {entry_provider}.")
        if not entry_key:
            raise ProviderNotConfiguredError(entry_provider, f"No API key configured for provider '{entry_provider}'.")
        if not entry_model:
            raise ProviderNotConfiguredError(entry_provider, "AI model is not configured.")

    # OpenRouter natively falls back across its own models: collapse every
    # OpenRouter lane into the first one, carrying the rest as its native list.
    or_models = [model for (provider, model, _key) in chain if provider == OpenRouterAdapter.name]
    lanes: list[tuple] = []
    or_folded = False
    for entry_provider, entry_model, entry_key in chain:
        if entry_provider == OpenRouterAdapter.name:
            if or_folded:
                continue
            or_folded = True
            lanes.append((entry_provider, entry_model, entry_key,
                          [m for m in or_models if m != entry_model]))
        else:
            lanes.append((entry_provider, entry_model, entry_key, []))
    first = lanes[0]
    return AIService(
        provider=first[0], model=first[1], api_key=first[2],
        timeout_seconds=active.ai_timeout_seconds,
        fallbacks=[lane for lane in lanes[1:]],
        cache=get_shared_cache(active),
    )


def extract_land_record(payload: ExtractionInput) -> ExtractionResult:
    """The one function the rest of the application calls."""
    return get_ai_service().extract_land_record(payload)
