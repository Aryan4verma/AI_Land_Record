"""Validation rules engine (08 sections 3-6, 9-12).

`validate_record(values, reference=None)` runs every applicable rule and
returns a list of ValidationIssue (only non-passing checks; a clean record
yields []). Every message answers: what failed, which field, why, and what
the reviewer should inspect. Rule IDs are stable for DB/API use.
"""
from .normalize import KNOWN_UNITS, normalize_date, normalize_text, parse_area
from .models import ReferenceData, ValidationIssue

# Required when the khata-style MVP document is expected to contain them
# (04 section 2, Yes*). registration_number etc. stay optional.
REQUIRED_FIELDS = ("owner_name", "survey_number", "area", "village", "tehsil", "district")


def _blank(value: object) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def _key(value: object) -> str:
    return str(value or "").strip().lower()


def validate_record(values: dict, reference: ReferenceData | None = None) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    issues.extend(_required_checks(values))
    issues.extend(_format_checks(values))
    issues.extend(_cross_field_checks(values))
    issues.extend(_reference_checks(values, reference))
    return issues


def _required_checks(values: dict) -> list[ValidationIssue]:
    labels = {
        "owner_name": "Owner name",
        "survey_number": "Survey number",
        "area": "Area",
        "village": "Village",
        "tehsil": "Tehsil",
        "district": "District",
    }
    out = []
    for name in REQUIRED_FIELDS:
        if _blank(values.get(name)):
            out.append(
                ValidationIssue(
                    rule_id=f"REQ_{name.upper()}_001",
                    field_name=name,
                    status="REVIEW_REQUIRED",
                    severity="WARNING",
                    message=(
                        f"{labels[name]} is required but missing. Field: {name}. "
                        f"The document is expected to contain it. "
                        f"Reviewer: check the source document for the {labels[name].lower()}."
                    ),
                )
            )
    if not _blank(values.get("area")) and _blank(values.get("area_unit")):
        out.append(
            ValidationIssue(
                rule_id="REQ_AREA_UNIT_001",
                field_name="area_unit",
                status="REVIEW_REQUIRED",
                severity="WARNING",
                message=(
                    "Area is present but its unit is missing. Field: area_unit. "
                    "An area without a unit cannot be interpreted. "
                    "Reviewer: check the source document for the area unit."
                ),
            )
        )
    return out


def _format_checks(values: dict) -> list[ValidationIssue]:
    out = []
    area = values.get("area")
    if not _blank(area):
        canonical, numeric = parse_area(area)
        if not numeric:
            out.append(
                ValidationIssue(
                    rule_id="FMT_AREA_001",
                    field_name="area",
                    status="FAIL",
                    severity="ERROR",
                    message=(
                        f"Area is not numeric ({str(area).strip()!r}). Field: area. "
                        "Area must be a positive decimal number. "
                        "Reviewer: check whether the extracted value mixed digits with text."
                    ),
                )
            )
        elif float(canonical or 0) <= 0:
            out.append(
                ValidationIssue(
                    rule_id="FMT_AREA_002",
                    field_name="area",
                    status="FAIL",
                    severity="ERROR",
                    message=(
                        f"Area must be positive (got {canonical}). Field: area. "
                        "Zero or negative areas are never valid land areas. "
                        "Reviewer: verify the area figure against the source document."
                    ),
                )
            )
    unit = values.get("area_unit")
    if not _blank(unit) and normalize_text(unit).lower() not in KNOWN_UNITS:
        out.append(
            ValidationIssue(
                rule_id="FMT_UNIT_001",
                field_name="area_unit",
                status="WARNING",
                severity="WARNING",
                message=(
                    f"Area unit {str(unit).strip()!r} is not in the known list "
                    "(hectare, acre, sqm). Field: area_unit. Regional units vary, "
                    "so this is a review prompt, not a rejection. "
                    "Reviewer: confirm the unit as written in the source document."
                ),
            )
        )
    date = values.get("record_date")
    if isinstance(date, str) and not _blank(date):
        # Unparseable dates are kept verbatim by the normalizer: flag them
        # as review prompts instead of rejecting (regional formats vary).
        if normalize_date(date) == date.strip() and not _looks_iso(date.strip()):
            out.append(
                ValidationIssue(
                    rule_id="FMT_DATE_001",
                    field_name="record_date",
                    status="WARNING",
                    severity="WARNING",
                    message=(
                        f"Record date {date.strip()!r} is not in a recognized format. "
                        "Field: record_date. The raw value was preserved unchanged. "
                        "Reviewer: confirm the intended date from the source document."
                    ),
                )
            )
    return out


