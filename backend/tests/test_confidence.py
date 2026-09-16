"""Confidence engine checks: bands, caps, review routing, explanations."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ai.confidence.engine import match_ocr_confidence, score_field, score_record  # noqa: E402

LINES = [
    {"text": "Owner Name: Ramesh Kumar", "confidence": 0.95},
    {"text": "Survey Number: 145/2", "confidence": 0.90},
    {"text": "Area: 2.45 Hectare", "confidence": 0.60},
]


def _issue(rule, field, status="WARNING", severity="WARNING", message="check this"):
    return {"rule_id": rule, "field": field, "status": status, "severity": severity, "message": message}


def test_high_quality_extraction_is_high_without_review():
    fc = score_field("owner_name", "Ramesh Kumar", 0.95, LINES, [])
    assert fc.score == 0.95
    assert fc.band == "HIGH"
    assert fc.review_required is False
    assert any("OCR" in r for r in fc.reasons) and any("extraction" in r for r in fc.reasons)


def test_low_ocr_confidence_drags_band_to_low_with_review():
    fc = score_field("area", "2.45", 0.85, [{"text": "Area: 2.45", "confidence": 0.25}], [])
    assert fc.score == 0.55
    assert fc.band == "LOW"
    assert fc.review_required is True


def test_missing_extraction_component_renormalizes():
    fc = score_field("owner_name", "Ramesh Kumar", None, LINES, [])
    assert fc.score == 0.95
    assert fc.band == "HIGH"


def test_validation_fail_caps_to_low_despite_high_inputs():
    fc = score_field("area", "0", 0.95, [{"text": "Area: 0", "confidence": 0.95}],
                     [_issue("FMT_AREA_002", "area", "FAIL", "ERROR", "must be positive")])
    assert fc.score is not None and fc.score <= 0.39
    assert fc.band == "LOW"
    assert fc.review_required is True
    assert any("caps score" in r for r in fc.reasons)


def test_validation_warning_caps_to_medium_with_review():
    fc = score_field("area_unit", "bigha", 0.95, [{"text": "Unit: bigha", "confidence": 0.95}],
                     [_issue("FMT_UNIT_001", "area_unit")])
    assert fc.score is not None and fc.score <= 0.69
    assert fc.band in ("MEDIUM", "LOW")
    assert fc.review_required is True


def test_info_issue_neither_caps_nor_flags():
    fc = score_field("village", "Demo Village", 0.9,
                     [{"text": "Village: Demo Village", "confidence": 0.9}],
                     [_issue("REF_DATA_001", None, "NOT_CHECKED", "INFO", "skipped")])
    assert fc.band == "HIGH"
    assert fc.review_required is False


def test_missing_value_is_unscorable_and_flagged():
    fc = score_field("owner_name", None, None, LINES, [])
    assert fc.score is None
    assert fc.band == "REVIEW_REQUIRED"
    assert fc.review_required is True


def test_band_boundaries():
    assert score_field("f", "x", 0.80, [{"text": "x", "confidence": 0.80}], []).band == "HIGH"
    assert score_field("f", "x", 0.60, [{"text": "x", "confidence": 0.60}], []).band == "MEDIUM"
    assert score_field("f", "x", 0.599, [{"text": "x", "confidence": 0.599}], []).band == "LOW"


def test_ocr_matching_is_documented_heuristic():
    assert match_ocr_confidence("Ramesh Kumar", LINES) == 0.95
    assert match_ocr_confidence("Nobody Here", LINES) is None
    assert match_ocr_confidence(None, LINES) is None
    assert match_ocr_confidence("x", [{"text": "x", "confidence": "bad"}]) is None


def test_record_rollup_propagates_review_and_averages():
    values = {"owner_name": "Ramesh Kumar", "area": "0"}
    confidences = {"owner_name": 0.95, "area": 0.95}
    lines = [{"text": "Owner Name: Ramesh Kumar", "confidence": 0.95}, {"text": "Area: 0", "confidence": 0.95}]
    record = score_record("d", values, confidences, lines, [_issue("FMT_AREA_002", "area", "FAIL", "ERROR")])
    assert record.fields["owner_name"].band == "HIGH"
    assert record.fields["area"].band == "LOW"
    assert record.overall_score == (0.95 + record.fields["area"].score) / 2
    assert record.review_required is True


def test_record_level_issue_forces_review():
    record = score_record("d", {"village": "Demo Village"}, {"village": 0.9},
                          [{"text": "Village: Demo Village", "confidence": 0.9}],
                          [_issue("DUP_CANDIDATE_001", None)])
    assert record.review_required is True
    assert record.reasons
