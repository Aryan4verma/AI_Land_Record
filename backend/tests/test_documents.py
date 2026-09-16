"""Document upload/storage checks with faked persistence (no live DB)."""
import hashlib
import uuid
from datetime import datetime, timezone

import pytest

from app.documents import validation as v
from app.documents.storage_backend import get_storage_backend
from app.documents.store import get_document_store
from app.errors import AppError
from app.main import app
from tests.conftest import OP_ID

PDF = b"%PDF-1.7\n%\xe2\xe3\n"
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16
JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 16
TIFF_LE = b"II*\x00" + b"\x00" * 16
TIFF_BE = b"MM\x00*" + b"\x00" * 16


class FakeStore:
    def __init__(self):
        self.rows = {}
        self.fail = False
        self.fail_with = None

    def create(self, row):
        if self.fail_with is not None:
            raise self.fail_with
        if self.fail:
            raise RuntimeError("db down")
        # Mirror DB defaults: UUID id + server timestamps.
        now = datetime.now(timezone.utc).isoformat()
        rid = str(uuid.uuid4())
        saved = {"id": rid, "uploaded_at": now, "created_at": now, "updated_at": now, **row}
        self.rows[rid] = saved
        return saved

    def get(self, document_id):
        return self.rows.get(document_id)


class FakeStorage:
    def __init__(self):
        self.objects = {}
        self.fail_upload = False

    def upload(self, path, data, content_type):
        if self.fail_upload:
            raise RuntimeError("storage down")
        self.objects[path] = (data, content_type)

    def remove(self, path):
        self.objects.pop(path, None)


@pytest.fixture()
def fakes():
    store, storage = FakeStore(), FakeStorage()
    app.dependency_overrides[get_document_store] = lambda: store
    app.dependency_overrides[get_storage_backend] = lambda: storage
    yield store, storage


def _token(client):
    response = client.post("/api/v1/auth/login", json={"email": "op@example.com", "password": "op-pass"})
    assert response.status_code == 200
    return response.json()["access_token"]


def _auth(client):
    return {"Authorization": f"Bearer {_token(client)}"}


def test_valid_pdf_upload_persists_and_retrieves(client, fakes):
    store, storage = fakes
    response = client.post(
        "/api/v1/documents",
        files={"file": ("record.pdf", PDF, "application/pdf")},
        data={"document_type": "khata", "language": "en"},
        headers=_auth(client),
    )
    assert response.status_code == 201
    document_id = response.json()["document_id"]
    assert response.json()["status"] == "UPLOADED"

    meta = client.get(f"/api/v1/documents/{document_id}", headers=_auth(client))
    assert meta.status_code == 200
    body = meta.json()
    assert body["file_name"] == "record.pdf"
    assert body["file_type"] == "application/pdf"
    assert body["file_size"] == len(PDF)
    assert body["checksum"] == hashlib.sha256(PDF).hexdigest()
    assert body["document_type"] == "khata"
    assert body["language"] == "en"
    assert body["uploaded_by"] == OP_ID
    assert body["processing_status"] == "UPLOADED"
    assert body["storage_path"].startswith("documents/")
    assert body["storage_path"].endswith(".pdf")
    assert "record.pdf" not in body["storage_path"]  # generated name only

    status = client.get(f"/api/v1/documents/{document_id}/status", headers=_auth(client))
    assert status.status_code == 200
    assert status.json() == {"document_id": document_id, "status": "UPLOADED"}

    assert len(storage.objects) == 1
    stored_bytes, content_type = next(iter(storage.objects.values()))
    assert stored_bytes == PDF
    assert content_type == "application/pdf"


def test_valid_png_upload_without_optional_fields(client, fakes):
    headers = _auth(client)
    response = client.post(
        "/api/v1/documents", files={"file": ("scan.png", PNG, "image/png")}, headers=headers
    )
    assert response.status_code == 201
    meta = client.get(f"/api/v1/documents/{response.json()['document_id']}", headers=headers)
    assert meta.json()["document_type"] is None
    assert meta.json()["language"] is None


