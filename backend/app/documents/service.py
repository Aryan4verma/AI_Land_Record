"""Upload orchestration: validate -> store bytes -> insert row.

The AI pipeline is NOT started here (STEP 04 scope ends at UPLOADED).
If the DB insert fails after a successful upload, the stored object is
removed again so no orphan bytes are left behind.
"""
from typing import Any

from fastapi import UploadFile

from ..db_errors import classify_db_error
from ..errors import AppError
from ..logging_config import get_logger
from . import validation as v
from .storage_backend import StorageBackend
from .store import DocumentStore

log = get_logger(__name__)

_CHUNK_SIZE = 1024 * 1024  # 1 MiB streaming reads; oversized uploads abort early


async def _read_limited(upload: UploadFile, max_bytes: int) -> bytes:
    parts: list[bytes] = []
    total = 0
    while True:
        chunk = await upload.read(_CHUNK_SIZE)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise AppError(413, "FILE_TOO_LARGE", "File exceeds the configured size limit.")
        parts.append(chunk)
    return b"".join(parts)


def _optional_text(value: str | None) -> str | None:
    cleaned = (value or "").strip()
    return cleaned or None


async def upload_document(
    *,
    file: UploadFile,
    document_type: str | None,
    language: str | None,
    user_id: str,
    max_bytes: int,
    store: DocumentStore,
    storage: StorageBackend,
) -> dict[str, Any]:
    safe_name = v.sanitize_filename(file.filename)
    mime = v.resolve_mime(safe_name, file.content_type)
    data = await _read_limited(file, max_bytes)
    v.check_size(len(data), max_bytes)
    v.verify_content(data, mime)

    checksum = v.sha256_hex(data)
    storage_path = v.build_storage_path(v.canonical_extension(mime))

    try:
        storage.upload(storage_path, data, mime)
    except AppError:
        raise
    except Exception as exc:
        raise AppError(503, "STORAGE_UNAVAILABLE", "Document storage is temporarily unavailable.") from exc

    row = {
        "file_name": safe_name,
        "file_type": mime,
        "file_size": len(data),
        "checksum": checksum,
        "document_type": _optional_text(document_type),
        "language": _optional_text(language),
        "storage_path": storage_path,
        "uploaded_by": user_id,
        "processing_status": "UPLOADED",
    }
    try:
        created = store.create(row)
    except AppError:
        # The DB insert failed, so no row references the uploaded bytes:
        # remove the orphan object (cleanup failure is logged, never masks
        # the original error).
        try:
            storage.remove(storage_path)
        except Exception:
            log.warning("storage cleanup failed")
        raise
    except Exception as exc:
        try:
            storage.remove(storage_path)
        except Exception:
            log.warning("storage cleanup failed")
        raise classify_db_error(
            exc, subject="Document store", action="documents.upload") from exc

    log.info("document uploaded")
    return {"document_id": created["id"], "status": created["processing_status"]}
