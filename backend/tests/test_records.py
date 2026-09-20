"""Records/search/dashboard/export/integration checks with fakes."""
import uuid
from datetime import datetime, timezone

from app.main import app
from app.documents.store import get_document_store
from app.records.stores import (
    SupabaseRecordQueryStore,
    _escape_like,
    _is_unsatisfiable_range,
    get_dashboard_store,
    get_record_query_store,
)
from app.reviews.stores import get_record_store
from app.reviews.stores import get_audit_store

NOW = "2026-09-04T00:00:00+00:00"
R1 = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
R2 = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
R3 = "cccccccc-cccc-4ccc-8ccc-cccccccccccc"
D1 = "dddddddd-dddd-4ddd-8ddd-dddddddddddd"
D2 = "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee"
D3 = "ffffffff-ffff-4fff-8fff-ffffffffffff"


def _rec(rec_id, doc_id, owner, survey, village, status):
    return {"id": rec_id, "document_id": doc_id, "status": status, "owner_name": owner,
            "survey_number": survey, "khasra_number": None, "khata_number": None,
            "area": "1.0", "area_unit": "hectare", "village": village,
            "tehsil": "Demo Tehsil", "district": "Demo District",
            "land_classification": None, "mutation_number": None,
            "registration_number": None, "record_date": None,
            "approved_by": None, "approved_at": None, "created_at": NOW, "updated_at": NOW}


class FakeRecords:
    def __init__(self):
        self.records = {
            R1: _rec(R1, D1, "Ramesh Kumar", "145/2", "Demo Village", "APPROVED"),
            R2: _rec(R2, D2, "Sunita Devi", "99", "Demo Village", "REVIEW_REQUIRED"),
            R3: _rec(R3, D3, "Ramesh Kumar", "77", "Other Village", "DRAFT"),
        }

    def get_record(self, record_id):
        return self.records.get(record_id)

    def get_record_by_document(self, document_id):
        return next((r for r in self.records.values() if r["document_id"] == document_id), None)

    def create_record(self, row):
        saved = {"id": str(uuid.uuid4()), **row}
        self.records[saved["id"]] = saved
        return saved

    def update_record(self, record_id, patch):
        self.records[record_id].update(patch)
        return self.records[record_id]

    def list_extracted_fields(self, record_id):
        if record_id not in self.records:
            return []
        return [{"field_name": "owner_name", "value": self.records[record_id]["owner_name"],
                 "confidence": 0.9}]

    def replace_extracted_fields(self, record_id, rows):
        return None

    def replace_validation_results(self, record_id, rows):
        return None

    def list_validation_results(self, record_id):
        if record_id == R1:
            return []
        return [{"rule_id": "REQ_X", "field_name": "area", "status": "REVIEW_REQUIRED",
                 "severity": "WARNING", "message": "m"}]

    def save_correction(self, row):
        return row

    def get_document(self, document_id):
        if document_id in (D1, D2, D3):
            return {"id": document_id, "file_name": "s.pdf", "processing_status": "APPROVED"}
        return None

    def list_reference_rows(self):
        return []


class FakeQuery:
    def __init__(self, records):
        self._records = records

    def search_records(self, filters, page, limit):
        rows = list(self._records.values())
        mapping = {"owner": "owner_name", "survey_number": "survey_number",
                   "khasra_number": "khasra_number", "village": "village",
                   "tehsil": "tehsil", "district": "district"}
        for param, column in mapping.items():
            if filters.get(param):
                rows = [r for r in rows if filters[param].lower() in str(r.get(column) or "").lower()]
        if filters.get("status"):
            rows = [r for r in rows if r.get("status") == filters["status"]]
        total = len(rows)
        start = (page - 1) * limit
        return rows[start:start + limit], total


class FakeDashboard:
    def summary(self):
        return {"documents_total": 3, "documents_by_status": {"APPROVED": 1},
                "records_by_status": {"APPROVED": 1}, "open_reviews": 2, "average_confidence": 0.9}

    def processing(self):
        return {"jobs_by_status": {"SUCCEEDED": 1}, "recent_jobs": [{"id": "j1"}]}

    def validation(self):
        return {"issues_by_severity": {"WARNING": 2}, "issues_by_status": {"REVIEW_REQUIRED": 2},
                "blocked_documents": 0}


class FakeDocs:
    def get(self, document_id):
        if document_id in (D1, D2, D3):
            return {"id": document_id, "processing_status": "APPROVED"}
        return None

    def create(self, row):
        return row

    def update_status(self, document_id, status):
        return {}


class FakeAudit:
    def __init__(self):
        self.entries = []

    def append(self, entry):
        self.entries.append(entry)
        return entry


import pytest


@pytest.fixture()
def fakes():
    records = FakeRecords()
    audits = FakeAudit()
    app.dependency_overrides[get_record_store] = lambda: records
    app.dependency_overrides[get_record_query_store] = lambda: FakeQuery(records.records)
    app.dependency_overrides[get_dashboard_store] = lambda: FakeDashboard()
    app.dependency_overrides[get_document_store] = lambda: FakeDocs()
    app.dependency_overrides[get_audit_store] = lambda: audits
    yield records, audits
    app.dependency_overrides.clear()


def _token(client, email="op@example.com", password="op-pass"):
    return client.post("/api/v1/auth/login", json={"email": email, "password": password}).json()["access_token"]


def test_search_filters_and_pagination(client, fakes):
    headers = {"Authorization": f"Bearer {_token(client)}"}
    body = client.get("/api/v1/records", headers=headers).json()
    assert body["total"] == 3 and body["page"] == 1 and len(body["items"]) == 3
    assert client.get("/api/v1/records", params={"owner": "ramesh"}, headers=headers).json()["total"] == 2
    assert client.get("/api/v1/records", params={"status": "APPROVED"}, headers=headers).json()["total"] == 1
    page2 = client.get("/api/v1/records", params={"page": 2, "limit": 2}, headers=headers).json()
    assert page2["total"] == 3 and len(page2["items"]) == 1
    assert client.get("/api/v1/records", params={"status": "BOGUS"}, headers=headers).status_code == 422
    assert client.get("/api/v1/records").status_code == 401


