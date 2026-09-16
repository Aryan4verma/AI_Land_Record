"""Records/search/dashboard/export schemas (10 sections 8, 10, 11)."""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class RecordSearchOut(BaseModel):
    items: list[dict]
    page: int
    limit: int
    total: int


class RecordDetailOut(BaseModel):
    record: dict
    extracted_fields: list[dict] = []
    validation: list[dict] = []
    document: dict | None = None


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


class RecordExportOut(BaseModel):
    record: dict
    extracted_fields: list[dict] = []
    validation: list[dict] = []
    document: dict | None = None
    exported_at: datetime
    format_version: str = "v1"


class MockLrmsIn(BaseModel):
    record_id: UUID


class MockLrmsOut(BaseModel):
    integration: str = "mock-lrms"
    status: str = "accepted"
    record_id: UUID
    received_at: datetime
    disclaimer: str = Field(
        default="Demonstration endpoint — not a live government integration."
    )


class DashboardSummaryOut(BaseModel):
    documents_total: int
    documents_by_status: dict[str, int] = {}
    records_by_status: dict[str, int] = {}
    open_reviews: int
    average_confidence: float | None = None


class DashboardProcessingOut(BaseModel):
    jobs_by_status: dict[str, int] = {}
    recent_jobs: list[dict] = []


class DashboardValidationOut(BaseModel):
    issues_by_severity: dict[str, int] = {}
    issues_by_status: dict[str, int] = {}
    blocked_documents: int
