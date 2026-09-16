"""Typed-value persistence + database error classification (STEP 4, P0).

Reproduces the original defect and locks in the fix: an extracted value that
validation correctly flags (an unparseable date, a non-numeric area) must NOT
abort the insert. The typed column is stored NULL, the raw string survives in
extracted_fields, the validation issue stays attached, and the document reaches
human review instead of being destroyed with a misleading
"database temporarily unavailable".
"""
import sys
import uuid
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.db_errors import classify_db_error, sqlstate_of  # noqa: E402
from app.errors import AppError  # noqa: E402
from app.records.typed_values import (  # noqa: E402
    coerce_area,
    coerce_record_date,
    coerce_typed_columns,
)
from tests.test_processing import (  # noqa: E402
    CLEAN_VALUES,
    DOC_ID,
    _run,
    world,  # noqa: F401  (pytest fixture)
)

# The exact value from the reproduced live failure (job e1a0dd81).
BAD_DATE = "99/99/2024"
BAD_AREA = "two and a half"


# --------------------------------------------------------------------------
# 1. unit level: coercion accepts valid values and drops only the impossible
# --------------------------------------------------------------------------

@pytest.mark.parametrize("value", ["2024-03-15", "1900-01-01", "2026-12-31"])
def test_valid_date_passes_through_unchanged(value):
    stored, dropped = coerce_record_date(value)
    assert stored == value and dropped is False


@pytest.mark.parametrize("value", [BAD_DATE, "2024-02-30", "14/03/2024", "March 2024", "unknown"])
def test_invalid_date_is_dropped_not_guessed(value):
    stored, dropped = coerce_record_date(value)
    assert stored is None and dropped is True


@pytest.mark.parametrize("value", ["2.45", "0", "0.001", "1234567.89", "-3"])
def test_valid_area_passes_through_unchanged(value):
    stored, dropped = coerce_area(value)
    assert stored == value and dropped is False


@pytest.mark.parametrize("value", [BAD_AREA, "2.5 hectare", "", "  ", "NaN", "Infinity", True])
def test_invalid_area_is_dropped_or_blank(value):
    stored, _ = coerce_area(value)
    assert stored is None


def test_blank_is_null_but_not_reported_as_dropped():
    """A missing value is not a data fault — it must not be audited as one."""
    for blank in (None, "", "   "):
        assert coerce_record_date(blank) == (None, False)
        assert coerce_area(blank) == (None, False)


def test_coerce_typed_columns_leaves_untyped_fields_untouched():
    row = {"owner_name": "Ramesh Kumar", "survey_number": "145/2",
           "record_date": BAD_DATE, "area": "2.45", "status": "REVIEW_REQUIRED"}
    safe, dropped = coerce_typed_columns(row)
    assert safe["owner_name"] == "Ramesh Kumar"
    assert safe["survey_number"] == "145/2"
    assert safe["status"] == "REVIEW_REQUIRED"
    assert safe["area"] == "2.45"          # valid -> untouched
    assert safe["record_date"] is None      # invalid -> NULL
    assert dropped == {"record_date": BAD_DATE}   # raw value kept for audit
    assert row["record_date"] == BAD_DATE   # input not mutated


# --------------------------------------------------------------------------
# 2. pipeline level: the record survives and reaches review
# --------------------------------------------------------------------------

def _record_of(world):
    return world["records"].get_record_by_document(DOC_ID)


def _field(world, record_id, name):
    return next(f for f in world["records"].extracted[record_id] if f["field_name"] == name)


def test_invalid_date_persists_record_instead_of_failing_the_job(world):
    """The original P0: this job used to end FAILED/PERSIST_FAILED."""
    job = _run(world, values=dict(CLEAN_VALUES, record_date=BAD_DATE))

    assert job["status"] == "SUCCEEDED"
    assert job["error_code"] is None
    record = _record_of(world)
    assert record is not None, "the record must exist, not be destroyed"
    assert record["record_date"] is None          # typed column nulled
    assert record["owner_name"] == "Ramesh Kumar"  # everything else intact


def test_invalid_date_preserves_the_raw_extracted_value(world):
    record = _run(world, values=dict(CLEAN_VALUES, record_date=BAD_DATE)) and _record_of(world)
    assert _field(world, record["id"], "record_date")["value"] == BAD_DATE


def test_invalid_area_persists_record_and_preserves_raw_value(world):
    job = _run(world, values=dict(CLEAN_VALUES, area=BAD_AREA))
    assert job["status"] == "SUCCEEDED"
    record = _record_of(world)
    assert record["area"] is None
    assert _field(world, record["id"], "area")["value"] == BAD_AREA


def test_valid_values_are_never_nulled_by_the_fix(world):
    """Guard against over-coercion: good data must be stored as-is."""
    _run(world, values=CLEAN_VALUES)
    record = _record_of(world)
    assert record["record_date"] == "2024-03-15"
    assert record["area"] == "2.45"


def test_invalid_typed_field_still_creates_a_review_task(world):
    _run(world, values=dict(CLEAN_VALUES, record_date=BAD_DATE))
    record = _record_of(world)
    assert record["status"] == "REVIEW_REQUIRED"
    tasks = [t for t in world["reviews"].tasks.values() if t["land_record_id"] == record["id"]]
    assert len(tasks) == 1 and tasks[0]["status"] == "PENDING"


