"""Records search/detail/export + dashboard + mock integration logic."""
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _ensure_repo_root() -> None:
    root = Path(__file__).resolve().parents[3]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))


_ensure_repo_root()

from ai.validation.models import ValidationIssue  # noqa: E402
from ai.validation.rules import record_verdict  # noqa: E402

from ..errors import AppError

ALLOWED_STATUSES = ("DRAFT", "PROCESSING", "REVIEW_REQUIRED", "READY_FOR_APPROVAL", "APPROVED", "REJECTED")


def collect_filters(owner: str | None, survey_number: str | None, khasra_number: str | None,
                    village: str | None, tehsil: str | None, district: str | None,
                    status: str | None) -> dict[str, str]:
    filters = {"owner": owner, "survey_number": survey_number, "khasra_number": khasra_number,
               "village": village, "tehsil": tehsil, "district": district, "status": status}
    return {key: value.strip() for key, value in filters.items() if value and value.strip()}


def stored_validation_verdict(rows: list[dict]) -> str:
    issues = [ValidationIssue(rule_id=row.get("rule_id", ""), field_name=row.get("field_name"),
                              status=row.get("status", "NOT_CHECKED"),
                              severity=row.get("severity", "INFO"),
                              message=row.get("message", "")) for row in rows]
    return record_verdict(issues)


def record_detail(record_id: str, records: Any) -> dict:
    record = records.get_record(record_id)
    if record is None:
        raise AppError(404, "RECORD_NOT_FOUND", "The requested record was not found.")
    validation = records.list_validation_results(record_id)
    document = records.get_document(str(record["document_id"])) if record.get("document_id") else None
    return {"record": record, "extracted_fields": records.list_extracted_fields(record_id),
            "validation": validation, "document": document}


def export_record(record_id: str, records: Any) -> dict:
    detail = record_detail(record_id, records)
    detail["exported_at"] = datetime.now(timezone.utc).isoformat()
    detail["format_version"] = "v1"
    return detail


def mock_lrms_submit(record_id: str, records: Any) -> dict:
    """Demonstration-only receiver. Accepts APPROVED records; never claims
    to be a live government integration (10 section 11)."""
    record = records.get_record(record_id)
    if record is None:
        raise AppError(404, "RECORD_NOT_FOUND", "The requested record was not found.")
    if record.get("status") != "APPROVED":
        raise AppError(409, "MOCK_LRMS_NOT_APPROVED",
                       f"Mock LRMS only accepts APPROVED records (current status: {record.get('status')}).")
    return {"integration": "mock-lrms", "status": "accepted", "record_id": record["id"],
            "received_at": datetime.now(timezone.utc).isoformat(),
            "disclaimer": "Demonstration endpoint — not a live government integration."}
