"""Authenticated source-page rendering tests using private-storage fakes."""
import io
import sys
import uuid
from pathlib import Path

import pymupdf
import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.documents.store import get_document_store  # noqa: E402
from app.documents.storage_backend import get_storage_backend  # noqa: E402
from app.main import app  # noqa: E402

DOC_ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
OTHER_ID = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
STORAGE_PATH = "documents/0123456789abcdef0123456789abcdef/abcdef0123456789abcdef0123456789.pdf"


def _pdf_bytes() -> bytes:
    document = pymupdf.open()
    for number in (1, 2):
        page = document.new_page(width=300, height=200)
        page.insert_text((40, 90), f"source page {number}")
    try:
        return document.tobytes()
    finally:
        document.close()


class FakeDocuments:
    def __init__(self):
        self.rows = {
            DOC_ID: {
                "id": DOC_ID,
                "file_type": "application/pdf",
                "storage_path": STORAGE_PATH,
                "processing_status": "REVIEW_REQUIRED",
            }
        }

    def get(self, document_id):
        return self.rows.get(document_id)


class FakeStorage:
    def __init__(self, source: bytes):
        self.source = source
        self.downloads = []
        self.missing = False

    def download(self, path):
        self.downloads.append(path)
        if self.missing:
            raise FileNotFoundError(path)
        return self.source


@pytest.fixture()
def page_backend():
    documents = FakeDocuments()
    storage = FakeStorage(_pdf_bytes())
    app.dependency_overrides[get_document_store] = lambda: documents
    app.dependency_overrides[get_storage_backend] = lambda: storage
    try:
        yield documents, storage
    finally:
        app.dependency_overrides.pop(get_document_store, None)
        app.dependency_overrides.pop(get_storage_backend, None)


def _token(client, email="op@example.com", password="op-pass"):
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]


def _auth(client, email="op@example.com", password="op-pass"):
    return {"Authorization": f"Bearer {_token(client, email, password)}"}


def test_valid_page_returns_non_empty_jpeg(client, page_backend):
    _, storage = page_backend
    response = client.get(f"/api/v1/documents/{DOC_ID}/pages/1", headers=_auth(client))

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.content
    assert storage.downloads == [STORAGE_PATH]
    with Image.open(io.BytesIO(response.content)) as image:
        assert image.format == "JPEG"
        assert image.width > 0 and image.height > 0


def test_multiple_pages_render_independently(client, page_backend):
    first = client.get(f"/api/v1/documents/{DOC_ID}/pages/1", headers=_auth(client))
    second = client.get(f"/api/v1/documents/{DOC_ID}/pages/2", headers=_auth(client))

    assert first.status_code == second.status_code == 200
    assert first.content and second.content
    assert first.content != second.content


def test_page_out_of_range_returns_safe_404(client, page_backend):
    response = client.get(f"/api/v1/documents/{DOC_ID}/pages/3", headers=_auth(client))

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "DOCUMENT_PAGE_NOT_FOUND"


def test_non_positive_page_is_rejected(client, page_backend):
    response = client.get(f"/api/v1/documents/{DOC_ID}/pages/0", headers=_auth(client))

    assert response.status_code == 422


def test_missing_document_returns_404(client, page_backend):
    response = client.get(f"/api/v1/documents/{OTHER_ID}/pages/1", headers=_auth(client))

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "DOCUMENT_NOT_FOUND"


def test_missing_private_source_returns_safe_404(client, page_backend):
    _, storage = page_backend
    storage.missing = True
    response = client.get(f"/api/v1/documents/{DOC_ID}/pages/1", headers=_auth(client))

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "DOCUMENT_SOURCE_NOT_FOUND"


def test_unauthenticated_request_is_rejected(client, page_backend):
    response = client.get(f"/api/v1/documents/{DOC_ID}/pages/1")

    assert response.status_code == 401


def test_invalid_token_is_unauthorized(client, page_backend):
    response = client.get(
        f"/api/v1/documents/{DOC_ID}/pages/1",
        headers={"Authorization": "Bearer not-a-valid-token"},
    )

    assert response.status_code == 401


def test_read_only_user_can_view_source_under_current_role_model(client, page_backend):
    response = client.get(
        f"/api/v1/documents/{DOC_ID}/pages/1",
        headers=_auth(client, "user@example.com", "user-pass"),
    )

    assert response.status_code == 200


def test_corrupt_document_fails_without_library_details(client, page_backend):
    _, storage = page_backend
    storage.source = b"not a real PDF"
    response = client.get(f"/api/v1/documents/{DOC_ID}/pages/1", headers=_auth(client))

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "DOCUMENT_SOURCE_INVALID"
    assert "pymupdf" not in body["error"]["message"].lower()


def test_path_traversal_storage_reference_is_rejected(client, page_backend):
    documents, storage = page_backend
    documents.rows[DOC_ID]["storage_path"] = "documents/../outside.pdf"
    response = client.get(f"/api/v1/documents/{DOC_ID}/pages/1", headers=_auth(client))

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "DOCUMENT_SOURCE_NOT_FOUND"
    assert storage.downloads == []
