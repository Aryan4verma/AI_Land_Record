"""Deterministic validation layer (STEP 08, 08_VALIDATION_SPECIFICATION).

The LLM is never the validator: these pure functions check extracted
values and return explainable issues. No I/O, no DB, no LLM here —
reference data and existing records are passed in by the caller.
"""

from .duplicates import duplicate_issue, find_duplicates
from .models import ReferenceData, ValidationIssue, demo_reference
from .normalize import normalize_record
from .rules import approval_blocked, record_verdict, validate_record

__all__ = [
    "ReferenceData",
    "ValidationIssue",
    "approval_blocked",
    "demo_reference",
    "duplicate_issue",
    "find_duplicates",
    "normalize_record",
    "record_verdict",
    "validate_record",
]