def _looks_iso(text: str) -> bool:
    import re

    return re.fullmatch(r"\d{4}-\d{2}-\d{2}", text) is not None


def _cross_field_checks(values: dict) -> list[ValidationIssue]:
    # Geographic chain consistency needs reference data; without it the
    # reference layer reports NOT_CHECKED instead of pretending.
    return []


def _reference_checks(values: dict, reference: ReferenceData | None) -> list[ValidationIssue]:
    if reference is None:
        return [
            ValidationIssue(
                rule_id="REF_DATA_001",
                field_name=None,
                status="NOT_CHECKED",
                severity="INFO",
                message=(
                    "No trusted reference data is configured, so village/tehsil/"
                    "district checks were skipped (recorded as NOT_CHECKED, not passed)."
                ),
            )
        ]
    out = []
    village = values.get("village")
    tehsil = values.get("tehsil")
    district = values.get("district")
    if not _blank(village) and _key(village) not in reference.villages:
        out.append(
            ValidationIssue(
                rule_id="REF_VILLAGE_001",
                field_name="village",
                status="REVIEW_REQUIRED",
                severity="WARNING",
                message=(
                    f"Village {str(village).strip()!r} is not in reference "
                    f"{reference.source} version {reference.version}. Field: village. "
                    "Reviewer: check the spelling against the source document and "
                    "the current reference list."
                ),
            )
        )
    if not _blank(tehsil) and _key(tehsil) not in reference.tehsils:
        out.append(
            ValidationIssue(
                rule_id="REF_TEHSIL_001",
                field_name="tehsil",
                status="REVIEW_REQUIRED",
                severity="WARNING",
                message=(
                    f"Tehsil {str(tehsil).strip()!r} is not in reference "
                    f"{reference.source} version {reference.version}. Field: tehsil. "
                    "Reviewer: check the spelling against the source document."
                ),
            )
        )
    if not _blank(district) and _key(district) not in reference.districts:
        out.append(
            ValidationIssue(
                rule_id="REF_DISTRICT_001",
                field_name="district",
                status="REVIEW_REQUIRED",
                severity="WARNING",
                message=(
                    f"District {str(district).strip()!r} is not in reference "
                    f"{reference.source} version {reference.version}. Field: district. "
                    "Reviewer: check the spelling against the source document."
                ),
            )
        )
    if (
        not _blank(village)
        and not _blank(tehsil)
        and _key(village) in reference.villages
        and reference.village_to_tehsil.get(_key(village)) not in (None, _key(tehsil))
    ):
        expected = reference.village_to_tehsil[_key(village)]
        out.append(
            ValidationIssue(
                rule_id="REF_GEO_CHAIN_001",
                field_name="tehsil",
                status="REVIEW_REQUIRED",
                severity="WARNING",
                message=(
                    f"Village {str(village).strip()!r} belongs to tehsil {expected!r} "
                    f"per reference data, but the record says {str(tehsil).strip()!r}. "
                    "Field: tehsil. Reviewer: determine which tehsil the source "
                    "document actually states."
                ),
            )
        )
    if (
        not _blank(tehsil)
        and not _blank(district)
        and _key(tehsil) in reference.tehsils
        and reference.tehsil_to_district.get(_key(tehsil)) not in (None, _key(district))
    ):
        expected = reference.tehsil_to_district[_key(tehsil)]
        out.append(
            ValidationIssue(
                rule_id="REF_GEO_CHAIN_002",
                field_name="district",
                status="REVIEW_REQUIRED",
                severity="WARNING",
                message=(
                    f"Tehsil {str(tehsil).strip()!r} belongs to district {expected!r} "
                    f"per reference data, but the record says {str(district).strip()!r}. "
                    "Field: district. Reviewer: determine which district the source "
                    "document actually states."
                ),
            )
        )
    return out


def record_verdict(issues: list[ValidationIssue]) -> str:
    """READY_FOR_APPROVAL | REVIEW_REQUIRED | BLOCKED (08 sections 10-11)."""
    if any(i.severity in ("ERROR", "CRITICAL") or i.status == "FAIL" for i in issues):
        return "BLOCKED"
    if any(i.severity == "WARNING" or i.status == "REVIEW_REQUIRED" for i in issues):
        return "REVIEW_REQUIRED"
    return "READY_FOR_APPROVAL"


def approval_blocked(issues: list[ValidationIssue]) -> bool:
    """True unless the record is clean enough for automatic approval."""
    return record_verdict(issues) != "READY_FOR_APPROVAL"
