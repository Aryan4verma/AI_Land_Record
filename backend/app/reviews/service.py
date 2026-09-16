"""Human-review workflow (03 sections 7-9, 10 sections 6-7, 08 section 11).

Reviewers inspect extracted values, correct fields with a mandatory
reason, see validation re-run, and approve/reject. Approval is blocked
while required fields are unresolved, blocking validation failures exist,
or mandatory reviews are incomplete. Every meaningful action appends an
audit entry; source tables (documents/OCR) are never modified here.
"""
import sys
from datetime import datetime, timezone
from pathlib import Path


def _ensure_repo_root() -> None:
    # Monorepo layout: backend/ runs with backend/ on sys.path, while the
    # deterministic ai/* packages live at the repo root.
    root = Path(__file__).resolve().parents[3]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))


_ensure_repo_root()

from ai.validation import (  # noqa: E402
    ReferenceData,
    ValidationIssue,
    approval_blocked,
    normalize_record,
    record_verdict,
    validate_record,
)

from ..errors import AppError
from .stores import AuditStore, RecordStore, ReviewStore

# land_records columns a reviewer may correct (04 data dictionary fields).
RECORD_COLUMNS = (
    "owner_name",
    "father_or_spouse_name",
    "survey_number",
    "khasra_number",
    "khata_number",
    "area",
    "area_unit",
    "village",
    "tehsil",
    "district",
    "land_classification",
    "mutation_number",
    "registration_number",
    "record_date",
)

REQUIRED_COLUMNS = ("owner_name", "survey_number", "area", "village", "tehsil", "district")

OPEN_TASK_STATUSES = ("PENDING", "IN_REVIEW")
TERMINAL_RECORD_STATUSES = ("APPROVED", "REJECTED")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def review_needed(validation_verdict: str, low_confidence_fields: list[str] | None = None) -> bool:
    """A record needs human review unless validation is fully clean."""
    return validation_verdict != "READY_FOR_APPROVAL" or bool(low_confidence_fields)


def build_reference(rows: list[dict]) -> ReferenceData:
    """Build validation reference data from reference_data table rows."""
    by_id = {row.get("id"): row for row in rows}

    def active_names(reference_type: str) -> set[str]:
        return {
            str(row["name"]).strip().lower()
            for row in rows
            if row.get("reference_type") == reference_type
            and row.get("status", "active") == "active"
            and str(row.get("name", "")).strip()
        }

    village_to_tehsil: dict[str, str] = {}
    tehsil_to_district: dict[str, str] = {}
    for row in rows:
        if row.get("status", "active") != "active":
            continue
        name = str(row.get("name", "")).strip().lower()
        parent = by_id.get(row.get("parent_id"))
        if row.get("reference_type") == "village" and parent and parent.get("reference_type") == "tehsil":
            village_to_tehsil[name] = str(parent.get("name", "")).strip().lower()
        if row.get("reference_type") == "tehsil" and parent and parent.get("reference_type") == "district":
            tehsil_to_district[name] = str(parent.get("name", "")).strip().lower()
    version = next((str(row["version"]) for row in rows if row.get("version")), "unknown")
    return ReferenceData(
        version=version,
        source="supabase:reference_data",
        villages=active_names("village"),
        tehsils=active_names("tehsil"),
        districts=active_names("district"),
        village_to_tehsil=village_to_tehsil,
        tehsil_to_district=tehsil_to_district,
    )


def current_validation(record: dict, reference: ReferenceData) -> tuple[dict, list[ValidationIssue]]:
    """Normalize current record values and run the deterministic rules."""
    values = {name: record.get(name) for name in RECORD_COLUMNS}
    normalized = normalize_record(values)["normalized"]
    return normalized, validate_record(normalized, reference)


def _audit(
    audits: AuditStore,
    *,
    user_id: str,
    action: str,
    record_id: str,
    old_value: object = None,
    new_value: object = None,
    metadata: dict | None = None,
) -> dict:
    return audits.append(
        {
            "user_id": user_id,
            "entity_type": "land_record",
            "entity_id": record_id,
            "action": action,
            "old_value": old_value,
            "new_value": new_value,
            "metadata": metadata or {},
        }
    )