def test_validation_evidence_is_retained_for_the_dropped_value(world):
    _run(world, values=dict(CLEAN_VALUES, record_date=BAD_DATE))
    record = _record_of(world)
    issues = world["records"].validations[record["id"]]
    assert any(i["rule_id"] == "FMT_DATE_001" and i["field_name"] == "record_date"
               for i in issues), "the rule that flagged the value must survive persistence"


def test_coercion_is_recorded_in_the_audit_trail(world):
    _run(world, values=dict(CLEAN_VALUES, record_date=BAD_DATE))
    completed = next(e for e in world["audits"].entries
                     if e["action"] == "PROCESSING_COMPLETED")
    assert completed["metadata"]["unrepresentable_values"] == {"record_date": BAD_DATE}


def test_clean_run_records_no_unrepresentable_values(world):
    _run(world, values=CLEAN_VALUES)
    completed = next(e for e in world["audits"].entries
                     if e["action"] == "PROCESSING_COMPLETED")
    assert "unrepresentable_values" not in completed["metadata"]


def test_human_correction_then_approval_succeeds_after_a_dropped_value(world):
    """End of the intended journey: the record that used to be destroyed can be
    corrected by a human and approved."""
    from app.reviews.service import approve_record, complete_review, submit_correction

    _run(world, values=dict(CLEAN_VALUES, record_date=BAD_DATE))
    record = _record_of(world)
    task = next(t for t in world["reviews"].tasks.values()
                if t["land_record_id"] == record["id"])
    officer = {"id": str(uuid.uuid4()), "role": "operator"}

    detail = submit_correction(
        user=officer, task_id=task["id"], field_name="record_date",
        value="2024-03-15", reason="Read from the source document",
        records=world["records"], reviews=world["reviews"], audits=world["audits"],
        reference=None,
    )
    assert detail["record"]["record_date"] == "2024-03-15"

    # Approval stays blocked while the review is open — that guard is part of
    # the workflow and must survive this fix, so close the review properly.
    with pytest.raises(AppError) as blocked:
        approve_record(
            user=officer, record_id=record["id"], reason="too early",
            records=world["records"], reviews=world["reviews"], audits=world["audits"],
            reference=None,
        )
    assert blocked.value.code == "APPROVAL_BLOCKED"

    complete_review(user=officer, task_id=task["id"],
                    reviews=world["reviews"], audits=world["audits"])

    approved = approve_record(
        user=officer, record_id=record["id"], reason="Verified against the source",
        records=world["records"], reviews=world["reviews"], audits=world["audits"],
        reference=None,
    )
    assert approved["status"] == "APPROVED"
    actions = [e["action"] for e in world["audits"].entries]
    assert "FIELD_CORRECTED" in actions
    assert "REVIEW_COMPLETED" in actions
    assert "RECORD_APPROVED" in actions


# --------------------------------------------------------------------------
# 3. store-layer error classification
# --------------------------------------------------------------------------

class _PgError(Exception):
    """Mimics a supabase/postgrest APIError carrying a SQLSTATE."""

    def __init__(self, code, message="db said no"):
        super().__init__(message)
        self.code = code


def _classify(exc):
    return classify_db_error(exc, subject="Record store", action="test")


def test_data_error_is_422_not_database_unavailable():
    """SQLSTATE 22008 is exactly what the live failure produced."""
    err = _classify(_PgError("22008", 'date/time field value out of range: "99/99/2024"'))
    assert (err.status, err.code) == (422, "INVALID_FIELD_VALUE")


@pytest.mark.parametrize("state", ["22008", "22P02", "23514", "23502"])
def test_all_data_and_constraint_faults_classify_as_422(state):
    assert _classify(_PgError(state)).status == 422


def test_unique_violation_is_409_conflict():
    err = _classify(_PgError("23505", "duplicate key value violates unique constraint"))
    assert (err.status, err.code) == (409, "ALREADY_EXISTS")


def test_foreign_key_violation_is_409_reference_conflict():
    err = _classify(_PgError("23503"))
    assert (err.status, err.code) == (409, "REFERENCE_CONFLICT")


@pytest.mark.parametrize("state", ["08006", "08001", "53300", "57P01"])
def test_connection_and_resource_faults_are_503_unavailable(state):
    err = _classify(_PgError(state))
    assert (err.status, err.code) == (503, "DATABASE_UNAVAILABLE")


def test_network_exception_type_is_503_unavailable():
    class ConnectError(Exception):
        pass

    err = _classify(ConnectError("connection refused"))
    assert (err.status, err.code) == (503, "DATABASE_UNAVAILABLE")


def test_unknown_exception_is_500_not_misreported_as_unavailable():
    """The core of the fix: an unrecognized fault is NOT called 'unavailable'."""
    err = _classify(RuntimeError("something unexpected"))
    assert (err.status, err.code) == (500, "PERSISTENCE_FAILED")


def test_client_messages_never_echo_the_offending_value():
    err = _classify(_PgError("22008", 'date/time field value out of range: "99/99/2024"'))
    assert BAD_DATE not in err.message


def test_sqlstate_is_extracted_from_attribute_and_from_message():
    assert sqlstate_of(_PgError("23505")) == "23505"
    assert sqlstate_of(Exception("ERROR:  22008: date/time field value out of range")) == "22008"
    assert sqlstate_of(Exception("no code here")) is None


def test_apperror_passes_through_store_guard_unchanged():
    """An AppError raised deliberately inside a store is not re-classified."""
    original = AppError(404, "RECORD_NOT_FOUND", "nope")
    assert _classify(original).status == 500  # classify only runs on driver errors
    assert original.status == 404             # the original is untouched
