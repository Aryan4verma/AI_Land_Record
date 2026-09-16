"""Shared model-output mapping (STEP 13).

Both adapters receive the same contract — a JSON object shaped
{"fields": {"<04 field>": {"value": ..., "confidence": ...}, ...}} —
so coercion, fence-stripping and envelope checks live here once.
Unknown fields are dropped; absent ones become MISSING; nothing is
ever invented to fill the schema.
"""
import json

from .errors import ProviderBadResponseError
from .types import KNOWN_FIELDS, FieldResult


def coerce_value(raw: object) -> tuple[str | None, str]:
    """Return (value, status). Scalars become strings; null stays MISSING."""
    if raw is None:
        return None, "MISSING"
    if isinstance(raw, bool):
        return str(raw).lower(), "EXTRACTED"
    if isinstance(raw, (str, int, float)):
        text = str(raw).strip()
        return (text or None), ("EXTRACTED" if text else "MISSING")
    return None, "UNCERTAIN"


def coerce_confidence(raw: object) -> float | None:
    try:
        number = float(raw)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    if number != number:  # NaN guard
        return None
    return min(1.0, max(0.0, number))


def strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        lines = lines[1:] if len(lines) > 1 else []
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


def parse_fields_envelope(provider: str, raw_text: str) -> dict:
    """Parse the {"fields": {...}} envelope or raise a classified error."""
    try:
        data = json.loads(raw_text)
    except ValueError as exc:
        raise ProviderBadResponseError(provider, "Model did not return valid JSON.") from exc
    if not isinstance(data, dict) or not isinstance(data.get("fields"), dict):
        raise ProviderBadResponseError(provider, "Model JSON lacks the 'fields' object.")
    return data["fields"]


def map_fields(model_fields: dict) -> dict[str, FieldResult]:
    result: dict[str, FieldResult] = {}
    for name in KNOWN_FIELDS:
        entry = model_fields.get(name)
        if not isinstance(entry, dict):
            result[name] = FieldResult(name, None, None, None, "MISSING")
            continue
        value, status = coerce_value(entry.get("value"))
        result[name] = FieldResult(
            field_name=name,
            value=value,
            confidence=coerce_confidence(entry.get("confidence")),
            source_text=None,
            extraction_status=status,
        )
    return result