def test_record_detail_and_404(client, fakes):
    headers = {"Authorization": f"Bearer {_token(client)}"}
    body = client.get(f"/api/v1/records/{R1}", headers=headers).json()
    assert body["record"]["id"] == R1 and body["document"]["id"] == D1
    assert body["extracted_fields"][0]["field_name"] == "owner_name"
    assert client.get("/api/v1/records/00000000-0000-4000-8000-000000000000",
                      headers=headers).status_code == 404


def test_extraction_and_validation_endpoints(client, fakes):
    headers = {"Authorization": f"Bearer {_token(client)}"}
    ext = client.get(f"/api/v1/documents/{D1}/extraction", headers=headers).json()
    assert ext["record_id"] == R1 and ext["fields"][0]["confidence"] == 0.9
    val = client.get(f"/api/v1/documents/{D2}/validation", headers=headers).json()
    assert val["record_id"] == R2 and val["status"] == "REVIEW_REQUIRED" and len(val["issues"]) == 1
    assert client.get("/api/v1/documents/00000000-0000-4000-8000-000000000000/extraction",
                      headers=headers).status_code == 404
    assert client.get(f"/api/v1/documents/{D1}/validation").status_code == 401


def test_dashboard_shapes(client, fakes):
    headers = {"Authorization": f"Bearer {_token(client)}"}
    summary = client.get("/api/v1/dashboard/summary", headers=headers).json()
    assert summary["documents_total"] == 3 and summary["open_reviews"] == 2
    assert client.get("/api/v1/dashboard/processing", headers=headers).json()["recent_jobs"] == [{"id": "j1"}]
    assert client.get("/api/v1/dashboard/validation", headers=headers).json()["blocked_documents"] == 0
    assert client.get("/api/v1/dashboard/summary").status_code == 401


def test_export_and_mock_lrms(client, fakes):
    records, audits = fakes
    headers = {"Authorization": f"Bearer {_token(client)}"}
    export = client.get(f"/api/v1/records/{R1}/export", headers=headers).json()
    assert export["record"]["id"] == R1 and export["format_version"] == "v1" and export["exported_at"]
    ver = {"Authorization": f"Bearer {_token(client, 'ver@example.com', 'ver-pass')}"}
    accepted = client.post("/api/v1/integrations/mock-lrms", json={"record_id": R1}, headers=ver).json()
    assert accepted["status"] == "accepted" and "not a live government" in accepted["disclaimer"]
    assert audits.entries[-1]["action"] == "MOCK_LRMS_DISPATCHED"
    assert audits.entries[-1]["entity_id"] == R1
    audit_count = len(audits.entries)
    refused = client.post("/api/v1/integrations/mock-lrms", json={"record_id": R2}, headers=ver)
    assert refused.status_code == 409
    assert len(audits.entries) == audit_count
    assert client.post("/api/v1/integrations/mock-lrms",
                       json={"record_id": "00000000-0000-4000-8000-000000000000"},
                       headers=ver).status_code == 404
    reader = {"Authorization": f"Bearer {_token(client, 'user@example.com', 'user-pass')}"}
    assert client.post("/api/v1/integrations/mock-lrms", json={"record_id": R1},
                       headers=reader).status_code == 403


class _RangeError(Exception):
    def __init__(self):
        self.code = "PGRST103"
        super().__init__("Requested range not satisfiable")


class _FakeResult:
    def __init__(self, data, count):
        self.data = data
        self.count = count


class _FakePostgrestChain:
    """Mimics supabase-py's chaining API; range() beyond rows raises PGRST103."""

    def __init__(self, total):
        self._total = total
        self._ranged = False

    def select(self, *args, **kwargs):
        return self

    def ilike(self, *args):
        return self

    def eq(self, *args):
        return self

    def order(self, *args, **kwargs):
        return self

    def range(self, *args):
        self._ranged = True
        return self

    def limit(self, *args):
        return self

    def execute(self):
        if self._ranged:
            raise _RangeError()
        return _FakeResult([], self._total)


class _FakeClient:
    def __init__(self, total):
        self._total = total

    def table(self, name):
        return _FakePostgrestChain(self._total)


def test_search_beyond_last_page_returns_empty_with_total():
    store = SupabaseRecordQueryStore(_FakeClient(3))
    rows, total = store.search_records({}, 99, 20)
    assert rows == [] and total == 3


def test_unsatisfiable_range_detection():
    assert _is_unsatisfiable_range(_RangeError()) is True
    assert _is_unsatisfiable_range(ValueError("nope")) is False


def test_like_wildcards_escaped():
    assert _escape_like("100%") == "100\\%"
    assert _escape_like("a_b\\c") == "a\\_b\\\\c"
    assert _escape_like("plain") == "plain"


def test_search_sends_escaped_like_pattern():
    patterns = []

    class _Chain(_FakePostgrestChain):
        def ilike(self, column, pattern):
            patterns.append((column, pattern))
            return self

    class _Client(_FakeClient):
        def table(self, name):
            chain = _Chain(self._total)
            chain.execute = lambda: _FakeResult([{"id": "x"}], 1)
            return chain

    store = SupabaseRecordQueryStore(_Client(1))
    rows, total = store.search_records({"owner": "100%_x"}, 1, 20)
    assert total == 1 and rows == [{"id": "x"}]
    assert patterns == [("owner_name", "%100\\%\\_x%")]
