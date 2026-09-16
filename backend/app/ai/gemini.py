"""First provider: Google Gemini via plain HTTPS (httpx, no SDK needed).

Model and key are environment-driven (Settings.ai_model / GEMINI_API_KEY).
Controlled timeout via httpx; HTTP outcomes map to classified ProviderError
so AIService can retry once and fall back. Field mapping is shared
(see fields.py) so every provider parses the same contract.
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
from .fields import map_fields, parse_fields_envelope
from .prompt import PROMPT_VERSION, SCHEMA_VERSION, build_prompt
from .types import ExtractionInput, ExtractionResult

_API_HOST = "https://generativelanguage.googleapis.com"
_MAX_OUTPUT_TOKENS = 2048


class GeminiAdapter:
    name = "gemini"

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        timeout_seconds: int = 60,
        client: httpx.Client | None = None,
    ) -> None:
        if not api_key:
            raise ProviderNotConfiguredError(self.name, "GEMINI_API_KEY is not set.")
        if not model:
            raise ProviderNotConfiguredError(self.name, "AI model is not configured.")
        self._api_key = api_key
        self._model = model
        self._client = client or httpx.Client(
            timeout=httpx.Timeout(timeout_seconds, connect=10.0),
            headers={"Content-Type": "application/json"},
        )

    def _diagnostic(
        self, response: httpx.Response | None, code_path: str, exc: Exception | None = None
    ) -> dict:
        """Safe facts for this failure. The query string (which carries the
        API key) is stripped by rebuilding scheme://host/path manually."""
        endpoint, status, body = "unknown", None, ""
        if response is not None:
            url = response.request.url
            endpoint = f"{url.scheme}://{url.host}{url.path}"
            status = response.status_code
            try:
                body = response.text[:500]
            except Exception:
                body = ""
        return {
            "http_status": status,
            "endpoint": endpoint,
            "model": self._model,
            "key_configured": bool(self._api_key),
            "body": body,
            "exception": type(exc).__name__ if exc is not None else None,
            "code_path": code_path,
        }

    def extract(self, payload: ExtractionInput) -> ExtractionResult:
        started = time.perf_counter()
        url = f"{_API_HOST}/v1beta/models/{self._model}:generateContent"
        body = {
            "contents": [{"parts": [{"text": build_prompt(payload)}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.0,
                "maxOutputTokens": _MAX_OUTPUT_TOKENS,
            },
        }
        # NOTE: the key travels as a query param; messages below are static
        # strings so the key can never leak into logs via str(exc)/URLs.
        try:
            response = self._client.post(url, params={"key": self._api_key}, json=body)
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError(
                self.name, "Gemini request timed out.",
                self._diagnostic(None, "GeminiAdapter.extract:timeout", exc),
            ) from exc
        except httpx.HTTPError as exc:
            raise ProviderUnavailableError(
                self.name, "Gemini is unreachable.",
                self._diagnostic(None, "GeminiAdapter.extract:transport", exc),
            ) from exc

        if response.status_code == 429:
            raise ProviderRateLimitError(
                self.name, "Gemini rate limit exceeded.",
                self._diagnostic(response, "GeminiAdapter.extract:429"),
            )
        if response.status_code in (401, 403):
            raise ProviderAuthError(
                self.name, "Gemini rejected the API key.",
                self._diagnostic(response, "GeminiAdapter.extract:401/403"),
            )
        if response.status_code == 400:
            raise ProviderBadRequestError(
                self.name, "Gemini rejected the request.",
                self._diagnostic(response, "GeminiAdapter.extract:400"),
            )
        if response.status_code >= 500:
            raise ProviderUnavailableError(
                self.name, "Gemini returned a server error.",
                self._diagnostic(response, "GeminiAdapter.extract:5xx"),
            )
        if response.status_code != 200:
            raise ProviderUnavailableError(
                self.name, "Gemini returned an unexpected status.",
                self._diagnostic(response, "GeminiAdapter.extract:catch-all(!=200)"),
            )

        raw_text = self._read_text(response)
        fields = map_fields(parse_fields_envelope(self.name, raw_text))
        return ExtractionResult(
            fields=fields,
            provider=self.name,
            model=self._model,
            prompt_version=PROMPT_VERSION,
            schema_version=SCHEMA_VERSION,
            elapsed_seconds=time.perf_counter() - started,
            raw_response=raw_text,
        )

    def _read_text(self, response: httpx.Response) -> str:
        try:
            data = response.json()
        except ValueError as exc:
            raise ProviderBadResponseError(self.name, "Gemini returned non-JSON.") from exc
        try:
            candidates = data["candidates"]
            parts = candidates[0]["content"]["parts"]
            text = "".join(part.get("text", "") for part in parts if isinstance(part, dict))
        except (KeyError, IndexError, TypeError, AttributeError) as exc:
            raise ProviderBadResponseError(self.name, "Gemini response has no text content.") from exc
        text = text.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            lines = lines[1:] if len(lines) > 1 else []
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines).strip()
        if not text:
            raise ProviderBadResponseError(self.name, "Gemini returned empty content.")
        return text
