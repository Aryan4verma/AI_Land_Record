"""Document response schemas. Passwords/keys are never part of these."""
from datetime import datetime
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


class DocumentExtractionOut(BaseModel):
    document_id: UUID
    record_id: UUID
    status: str
    fields: list[dict] = []


class DocumentValidationOut(BaseModel):
    document_id: UUID
    record_id: UUID
    status: str
    issues: list[dict] = []
