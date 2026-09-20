"""Document response schemas. Passwords/keys are never part of these."""
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class DocumentUploadResponse(BaseModel):
    document_id: UUID
    status: str


class DocumentOut(BaseModel):
    id: UUID
    file_name: str
    file_type: str
    file_size: int
    checksum: str
    document_type: str | None = None
    language: str | None = None
    storage_path: str
    uploaded_by: UUID | None = None
    uploaded_at: datetime
    processing_status: str
    created_at: datetime
    updated_at: datetime


class DocumentStatusOut(BaseModel):
    document_id: UUID
    status: str
    job_id: UUID | None = None
    job_status: str | None = None
    error_code: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


class ExtractedFieldOut(BaseModel):
    """Stored extraction plus optional source evidence.

    Source fields remain nullable: the backend must not manufacture page or
    coordinate claims when the extraction provider did not supply them.
    """
    field_name: str
    value: str | None = None
    confidence: float | None = None
    source_page: int | None = None
    source_text: str | None = None
    bounding_box: Any | None = None
    extraction_status: str | None = None
    validation_status: str | None = None


class DocumentExtractionOut(BaseModel):
    document_id: UUID
    record_id: UUID
    status: str
    fields: list[ExtractedFieldOut] = []


class DocumentValidationOut(BaseModel):
    document_id: UUID
    record_id: UUID
    status: str
    issues: list[dict] = []
