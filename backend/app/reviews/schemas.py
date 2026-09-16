"""Review/approval/audit schemas. Passwords and keys never appear here."""
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

Priority = Literal["LOW", "MEDIUM", "HIGH", "URGENT"]
ReviewStatusFilter = Literal["PENDING", "IN_REVIEW", "COMPLETED", "CANCELLED"]


class ReviewCreate(BaseModel):
    land_record_id: UUID
    reason: str = Field(min_length=1, max_length=500)
    priority: Priority = "MEDIUM"


class ReviewOut(BaseModel):
    id: UUID
    land_record_id: UUID
    assigned_to: UUID | None = None
    status: str
    priority: str
    reason: str | None = None
    created_at: datetime
    completed_at: datetime | None = None


class CorrectionIn(BaseModel):
    value: str | None = Field(default=None, max_length=2000)
    reason: str = Field(min_length=1, max_length=500)


class ApprovalIn(BaseModel):
    reason: str | None = Field(default=None, max_length=500)


class RejectionIn(BaseModel):
    reason: str = Field(min_length=1, max_length=500)


class ReviewDetailOut(BaseModel):
    task: ReviewOut
    record: dict
    extracted_fields: list[dict] = []
    validation: list[dict] = []
    verdict: str
    approval_blocked: bool
    document: dict | None = None


class AuditOut(BaseModel):
    id: UUID
    user_id: UUID | None = None
    action: str
    entity_type: str
    entity_id: UUID | None = None
    old_value: object | None = None
    new_value: object | None = None
    metadata: dict = {}
    timestamp: datetime
