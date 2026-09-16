"""Normalization (04 section 6): trim, consistent date/area/unit forms.

NON-MUTATING: `normalize_record` never alters its input and returns both
the normalized view and the originals it changed, so raw extraction stays
recoverable for auditability. Unknown units/dates are kept verbatim —
validation flags them instead of guessing (08 section 4).
"""
import re
from datetime import datetime

_WS = re.compile(r"\s+")

# Only unambiguous synonyms are canonicalized. Regional units (bigha,
# guntha, ...) are left untouched and reported as unknown by the rules.
_UNIT_SYNONYMS = {
    "hectare": "hectare",
    "hectares": "hectare",
    "ha": "hectare",
    "acre": "acre",
    "acres": "acre",
    "sqm": "sqm",
    "sq.m.": "sqm",
    "sq meter": "sqm",
    "sq meters": "sqm",
    "sq metre": "sqm",
    "sq metres": "sqm",
}

KNOWN_UNITS = {"hectare", "acre", "sqm"}

_DATE_FORMATS = ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y")


def normalize_text(value: object) -> object:
    if not isinstance(value, str):
        return value
    return _WS.sub(" ", value.strip())


def parse_area(value: object) -> tuple[str | None, bool]:
    """Return (canonical_decimal_string, is_numeric). Never raises."""
    if value is None:
        return None, False
    text = _WS.sub("", str(value).strip())
    if not re.fullmatch(r"-?\d[\d,]*(\.\d+)?", text):
        return str(value).strip() or None, False
    return text.replace(",", ""), True


def normalize_unit(value: object) -> object:
    if not isinstance(value, str):
        return value
    key = _WS.sub(" ", value.strip().lower())
    return _UNIT_SYNONYMS.get(key, value.strip() if value.strip() else value)


def normalize_date(value: object) -> object:
    if not isinstance(value, str):
        return value
    text = value.strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    return text or value


def normalize_record(values: dict) -> dict:
    """Return {"normalized": {...}, "originals": {name: raw}}.

    `originals` holds only fields whose normalized form differs, so the
    raw extraction is always recoverable. The input dict is not modified.
    """
    normalized: dict = {}
    originals: dict = {}
    for name, raw in values.items():
        if name == "area":
            canonical, _ = parse_area(raw)
            new = canonical
        elif name == "area_unit":
            new = normalize_unit(raw)
        elif name == "record_date":
            new = normalize_date(raw)
        else:
            new = normalize_text(raw)
        normalized[name] = new
        if isinstance(raw, str) and new != raw:
            originals[name] = raw
    return {"normalized": normalized, "originals": originals}
