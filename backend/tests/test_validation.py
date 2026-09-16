"""Validation layer checks: normalization, rules, duplicates, verdicts.

Pure functions only — no DB, no LLM, no network.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ai.validation import (  # noqa: E402
    ReferenceData,
    approval_blocked,
    demo_reference,
    duplicate_issue,
    find_duplicates,
    normalize_record,
    record_verdict,
    validate_record,
)
from ai.validation.normalize import KNOWN_UNITS, normalize_date, normalize_unit, parse_area  # noqa: E402

VALID = {
    "owner_name": "Ramesh Kumar",
    "father_or_spouse_name": "Suresh Kumar",
    "survey_number": "145/2",
    "khasra_number": "78",
    "khata_number": "123",
    "area": "2.45",
    "area_unit": "hectare",
    "village": "Demo Village",
    "tehsil": "Demo Tehsil",
    "district": "Demo District",
    "land_classification": "Agricultural",
    "mutation_number": "M-2024-0091",
    "registration_number": None,
    "record_date": "2024-03-15",
}


def _by_rule(issues, rule_id):
    return [i for i in issues if i.rule_id == rule_id]


def test_valid_record_is_clean():
    issues = validate_record(VALID, demo_reference())
    assert issues == []
    assert record_verdict(issues) == "READY_FOR_APPROVAL"
    assert approval_blocked(issues) is False


def test_missing_required_fields_route_to_review():
    for field in ("owner_name", "survey_number", "area", "village", "tehsil", "district"):
        values = dict(VALID, **{field: None})
        issues = validate_record(values, demo_reference())
        assert record_verdict(issues) == "REVIEW_REQUIRED"
        assert approval_blocked(issues) is True
        hit = _by_rule(issues, f"REQ_{field.upper()}_001")
        assert len(hit) == 1
        assert hit[0].status == "REVIEW_REQUIRED" and hit[0].severity == "WARNING"
        assert field in hit[0].message  # explainability: names the field


def test_area_without_unit_needs_review():
    issues = validate_record(dict(VALID, area_unit=None), demo_reference())
    assert _by_rule(issues, "REQ_AREA_UNIT_001")
    assert approval_blocked(issues) is True


def test_invalid_area_values_fail():
    for bad in ("abc", "0", "-3", "0.00"):
        issues = validate_record(dict(VALID, area=bad), demo_reference())
        assert record_verdict(issues) == "BLOCKED"
        assert approval_blocked(issues) is True
        rule = "FMT_AREA_001" if bad == "abc" else "FMT_AREA_002"
        assert _by_rule(issues, rule)


def test_unknown_unit_warns_but_does_not_fail():
    issues = validate_record(dict(VALID, area_unit="bigha"), demo_reference())
    hit = _by_rule(issues, "FMT_UNIT_001")
    assert len(hit) == 1 and hit[0].status == "WARNING"
    assert record_verdict(issues) == "REVIEW_REQUIRED"  # review prompt, not BLOCKED


def test_unparseable_date_warns_and_keeps_raw():
    issues = validate_record(dict(VALID, record_date="sometime last year"), demo_reference())
    assert _by_rule(issues, "FMT_DATE_001")
    assert record_verdict(issues) == "REVIEW_REQUIRED"


def test_unknown_village_and_chain_mismatch():
    issues = validate_record(dict(VALID, village="Nowhere"), demo_reference())
    assert _by_rule(issues, "REF_VILLAGE_001")
    assert approval_blocked(issues) is True

    ref = ReferenceData(
        version="v1",
        source="test",
        villages={"demo village"},
        tehsils={"demo tehsil", "other tehsil"},
        districts={"demo district"},
        village_to_tehsil={"demo village": "other tehsil"},
        tehsil_to_district={},
    )
    issues = validate_record(VALID, ref)
    hit = _by_rule(issues, "REF_GEO_CHAIN_001")
    assert len(hit) == 1 and "other tehsil" in hit[0].message


def test_no_reference_means_not_checked_not_passed():
    issues = validate_record(VALID, None)
    assert len(issues) == 1
    assert issues[0].status == "NOT_CHECKED" and issues[0].severity == "INFO"
    assert record_verdict(issues) == "READY_FOR_APPROVAL"  # nothing blocking, nothing claimed


def test_duplicates_match_without_fraud_language():
    existing = [
        {"id": "a", "survey_number": "145/2", "village": "Demo Village", "owner_name": "Ramesh Kumar"},
        {"id": "b", "survey_number": "99", "village": "Demo Village", "owner_name": "Other"},
    ]
    verdict, matches = find_duplicates(
        {"survey_number": " 145/2 ", "village": "demo village", "owner_name": "Ramesh Kumar"}, existing
    )
    assert verdict == "POSSIBLE_DUPLICATE"
    assert [m["id"] for m in matches] == ["a"]
    issue = duplicate_issue(VALID, matches)
    assert issue.status == "REVIEW_REQUIRED" and issue.severity == "WARNING"
    lowered = issue.message.lower()
    assert "not a fraud finding" in lowered  # fraud explicitly disclaimed, never alleged
    assert "is fraud" not in lowered and "fraudulent" not in lowered
    assert "CONFIRMED" not in issue.message


def test_duplicates_no_match_without_keys():
    assert find_duplicates({"survey_number": "1", "village": "V"}, []) == ("NO_MATCH", [])
    assert find_duplicates({"survey_number": None, "village": "V"}, []) == ("NO_MATCH", [])


def test_normalization_is_non_mutating_and_auditable():
    raw = {"owner_name": "  Ramesh   Kumar ", "area": "2,450 ", "area_unit": "Hectares",
           "record_date": "15-03-2024", "village": "Demo Village"}
    snapshot = dict(raw)
    result = normalize_record(raw)
    assert raw == snapshot  # input untouched
    assert result["normalized"]["owner_name"] == "Ramesh Kumar"
    assert result["normalized"]["area"] == "2450"
    assert result["normalized"]["area_unit"] == "hectare"
    assert result["normalized"]["record_date"] == "2024-03-15"
    assert result["normalized"]["village"] == "Demo Village"
    assert result["originals"]["owner_name"] == "  Ramesh   Kumar "
    assert "village" not in result["originals"]  # unchanged fields need no audit copy


def test_normalize_helpers():
    assert parse_area("2.45") == ("2.45", True)
    assert parse_area("2,45,000") == ("245000", True)
    assert parse_area("abc")[1] is False
    assert parse_area(None) == (None, False)
    assert normalize_unit("HA") == "hectare"
    assert normalize_unit("bigha") == "bigha"  # unknown kept verbatim
    assert normalize_date("2024-03-15") == "2024-03-15"
    assert normalize_date("15/03/2024") == "2024-03-15"
    assert normalize_date("sometime") == "sometime"
    assert KNOWN_UNITS == {"hectare", "acre", "sqm"}
