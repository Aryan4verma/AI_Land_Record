"""TEMPORARY verification for the exact 78 -> 73 Step 10 workflow.

Isolated: in-memory fakes only (no Supabase, no AI provider calls —
the review path imports only stdlib validation code). Proves:
review -> correct area 78->73 with reason -> audit old/new ->
revalidation -> complete -> approve -> ordered audit chain.
"""
import uuid

from app.reviews.stores import get_audit_store, get_record_store, get_review_store
from app.main import app
from tests.test_reviews import BASE_RECORD, FakeAuditStore, FakeRecordStore, FakeReviewStore

REC_78 = "dddddddd-dddd-4ddd-8ddd-dddddddddddd"


def _seed(stores):
    records, _, _ = stores
    row = {"id": REC_78, "document_id": str(uuid.uuid4()), "status": "REVIEW_REQUIRED",
           "approved_by": None, "approved_at": None, **BASE_RECORD}
    row["area"] = "78"
    records.records[REC_78] = row
    records.documents[row["document_id"]] = {"id": row["document_id"], "file_name": "verify.pdf",
                                             "processing_status": "VALIDATION_FAILED"}


def _token(client, email, password):
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]


def test_step10_area_78_to_73_full_chain(client):
    stores = (FakeRecordStore(), FakeReviewStore(), FakeAuditStore())
    app.dependency_overrides[get_record_store] = lambda: stores[0]
    app.dependency_overrides[get_review_store] = lambda: stores[1]
    app.dependency_overrides[get_audit_store] = lambda: stores[2]
    try:
        _seed(stores)
        records, _, audits = stores
        op = {"Authorization": f"Bearer {_token(client, 'op@example.com', 'op-pass')}"}
        ver = {"Authorization": f"Bearer {_token(client, 'ver@example.com', 'ver-pass')}"}

        assert records.get_record(REC_78)["area"] == "78"

        task_id = client.post(
            "/api/v1/reviews",
            json={"land_record_id": REC_78, "reason": "area needs verification", "priority": "HIGH"},
            headers=op).json()["id"]

        patched = client.patch(
            f"/api/v1/reviews/{task_id}/fields/area",
            json={"value": "73", "reason": "Remeasured from source scan: 73"},
            headers=ver)
        assert patched.status_code == 200
        assert patched.json()["record"]["area"] == "73"

        assert client.post(f"/api/v1/reviews/{task_id}/complete", headers=ver).status_code == 200
        approved = client.post(f"/api/v1/records/{REC_78}/approve", json={}, headers=ver)
        assert approved.status_code == 200
        assert approved.json() == {"record_id": REC_78, "status": "APPROVED"}

        actions = [e["action"] for e in audits.list_for("land_record", REC_78)]
        assert actions == ["REVIEW_CREATED", "FIELD_CORRECTED", "REVIEW_COMPLETED", "RECORD_APPROVED"]

        correction = next(e for e in audits.list_for("land_record", REC_78) if e["action"] == "FIELD_CORRECTED")
        assert correction["old_value"] == {"area": "78"}
        assert correction["new_value"] == {"area": "73"}
        from tests.conftest import VER_ID
        assert correction["user_id"] == VER_ID
        assert records.corrections[-1]["old_value"] == "78"
        assert records.corrections[-1]["new_value"] == "73"
    finally:
        app.dependency_overrides.clear()
