"""Review workflow endpoints (10 sections 6-7, 9).

All review/approval work requires the operator role; `user` is read-only.
No polished UI here — API-level workflow for the QA frontend and tests.
"""
from uuid import UUID

from fastapi import APIRouter, Depends, Request

from ..auth.dependencies import get_current_user, require_role
from ..errors import AppError
from .schemas import (
    ApprovalIn,
    AuditOut,
    CorrectionIn,
    RejectionIn,
    ReviewCreate,
    ReviewDetailOut,
    ReviewOut,
    ReviewStatusFilter,
)
from .service import (
    approve_record,
    build_reference,
    complete_review,
    create_review,
    get_review_detail,
    reject_record,
    submit_correction,
)
from .stores import (
    AuditStore,
    RecordStore,
    ReviewStore,
    get_audit_store,
    get_record_store,
    get_review_store,
)

router = APIRouter(tags=["reviews"])


def _reference(request: Request, records: RecordStore):
    _ = request  # request_id flows through middleware/logging context
    return build_reference(records.list_reference_rows())


@router.post("/api/v1/reviews", status_code=201, response_model=ReviewOut)
def create_review_endpoint(
    body: ReviewCreate,
    request: Request,
    user: dict = Depends(require_role("operator")),
    records: RecordStore = Depends(get_record_store),
    reviews: ReviewStore = Depends(get_review_store),
    audits: AuditStore = Depends(get_audit_store),
) -> dict:
    return create_review(
        user=user, record_id=str(body.land_record_id), reason=body.reason,
        priority=body.priority, records=records, reviews=reviews, audits=audits,
    )


@router.get("/api/v1/reviews", response_model=list[ReviewOut])
def list_reviews(
    request: Request,
    status: ReviewStatusFilter | None = None,
    assigned_to: UUID | None = None,
    user: dict = Depends(require_role("operator")),
    reviews: ReviewStore = Depends(get_review_store),
) -> list:
    _ = (request, user)
    return reviews.list_tasks(status, str(assigned_to) if assigned_to else None)


@router.get("/api/v1/reviews/{review_id}", response_model=ReviewDetailOut)
def get_review(
    review_id: UUID,
    request: Request,
    user: dict = Depends(require_role("operator")),
    records: RecordStore = Depends(get_record_store),
    reviews: ReviewStore = Depends(get_review_store),
) -> dict:
    _ = user
    detail = get_review_detail(
        task_id=str(review_id), records=records, reviews=reviews,
        reference=_reference(request, records),
    )
    return {
        "task": detail["task"],
        "record": detail["record"],
        "extracted_fields": detail["extracted_fields"],
        "validation": detail["validation"],
        "verdict": detail["verdict"],
        "approval_blocked": detail["approval_blocked"],
        "document": detail["document"],
    }


@router.patch("/api/v1/reviews/{review_id}/fields/{field_name}", response_model=ReviewDetailOut)
def correct_field(
    review_id: UUID,
    field_name: str,
    body: CorrectionIn,
    request: Request,
    user: dict = Depends(require_role("operator")),
    records: RecordStore = Depends(get_record_store),
    reviews: ReviewStore = Depends(get_review_store),
    audits: AuditStore = Depends(get_audit_store),
) -> dict:
    detail = submit_correction(
        user=user, task_id=str(review_id), field_name=field_name, value=body.value,
        reason=body.reason, records=records, reviews=reviews, audits=audits,
        reference=_reference(request, records),
    )
    return {
        "task": detail["task"],
        "record": detail["record"],
        "extracted_fields": detail["extracted_fields"],
        "validation": detail["validation"],
        "verdict": detail["verdict"],
        "approval_blocked": detail["approval_blocked"],
        "document": detail["document"],
    }


@router.post("/api/v1/reviews/{review_id}/complete", response_model=ReviewOut)
def complete_review_endpoint(
    review_id: UUID,
    request: Request,
    user: dict = Depends(require_role("operator")),
    reviews: ReviewStore = Depends(get_review_store),
    audits: AuditStore = Depends(get_audit_store),
) -> dict:
    _ = request
    return complete_review(user=user, task_id=str(review_id), reviews=reviews, audits=audits)


@router.post("/api/v1/records/{record_id}/approve")
def approve_record_endpoint(
    record_id: UUID,
    body: ApprovalIn,
    request: Request,
    user: dict = Depends(require_role("operator")),
    records: RecordStore = Depends(get_record_store),
    reviews: ReviewStore = Depends(get_review_store),
    audits: AuditStore = Depends(get_audit_store),
) -> dict:
    approved = approve_record(
        user=user, record_id=str(record_id), reason=body.reason,
        records=records, reviews=reviews, audits=audits,
        reference=_reference(request, records),
    )
    return {"record_id": approved["id"], "status": approved["status"]}


@router.post("/api/v1/records/{record_id}/reject")
def reject_record_endpoint(
    record_id: UUID,
    body: RejectionIn,
    request: Request,
    user: dict = Depends(require_role("operator")),
    records: RecordStore = Depends(get_record_store),
    reviews: ReviewStore = Depends(get_review_store),
    audits: AuditStore = Depends(get_audit_store),
) -> dict:
    _ = request
    rejected = reject_record(
        user=user, record_id=str(record_id), reason=body.reason,
        records=records, reviews=reviews, audits=audits,
    )
    return {"record_id": rejected["id"], "status": rejected["status"]}


@router.get("/api/v1/records/{record_id}/audit", response_model=list[AuditOut])
def record_audit(
    record_id: UUID,
    request: Request,
    user: dict = Depends(require_role("operator")),
    records: RecordStore = Depends(get_record_store),
    audits: AuditStore = Depends(get_audit_store),
) -> list:
    _ = request
    if records.get_record(str(record_id)) is None:
        raise AppError(404, "RECORD_NOT_FOUND", "The requested record was not found.")
    _ = user
    return audits.list_for("land_record", str(record_id))
