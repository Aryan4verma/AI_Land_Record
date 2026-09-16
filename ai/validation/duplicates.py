"""Duplicate detection (08 section 7).

Configured combination: survey_number + village (+ owner as context).
Outcomes are NO_MATCH or POSSIBLE_DUPLICATE only — the MVP never confirms
a duplicate automatically, and a possible duplicate is NEVER labeled fraud.
"""
from .models import ValidationIssue


def _key(value: object) -> str:
    import re

    return re.sub(r"\s+", " ", str(value or "").strip().lower())


def find_duplicates(candidate: dict, existing: list[dict]) -> tuple[str, list[dict]]:
    """Return (verdict, matches). `existing` holds normalized record dicts
    (each optionally with an 'id'); the candidate itself must be excluded
    by the caller via its id."""
    matches = []
    survey, village = _key(candidate.get("survey_number")), _key(candidate.get("village"))
    if not survey or not village:
        return "NO_MATCH", []
    for record in existing:
        if _key(record.get("survey_number")) == survey and _key(record.get("village")) == village:
            matches.append(record)
    return ("POSSIBLE_DUPLICATE", matches) if matches else ("NO_MATCH", [])


def duplicate_issue(candidate: dict, matches: list[dict]) -> ValidationIssue:
    survey = str(candidate.get("survey_number") or "").strip()
    village = str(candidate.get("village") or "").strip()
    return ValidationIssue(
        rule_id="DUP_CANDIDATE_001",
        field_name="survey_number",
        status="REVIEW_REQUIRED",
        severity="WARNING",
        message=(
            f"Possible duplicate: survey number {survey!r} in village {village!r} "
            f"matches {len(matches)} existing record(s). This is a review prompt, "
            "not a fraud finding — the same parcel may legitimately be "
            "re-digitized. Reviewer: compare against the matched record(s) "
            "before approving."
        ),
    )
