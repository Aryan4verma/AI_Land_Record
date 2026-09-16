"""Confidence combination logic (06 Layer 7). Pure functions, no I/O.

score = mean of available components (OCR, extraction), renormalized when
one is missing; then validation caps; then banding. Missing values and
missing components yield no score and mandatory review — the engine never
invents confidence it does not have.
"""
import re

from .models import (
    FAIL_CAP,
    HIGH_THRESHOLD,
    MEDIUM_THRESHOLD,
    WARNING_CAP,
    FieldConfidence,
    RecordConfidence,
)

_ACTIONABLE_STATUSES = ("FAIL", "REVIEW_REQUIRED")
_ACTIONABLE_SEVERITIES = ("WARNING", "ERROR", "CRITICAL")


def _norm(text: object) -> str:
    return re.sub(r"\s+", " ", str(text or "").strip().lower())


def match_ocr_confidence(value: object, ocr_lines: list[dict]) -> float | None:
    """Best OCR-line confidence whose text contains the extracted value.

    Heuristic and documented as such: OCR output has lines, not fields, so
    the value is located by normalized containment and the strongest
    matching line wins. Returns None when the value is empty or unmatched.
    """
    target = _norm(value)
    if not target:
        return None
    best: float | None = None
    for line in ocr_lines:
        if target in _norm(line.get("text", "")):
            try:
                conf = float(line.get("confidence"))
            except (TypeError, ValueError):
                continue
            if 0.0 <= conf <= 1.0 and (best is None or conf > best):
                best = conf
    return best


def _band(score: float | None) -> str:
    if score is None:
        return "REVIEW_REQUIRED"
    if score >= HIGH_THRESHOLD:
        return "HIGH"
    if score >= MEDIUM_THRESHOLD:
        return "MEDIUM"
    return "LOW"


def _is_actionable(issue: dict) -> bool:
    return issue.get("status") in _ACTIONABLE_STATUSES or issue.get("severity") in _ACTIONABLE_SEVERITIES


def score_field(
    field_name: str,
    value: object,
    extraction_confidence: float | None,
    ocr_lines: list[dict],
    issues: list[dict],
) -> FieldConfidence:
    """Combine OCR + extraction + validation into one scored field."""
    reasons: list[str] = []
    ocr_conf = match_ocr_confidence(value, ocr_lines)
    if ocr_conf is None:
        reasons.append("no matching OCR line found; OCR signal unavailable" if value is not None else "no value to locate in OCR text")
    else:
        reasons.append(f"OCR line confidence {ocr_conf:.2f}")
    if extraction_confidence is None:
        reasons.append("extraction confidence not reported")
    else:
        reasons.append(f"extraction confidence {extraction_confidence:.2f}")

    field_issues = [i for i in issues if i.get("field") == field_name]
    components = [c for c in (ocr_conf, extraction_confidence) if c is not None]
    score: float | None = sum(components) / len(components) if components else None
    if value is None:
        score = None
        reasons.append("value is missing; nothing to score")

    for issue in field_issues:
        reasons.append(f"validation {issue.get('rule_id')} {issue.get('status')}: {issue.get('message', '')[:120]}")
    if any(i.get("status") == "FAIL" or i.get("severity") in ("ERROR", "CRITICAL") for i in field_issues):
        if score is not None:
            score = min(score, FAIL_CAP)
        reasons.append(f"blocking validation issue caps score at {FAIL_CAP}")
    elif any(_is_actionable(i) for i in field_issues):
        if score is not None:
            score = min(score, WARNING_CAP)
        reasons.append(f"review-level validation issue caps score at {WARNING_CAP}")

    band = _band(score)
    review_required = score is None or band == "LOW" or any(_is_actionable(i) for i in field_issues)
    if review_required and score is not None and band != "LOW":
        reasons.append("flagged for human review by validation outcome")
    return FieldConfidence(
        field_name=field_name,
        score=score,
        band=band,
        review_required=review_required,
        ocr_confidence=ocr_conf,
        extraction_confidence=extraction_confidence,
        reasons=reasons,
    )


def score_record(
    document_id: str,
    values: dict,
    confidences: dict,
    ocr_lines: list[dict],
    issues: list[dict],
) -> RecordConfidence:
    """Score every field, then roll up to a record verdict."""
    fields = {
        name: score_field(
            name,
            values.get(name),
            confidences.get(name),
            ocr_lines,
            issues,
        )
        for name in values
    }
    scores = [fc.score for fc in fields.values() if fc.score is not None]
    overall = sum(scores) / len(scores) if scores else None
    record_level = [i for i in issues if i.get("field") is None and _is_actionable(i)]
    reasons = []
    if record_level:
        reasons.append(f"{len(record_level)} record-level validation issue(s) require review")
    review_required = any(fc.review_required for fc in fields.values()) or bool(record_level)
    if overall is None:
        reasons.append("no scorable fields; record needs review")
    return RecordConfidence(
        document_id=document_id,
        fields=fields,
        overall_score=overall,
        overall_band=_band(overall),
        review_required=review_required,
        reasons=reasons,
    )
