"""Typed-column safety at the land_records persistence boundary.

`land_records.record_date` is DATE and `land_records.area` is NUMERIC, but
extraction and normalization deliberately PRESERVE unrecognized values verbatim
(04 section 6, 08 section 4) so a reviewer sees exactly what the document said.
Handing such a value straight to Postgres aborts the entire insert — SQLSTATE
22008 for a date like "99/99/2024", 22P02 for a non-numeric area — and destroys
a record that was supposed to go to a human instead. The validation layer had
already flagged the value correctly (FMT_DATE_001); persistence then threw the
whole document away.

So typed columns receive only values Postgres can actually represent. When a
value cannot be represented:

  * the typed column is stored as NULL,
  * the exact raw string still lands in `extracted_fields.value` (TEXT), and
  * the validation issue that flagged it stays attached to the record,

which means the record reaches human review carrying its own evidence.

Nothing is ever guessed, repaired, reformatted or invented: a value is either
exactly representable or it is NULL plus evidence. Values that ARE valid are
passed through byte-for-byte and are never nulled.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

# land_records columns whose Postgres type will reject a free-text value.
TYPED_COLUMNS = ("record_date", "area")


def _blank(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def coerce_record_date(value: Any) -> tuple[Any, bool]:
    """Return (storable_value, was_dropped).

    Accepts only an ISO calendar date, which is exactly what `normalize_date`
    produces for every format it recognizes — so a legitimate date is never
    dropped, and anything it could not parse (and therefore flagged) is.
    """
    if _blank(value):
        return None, False
    if isinstance(value, date):
        return value.isoformat(), False
    text = str(value).strip()
    try:
        date.fromisoformat(text)
    except ValueError:
        return None, True
    return text, False


def coerce_area(value: Any) -> tuple[Any, bool]:
    """Return (storable_value, was_dropped).

    Accepts a finite decimal number. `parse_area` already returns a canonical
    decimal string for numeric input and the raw string otherwise, so this
    drops exactly the values validation flags as non-numeric. NaN/Infinity are
    refused: they parse as Decimal but are not meaningful areas.
    """
    if _blank(value):
        return None, False
    if isinstance(value, bool):  # bool is an int subclass; never a valid area
        return None, True
    if isinstance(value, (int, float, Decimal)):
        number = Decimal(str(value))
        return (str(value), False) if number.is_finite() else (None, True)
    text = str(value).strip()
    try:
        number = Decimal(text)
    except (InvalidOperation, ValueError):
        return None, True
    if not number.is_finite():
        return None, True
    return text, False


_COERCERS = {"record_date": coerce_record_date, "area": coerce_area}


def coerce_typed_columns(row: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Split a land_records row into (storable_row, dropped_raw_values).

    `dropped_raw_values` maps column -> the exact value that could not be
    represented, for audit metadata. Untyped columns are passed through
    untouched, and a column absent from `row` stays absent.
    """
    safe = dict(row)
    dropped: dict[str, Any] = {}
    for column, coerce in _COERCERS.items():
        if column not in safe:
            continue
        value, was_dropped = coerce(safe[column])
        safe[column] = value
        if was_dropped:
            dropped[column] = row[column]
    return safe, dropped
