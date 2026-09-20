"""Second provider: OpenRouter via its OpenAI-compatible chat API.

Uses OpenRouter's NATIVE model fallback (07 section 5, 06 section 5):
the request carries "models": [primary, ...fallbacks] and OpenRouter
itself reroutes when the first model is unavailable — no custom
model-loop needed inside this adapter. Provider-level failover
(Gemini -> OpenRouter) stays in AIService.

Key travels ONLY as the Authorization Bearer header (never in URLs, logs
or messages). Shares prompt + field mapping with the Gemini adapter.
"""
import time

import httpx

from .errors import (
    ProviderAuthError,
    ProviderBadRequestError,
    ProviderBadResponseError,
    ProviderNotConfiguredError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from .fields import map_fields, parse_fields_envelope, strip_fences
from .prompt import PROMPT_VERSION, SCHEMA_VERSION, build_prompt
from .types import ExtractionInput, ExtractionResult

_API_URL = "https://openrouter.ai/api/v1/chat/completions"


class OpenRouterAdapter:
    name = "openrouter"

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        timeout_seconds: int = 60,
        client: httpx.Client | None = None,
        fallback_models: list[str] | None = None,
    ) -> None:
        if not api_key:
            raise ProviderNotConfiguredError(self.name, "OPENROUTER_API_KEY is not set.")
        if not model:
            raise ProviderNotConfiguredError(self.name, "AI model is not configured.")
        self._api_key = api_key
        self._model = model
        self._fallback_models = [m for m in (fallback_models or []) if m and m != model]
        self._client = client or httpx.Client(
            timeout=httpx.Timeout(timeout_seconds, connect=10.0),
            headers={"Content-Type": "application/json"},
        )

    @property
    def native_models(self) -> list[str]:
        """Full model list handed to OpenRouter for native fallback."""
        return [self._model, *self._fallback_models]

    def _diagnostic(self, response: httpx.Response | None, code_path: str, exc: Exception | None = None) -> dict:
        endpoint, status = "unknown", None
        if response is not None:
            url = response.request.url
            endpoint = f"{url.scheme}://{url.host}{url.path}"
            status = response.status_code
        return {
            "http_status": status, "endpoint": endpoint, "model": self._model,
            "key_configured": bool(self._api_key),
            "exception": type(exc).__name__ if exc is not None else None, "code_path": code_path,
        }

    def extract(self, payload: ExtractionInput) -> ExtractionResult:
        started = time.perf_counter()
        body = {
            "model": self._model,
            "models": self.native_models,
            "messages": [{"role": "user", "content": build_prompt(payload)}],
            "response_format": {"type": "json_object"},
            "temperature": 0.0,
        }
        try:
            response = self._client.post(
                _API_URL, headers={"Authorization": f"Bearer {self._api_key}"}, json=body
            )
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError(
                self.name, "OpenRouter request timed out.",
                self._diagnostic(None, "OpenRouterAdapter.extract:timeout", exc)) from exc
        except httpx.HTTPError as exc:
            raise ProviderUnavailableError(
                self.name, "OpenRouter is unreachable.",
                self._diagnostic(None, "OpenRouterAdapter.extract:transport", exc)) from exc

        self._raise_for_status(response)
        raw_text = self._read_text(response)
        fields = map_fields(parse_fields_envelope(self.name, raw_text))
        return ExtractionResult(
            fields=fields, provider=self.name, model=self._model,
            prompt_version=PROMPT_VERSION, schema_version=SCHEMA_VERSION,
            elapsed_seconds=time.perf_counter() - started, raw_response=raw_text,
        )

    def _raise_for_status(self, response: httpx.Response) -> None:
        status = response.status_code
        if status == 200:
            error = self._api_error(response)
            if error is None:
                return
            status = error  # OpenRouter 200-envelope carrying an error code
        if status == 429:
            raise ProviderRateLimitError(self.name, "OpenRouter rate limit exceeded.",
                                         self._diagnostic(response, "OpenRouterAdapter.extract:429"))
        if status in (401, 403):
            raise ProviderAuthError(self.name, "OpenRouter rejected the API key.",
                                    self._diagnostic(response, "OpenRouterAdapter.extract:401/403"))
        if status == 400:
            raise ProviderBadRequestError(self.name, "OpenRouter rejected the request.",
                                          self._diagnostic(response, "OpenRouterAdapter.extract:400"))
        raise ProviderUnavailableError(self.name, "OpenRouter returned an unexpected status.",
                                       self._diagnostic(response, "OpenRouterAdapter.extract:unexpected"))

    @staticmethod
    def _api_error(response: httpx.Response) -> int | None:
        """Map an OpenRouter 200-embedded {"error": {...}} envelope, if present."""
        try:
            error = response.json().get("error")
        except ValueError:
            return None
        if not isinstance(error, dict) or "choices" in (response.json() or {}):
            return None
        try:
            return int(error.get("code") or 0) or None
        except (TypeError, ValueError):
            return None

    def _read_text(self, response: httpx.Response) -> str:
        try:
            data = response.json()
            text = data["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError, AttributeError) as exc:
            raise ProviderBadResponseError(self.name, "OpenRouter response has no text content.") from exc
        if not isinstance(text, str):
            raise ProviderBadResponseError(self.name, "OpenRouter response has no text content.")
        text = strip_fences(text)
        if not text:
            raise ProviderBadResponseError(self.name, "OpenRouter returned empty content.")
        return text