def create_review(
    *,
    user: dict,
    record_id: str,
    reason: str,
    priority: str,
    records: RecordStore,
    reviews: ReviewStore,
    audits: AuditStore,
) -> dict:
    record = records.get_record(record_id)
    if record is None:
        raise AppError(404, "RECORD_NOT_FOUND", "The requested record was not found.")
    if record.get("status") in TERMINAL_RECORD_STATUSES:
        raise AppError(409, "RECORD_FINALIZED", "Approved or rejected records cannot be sent back to review.")
    if reviews.open_tasks_for_record(record_id):
        raise AppError(409, "REVIEW_ALREADY_OPEN", "This record already has an open review task.")
    task = reviews.create_task(
        {"land_record_id": record_id, "status": "PENDING", "priority": priority, "reason": reason.strip()}
    )
    _audit(
        audits, user_id=user["id"], action="REVIEW_CREATED", record_id=record_id,
        metadata={"review_id": task["id"], "priority": priority, "reason": reason.strip()},
    )
    return task


def get_review_detail(
    *, task_id: str, records: RecordStore, reviews: ReviewStore, reference: ReferenceData
) -> dict:
    task = reviews.get_task(task_id)
    if task is None:
        raise AppError(404, "REVIEW_NOT_FOUND", "The requested review was not found.")
    record = records.get_record(str(task["land_record_id"]))
    if record is None:
        raise AppError(404, "RECORD_NOT_FOUND", "The reviewed record no longer exists.")
    normalized, issues = current_validation(record, reference)
    document = records.get_document(str(record["document_id"])) if record.get("document_id") else None
    return {
        "task": task,
        "record": record,
        "normalized_values": normalized,
        "extracted_fields": records.list_extracted_fields(str(record["id"])),
        "validation": [issue.to_dict() for issue in issues],
        "verdict": record_verdict(issues),
        "approval_blocked": approval_blocked(issues),
        "document": document,
    }


def submit_correction(
    *,
    user: dict,
    task_id: str,
    field_name: str,
    value: str | None,
    reason: str,
    records: RecordStore,
    reviews: ReviewStore,
    audits: AuditStore,
    reference: ReferenceData,
) -> dict:
    if field_name not in RECORD_COLUMNS:
        raise AppError(404, "FIELD_NOT_FOUND", f"Field '{field_name}' cannot be corrected.")
    if not (reason or "").strip():
        raise AppError(422, "CORRECTION_REASON_REQUIRED", "A reason is required for every correction.")
    task = reviews.get_task(task_id)
    if task is None:
        raise AppError(404, "REVIEW_NOT_FOUND", "The requested review was not found.")
    if task.get("status") not in OPEN_TASK_STATUSES:
        raise AppError(409, "REVIEW_CLOSED", "Corrections are only allowed on open reviews.")
    record = records.get_record(str(task["land_record_id"]))
    if record is None:
        raise AppError(404, "RECORD_NOT_FOUND", "The reviewed record no longer exists.")
    if record.get("status") in TERMINAL_RECORD_STATUSES:
        raise AppError(409, "RECORD_FINALIZED", "Approved or rejected records cannot be corrected.")

    old_value = record.get(field_name)
    updated = records.update_record(str(record["id"]), {field_name: value})
    records.save_correction(
        {
            "land_record_id": str(record["id"]),
            "field_name": field_name,
            "old_value": old_value,
            "new_value": value,
            "reason": reason.strip(),
            "changed_by": user["id"],
        }
    )
    if task.get("status") == "PENDING":
        reviews.update_task(task_id, {"status": "IN_REVIEW"})
    normalized, issues = current_validation(updated, reference)
    records.replace_validation_results(
        str(record["id"]),
        [
            {
                "land_record_id": str(record["id"]),
                "rule_id": issue.rule_id,
                "field_name": issue.field_name,
                "status": issue.status,
                "severity": issue.severity,
                "message": issue.message,
            }
            for issue in issues
        ],
    )
    _audit(
        audits, user_id=user["id"], action="FIELD_CORRECTED", record_id=str(record["id"]),
        old_value={field_name: old_value}, new_value={field_name: value},
        metadata={"review_id": task_id, "field": field_name, "reason": reason.strip()},
    )
    return get_review_detail(task_id=task_id, records=records, reviews=reviews, reference=reference)


