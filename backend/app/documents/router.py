"""Document endpoints per 10_API_SPECIFICATION section 3 (upload,
metadata, status, processing, extraction, validation).
Versioned under /api/v1.
"""
import io
import re
import sys
from pathlib import Path as FilePath
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Path, Request, UploadFile
from fastapi.responses import Response

from ..auth.dependencies import get_current_user, require_role
from ..config import get_settings
from ..errors import AppError
from ..reviews.stores import RecordStore, get_record_store
from ..processing.stores import JobStore, get_job_store
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

_SAFE_STORAGE_PATH = re.compile(
    r"\Adocuments/[0-9a-f]{32}/[0-9a-f]{32}\.(?:pdf|png|jpg|tif)\Z",
    re.IGNORECASE,
)
_MIME_TO_SUFFIX = {
    "application/pdf": ".pdf",
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/tiff": ".tif",
}


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


@router.get("/{document_id}/status", response_model=DocumentStatusOut, response_model_exclude_none=True)
def get_document_status(
    document_id: UUID,
    user: dict = Depends(get_current_user),
    store: DocumentStore = Depends(get_document_store),
    jobs: JobStore = Depends(get_job_store),
) -> dict:
    row = _load_or_404(document_id, store)
    latest_reader = getattr(jobs, "latest_job_for_document", None)
    if callable(latest_reader):
        latest = latest_reader(str(document_id))
    else:
        history = jobs.list_jobs_for_document(str(document_id))
        latest = history[0] if history else None
    return {
        "document_id": row["id"],
        "status": row["processing_status"],
        "job_id": latest.get("id") if latest else None,
        "job_status": latest.get("status") if latest else None,
        "error_code": latest.get("error_code") if latest else None,
        "error_message": latest.get("error_message") if latest else None,
        "started_at": latest.get("started_at") if latest else None,
        "completed_at": latest.get("completed_at") if latest else None,
    }


@router.get("/{document_id}/pages/{page_number}", response_class=Response,
            responses={200: {"content": {"image/jpeg": {}}}})
def get_document_page(
    document_id: UUID,
    page_number: int = Path(..., ge=1, le=10000),
    user: dict = Depends(require_role("user")),
    store: DocumentStore = Depends(get_document_store),
    storage: StorageBackend = Depends(get_storage_backend),
) -> Response:
    """Return one privately stored source page as a browser-safe JPEG.

    Read access follows the product model: authenticated `user` accounts may
    view records and their source evidence; operators and admins inherit it.
    The storage path is an internal generated reference and is never returned.
    """
    _ = user
    document = _load_or_404(document_id, store)
    storage_path = document.get("storage_path")
    if not isinstance(storage_path, str) or not _SAFE_STORAGE_PATH.fullmatch(storage_path):
        raise AppError(404, "DOCUMENT_SOURCE_NOT_FOUND", "The document source is unavailable.")

    suffix = _MIME_TO_SUFFIX.get(str(document.get("file_type") or "").lower())
    if suffix is None:
        raise AppError(422, "DOCUMENT_SOURCE_INVALID", "The document source cannot be rendered.")

    try:
        source = storage.download(storage_path)
    except FileNotFoundError as exc:
        raise AppError(404, "DOCUMENT_SOURCE_NOT_FOUND", "The document source is unavailable.") from exc
    except Exception as exc:
        # Do not expose storage provider errors, URLs, or internal paths.
        status = getattr(exc, "status_code", None) or getattr(exc, "status", None)
        if status == 404:
            raise AppError(404, "DOCUMENT_SOURCE_NOT_FOUND", "The document source is unavailable.") from exc
        raise AppError(503, "STORAGE_UNAVAILABLE", "Document storage is temporarily unavailable.") from exc

    try:
        # The OCR package lives at the repository root and is intentionally
        # imported lazily so document routes can boot from the backend cwd.
        repo_root = str(FilePath(__file__).resolve().parents[3])
        if repo_root not in sys.path:
            sys.path.insert(0, repo_root)
        from ai.ocr.pdf_render import (  # noqa: PLC0415
            PageNotFoundError,
            SourceRenderError,
            render_page_from_bytes,
        )
        image = render_page_from_bytes(source, suffix, page_number, dpi=150)
    except PageNotFoundError as exc:
        raise AppError(404, "DOCUMENT_PAGE_NOT_FOUND", "The requested document page was not found.") from exc
    except SourceRenderError as exc:
        raise AppError(422, "DOCUMENT_SOURCE_INVALID", "The document source cannot be rendered.") from exc

    output = io.BytesIO()
    try:
        image.save(output, format="JPEG", quality=85, optimize=True)
    except Exception as exc:
        raise AppError(422, "DOCUMENT_SOURCE_INVALID", "The document source cannot be rendered.") from exc
    finally:
        image.close()

    return Response(
        content=output.getvalue(),
        media_type="image/jpeg",
        headers={
            "Cache-Control": "private, no-store",
            "Content-Disposition": "inline",
            "X-Content-Type-Options": "nosniff",
        },
    )


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
