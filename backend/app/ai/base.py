"""The single interface the application depends on (06 section 4).

Providers implement this Protocol with the constructor signature
`(api_key, model, timeout_seconds)` so `AIService` can instantiate them
from configuration alone. OpenRouter additionally accepts an optional
`fallback_models` list for its native model fallback; every other
provider ignores it.
"""
from typing import Protocol

from .types import ExtractionInput, ExtractionResult


class ExtractionProvider(Protocol):
    name: str

    def extract(self, payload: ExtractionInput) -> ExtractionResult: ...