def test_invalid_file_type_rejected(client, fakes):
    store, storage = fakes
    response = client.post(
        "/api/v1/documents",
        files={"file": ("evil.exe", b"MZ\x90\x00", "application/x-msdownload")},
        headers=_auth(client),
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "UNSUPPORTED_FILE_TYPE"
    assert store.rows == {}
    assert storage.objects == {}


def test_extension_mime_mismatch_rejected(client, fakes):
    response = client.post(
        "/api/v1/documents",
        files={"file": ("record.pdf", PNG, "image/png")},
        headers=_auth(client),
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "FILE_TYPE_MISMATCH"


def test_content_mismatch_rejected(client, fakes):
    response = client.post(
        "/api/v1/documents",
        files={"file": ("record.pdf", PNG, "application/pdf")},
        headers=_auth(client),
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "FILE_CONTENT_MISMATCH"


def test_empty_file_rejected(client, fakes):
    response = client.post(
        "/api/v1/documents",
        files={"file": ("empty.pdf", b"", "application/pdf")},
        headers=_auth(client),
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "EMPTY_FILE"


def test_oversized_file_rejected(client, fakes):
    big = b"%PDF-" + b"\x00" * (10 * 1024 * 1024 + 1 - len(b"%PDF-"))
    response = client.post(
        "/api/v1/documents",
        files={"file": ("big.pdf", big, "application/pdf")},
        headers=_auth(client),
    )
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "FILE_TOO_LARGE"


def test_upload_requires_authentication(client, fakes):
    response = client.post(
        "/api/v1/documents", files={"file": ("record.pdf", PDF, "application/pdf")}
    )
    assert response.status_code == 401


def test_get_unknown_document_returns_404(client, fakes):
    response = client.get(f"/api/v1/documents/{uuid.uuid4()}", headers=_auth(client))
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "DOCUMENT_NOT_FOUND"


def test_get_malformed_id_returns_422(client, fakes):
    response = client.get("/api/v1/documents/not-a-uuid", headers=_auth(client))
    assert response.status_code == 422


def test_storage_failure_leaves_no_row(client, fakes):
    store, storage = fakes
    storage.fail_upload = True
    response = client.post(
        "/api/v1/documents",
        files={"file": ("record.pdf", PDF, "application/pdf")},
        headers=_auth(client),
    )
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "STORAGE_UNAVAILABLE"
    assert store.rows == {}


def test_db_failure_cleans_uploaded_bytes(client, fakes):
    """An opaque store fault still cleans up the uploaded object.

    STEP 4: it is now reported as 500 PERSISTENCE_FAILED, not 503. An
    unrecognized exception is an *unexpected* failure — calling it
    "temporarily unavailable" told operators to retry a fault that would
    never resolve, which is exactly what hid the record_date defect.
    """
    store, storage = fakes
    store.fail = True
    response = client.post(
        "/api/v1/documents",
        files={"file": ("record.pdf", PDF, "application/pdf")},
        headers=_auth(client),
    )
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "PERSISTENCE_FAILED"
    assert storage.objects == {}


def test_genuine_connection_failure_is_reported_as_unavailable(client, fakes):
    """A real transport failure keeps the retryable 503 classification."""

    class ConnectError(Exception):
        pass

    store, storage = fakes
    store.fail_with = ConnectError("connection refused")
    response = client.post(
        "/api/v1/documents",
        files={"file": ("record.pdf", PDF, "application/pdf")},
        headers=_auth(client),
    )
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "DATABASE_UNAVAILABLE"
    assert storage.objects == {}


def test_duplicate_constraint_on_upload_is_reported_as_conflict(client, fakes):
    """A unique violation is a 409, not an outage."""

    class ApiError(Exception):
        def __init__(self):
            super().__init__("duplicate key value violates unique constraint")
            self.code = "23505"

    store, storage = fakes
    store.fail_with = ApiError()
    response = client.post(
        "/api/v1/documents",
        files={"file": ("record.pdf", PDF, "application/pdf")},
        headers=_auth(client),
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "ALREADY_EXISTS"
    assert storage.objects == {}


def test_db_apperror_cleans_uploaded_bytes_and_preserves_error(client, fakes):
    """Phase 1E: a store-level AppError (e.g. constraint/RLS rejection) must
    also remove the already-uploaded object — otherwise every such failure
    leaks an orphan into the private bucket. The original error propagates."""
    store, storage = fakes
    store.fail_with = AppError(503, "DATABASE_UNAVAILABLE", "Document store is temporarily unavailable.")
    response = client.post(
        "/api/v1/documents",
        files={"file": ("record.pdf", PDF, "application/pdf")},
        headers=_auth(client),
    )
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "DATABASE_UNAVAILABLE"
    assert store.rows == {}
    assert storage.objects == {}


def test_validation_units():
    assert v.sanitize_filename("../../etc/passwd.pdf") == "passwd.pdf"
    assert v.sanitize_filename("   ") == "upload"
    assert v.sanitize_filename(None) == "upload"
    assert len(v.sanitize_filename("a" * 300 + ".pdf")) == 255
    assert v.sha256_hex(b"abc") == hashlib.sha256(b"abc").hexdigest()
    first, second = v.build_storage_path("pdf"), v.build_storage_path("pdf")
    assert first.startswith("documents/") and first.endswith(".pdf")
    assert first != second
    v.verify_content(TIFF_LE, "image/tiff")
    v.verify_content(TIFF_BE, "image/tiff")
    v.verify_content(JPEG, "image/jpeg")
    assert v.resolve_mime("scan", "image/png") == "image/png"
    with pytest.raises(Exception):
        v.resolve_mime("notes.txt", "text/plain")