def complete_review(*, user: dict, task_id: str, reviews: ReviewStore, audits: AuditStore) -> dict:
    task = reviews.get_task(task_id)
    if task is None:
        raise AppError(404, "REVIEW_NOT_FOUND", "The requested review was not found.")
    if task.get("status") not in OPEN_TASK_STATUSES:
        raise AppError(409, "REVIEW_CLOSED", "Only open reviews can be completed.")
    completed = reviews.update_task(task_id, {"status": "COMPLETED", "completed_at": _now()})
    _audit(
        audits, user_id=user["id"], action="REVIEW_COMPLETED", record_id=str(task["land_record_id"]),
        metadata={"review_id": task_id},
    )
    return completed


def _approval_blockers(record: dict, issues: list[ValidationIssue], open_tasks: list[dict]) -> list[str]:
    blockers = []
    failing = sorted({issue.rule_id for issue in issues if issue.status == "FAIL" or issue.severity in ("ERROR", "CRITICAL")})
    blockers.extend(f"blocking validation failure: {rule}" for rule in failing)
    missing = [name for name in REQUIRED_COLUMNS if record.get(name) is None or (isinstance(record.get(name), str) and not record.get(name).strip())]
    blockers.extend(f"required field unresolved: {name}" for name in missing)
    if open_tasks:
        blockers.append(f"mandatory review incomplete: {len(open_tasks)} open review task(s)")
    return blockers


def approve_record(
    *,
    user: dict,
    record_id: str,
    reason: str | None,
    records: RecordStore,
    reviews: ReviewStore,
    audits: AuditStore,
    reference: ReferenceData,
) -> dict:
    record = records.get_record(record_id)
    if record is None:
        raise AppError(404, "RECORD_NOT_FOUND", "The requested record was not found.")
    if record.get("status") in TERMINAL_RECORD_STATUSES:
        raise AppError(409, "RECORD_FINALIZED", f"Record is already {record.get('status')}.")
    _, issues = current_validation(record, reference)
    open_tasks = reviews.open_tasks_for_record(record_id)
    blockers = _approval_blockers(record, issues, open_tasks)
    if blockers:
        raise AppError(409, "APPROVAL_BLOCKED", "Approval blocked: " + "; ".join(blockers))
    previous_status = record.get("status")
    approved = records.update_record(
        record_id, {"status": "APPROVED", "approved_by": user["id"], "approved_at": _now()}
    )
    _audit(
        audits, user_id=user["id"], action="RECORD_APPROVED", record_id=record_id,
        old_value={"status": previous_status}, new_value={"status": "APPROVED"},
        metadata={"reason": (reason or "").strip() or None},
    )
    return approved


def reject_record(
    *,
    user: dict,
    record_id: str,
    reason: str,
    records: RecordStore,
    reviews: ReviewStore,
    audits: AuditStore,
) -> dict:
    if not (reason or "").strip():
        raise AppError(422, "REJECTION_REASON_REQUIRED", "A reason is required to reject a record.")
    record = records.get_record(record_id)
    if record is None:
        raise AppError(404, "RECORD_NOT_FOUND", "The requested record was not found.")
    if record.get("status") in TERMINAL_RECORD_STATUSES:
        raise AppError(409, "RECORD_FINALIZED", f"Record is already {record.get('status')}.")
    open_tasks = reviews.open_tasks_for_record(record_id)
    previous_status = record.get("status")
    rejected = records.update_record(record_id, {"status": "REJECTED"})
    cancelled = []
    for task in open_tasks:
        reviews.update_task(str(task["id"]), {"status": "CANCELLED", "completed_at": _now()})
        cancelled.append(str(task["id"]))
    _audit(
        audits, user_id=user["id"], action="RECORD_REJECTED", record_id=record_id,
        old_value={"status": previous_status}, new_value={"status": "REJECTED"},
        metadata={"reason": reason.strip(), "cancelled_reviews": cancelled},
    )
    return rejected
