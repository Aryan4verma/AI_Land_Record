"""Upload validation: extension, MIME, size, filename, magic bytes.

Implements 11_SECURITY_DESIGN section 5 (validate type/MIME/size/filename
and content where practical; generated internal storage names only).
"""
import hashlib
import os
import uuid

from ..errors import AppError

_MIME_TO_EXT = {
    "application/pdf": "pdf",
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/tiff": "tif",
}
_EXT_TO_MIME = {
    "pdf": "application/pdf",
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "tif": "image/tiff",
    "tiff": "image/tiff",
}
_MAGIC = {
    "application/pdf": (b"%PDF-",),
    "image/png": (b"\x89PNG\r\n\x1a\n",),
    "image/jpeg": (b"\xff\xd8\xff",),
    "image/tiff": (b"II*\x00", b"MM\x00*"),
}
_MAX_FILENAME_LEN = 255


def sanitize_filename(name: str | None) -> str:
    """Strip directories and unsafe characters; never trust the client name."""
    base = os.path.basename((name or "").strip())
    base = "".join(ch for ch in base if ch.isprintable()).strip(" .")
    if not base:
        return "upload"
    return base[:_MAX_FILENAME_LEN]


def check_size(size: int, max_bytes: int) -> None:
    if size <= 0:
        raise AppError(400, "EMPTY_FILE", "Uploaded file is empty.")
    if size > max_bytes:
        raise AppError(413, "FILE_TOO_LARGE", "File exceeds the configured size limit.")


def resolve_mime(filename: str, content_type: str | None) -> str:
    """Cross-check extension against declared MIME; both must agree."""
    ext = os.path.splitext(filename)[1].lower().lstrip(".")
    declared = (content_type or "").split(";")[0].strip().lower()
    mime: str | None = declared if declared in _MIME_TO_EXT else None
    if ext in _EXT_TO_MIME:
        expected = _EXT_TO_MIME[ext]
        if mime is None:
            mime = expected
        elif mime != expected:
            raise AppError(400, "FILE_TYPE_MISMATCH", "File extension does not match the declared file type.")
    if mime is None:
        raise AppError(400, "UNSUPPORTED_FILE_TYPE", "Only PDF, PNG, JPEG, and TIFF files are supported.")
    return mime


def verify_content(data: bytes, mime: str) -> None:
    """Magic-byte sniffing: content must match the declared type."""
    if not any(data.startswith(marker) for marker in _MAGIC[mime]):
        raise AppError(400, "FILE_CONTENT_MISMATCH", "File content does not match its declared type.")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_extension(mime: str) -> str:
    return _MIME_TO_EXT[mime]


def build_storage_path(extension: str) -> str:
    """Generated internal reference only — never derived from user input."""
    return f"documents/{uuid.uuid4().hex}/{uuid.uuid4().hex}.{extension}"
