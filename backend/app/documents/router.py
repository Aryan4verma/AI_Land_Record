"""Document endpoints per 10_API_SPECIFICATION section 3 (upload,
metadata, status, processing, extraction, validation).
Versioned under /api/v1.
"""
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile

from ..auth.dependencies import get_current_user, require_role
from ..config import get_settings
from ..errors import AppError
from ..reviews.stores import RecordStore, get_record_store
from .schemas import (
    DocumentExtractionOut,
    DocumentOut,
    DocumentStatusOut,
    DocumentUploadResponse,
    DocumentValidationOut,
)
from .service import upload_document
from .storage_backend import StorageBackend, get_storage_backend
from .store import DocumentStore, get_document_store

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])


@router.post("", status_code=201, response_model=DocumentUploadResponse)
async def upload_document_endpoint(
    request: Request,
    file: UploadFile = File(...),
    document_type: str | None = Form(None, max_length=64),
    language: str | None = Form(None, max_length=32),
    user: dict = Depends(require_role("operator")),
    store: DocumentStore = Depends(get_document_store),
    storage: StorageBackend = Depends(get_storage_backend),
) -> dict:
    _ = request  # request_id is handled by middleware/logging context
    return await upload_document(
        file=file,
        document_type=document_type,
        language=language,
        user_id=user["id"],
        max_bytes=get_settings().max_upload_bytes,
        store=store,
        storage=storage,
    )


def _load_or_404(document_id: UUID, store: DocumentStore) -> dict:
    row = store.get(str(document_id))
    if row is None:
        raise AppError(404, "DOCUMENT_NOT_FOUND", "The requested document was not found.")
    return row


@router.get("/{document_id}", response_model=DocumentOut)
def get_document(
    document_id: UUID,
    user: dict = Depends(get_current_user),
    store: DocumentStore = Depends(get_document_store),
) -> dict:
    return _load_or_404(document_id, store)


@router.get("/{document_id}/status", response_model=DocumentStatusOut)
def get_document_status(
    document_id: UUID,
    user: dict = Depends(get_current_user),
    store: DocumentStore = Depends(get_document_store),
) -> dict:
    row = _load_or_404(document_id, store)
    return {"document_id": row["id"], "status": row["processing_status"]}


def _record_for_document_or_404(document_id: UUID, store: DocumentStore, records: RecordStore) -> dict:
    _load_or_404(document_id, store)
    record = records.get_record_by_document(str(document_id))
    if record is None:
        raise AppError(404, "EXTRACTION_NOT_FOUND", "This document has no extracted record yet.")
    return record


@router.get("/{document_id}/extraction", response_model=DocumentExtractionOut)
def get_document_extraction(
    document_id: UUID,
    user: dict = Depends(get_current_user),
    store: DocumentStore = Depends(get_document_store),
    records: RecordStore = Depends(get_record_store),
) -> dict:
    _ = user
    record = _record_for_document_or_404(document_id, store, records)
    return {"document_id": str(document_id), "record_id": record["id"], "status": record.get("status"),
            "fields": records.list_extracted_fields(str(record["id"]))}


@router.get("/{document_id}/validation", response_model=DocumentValidationOut)
def get_document_validation(
    document_id: UUID,
    user: dict = Depends(get_current_user),
    store: DocumentStore = Depends(get_document_store),
    records: RecordStore = Depends(get_record_store),
) -> dict:
    _ = user
    from ..records.service import stored_validation_verdict

    record = _record_for_document_or_404(document_id, store, records)
    rows = records.list_validation_results(str(record["id"]))
    return {"document_id": str(document_id), "record_id": record["id"],
            "status": stored_validation_verdict(rows), "issues": rows}
