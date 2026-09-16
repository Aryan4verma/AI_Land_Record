"""Human-review workflow checks with faked persistence (no live DB)."""
import uuid
from datetime import datetime, timezone

import pytest

from app.reviews.service import review_needed
from app.reviews.stores import get_audit_store, get_record_store, get_review_store
from app.main import app
from tests.conftest import OP_ID, VER_ID

NOW = datetime.now(timezone.utc).isoformat()

# Fake record ids are real UUIDs: the API types ids as UUID (matching the
# database default gen_random_uuid()), so non-UUID ids correctly 422.
REC_OK = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
REC_BAD = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
REC_BLOCKED = "cccccccc-cccc-4ccc-8ccc-cccccccccccc"

REF_ROWS = [
    {"id": "d1", "reference_type": "district", "code": "DEMO-D01", "name": "Demo District",
     "parent_id": None, "version": "v1", "status": "active"},
    {"id": "t1", "reference_type": "tehsil", "code": "DEMO-T01", "name": "Demo Tehsil",
     "parent_id": "d1", "version": "v1", "status": "active"},
    {"id": "v1", "reference_type": "village", "code": "DEMO-V01", "name": "Demo Village",
     "parent_id": "t1", "version": "v1", "status": "active"},
]

BASE_RECORD = {
    "owner_name": "Ramesh Kumar",
    "father_or_spouse_name": "Suresh Kumar",
    "survey_number": "145/2",
    "khasra_number": "78",
    "khata_number": "123",
    "area": "2.45",
    "area_unit": "hectare",
    "village": "Demo Village",
    "tehsil": "Demo Tehsil",
    "district": "Demo District",
    "land_classification": "Agricultural",
    "mutation_number": "M-2024-0091",
    "registration_number": None,
    "record_date": "2024-03-15",
}


def _record(rec_id, **overrides):
    row = {"id": rec_id, "document_id": str(uuid.uuid4()), "status": "REVIEW_REQUIRED",
           "approved_by": None, "approved_at": None, **BASE_RECORD}
    row.update(overrides)
    return row


class FakeRecordStore:
    def __init__(self):
        self.records = {
            REC_OK: _record(REC_OK),
            REC_BAD: _record(REC_BAD, owner_name=None, area="0"),
            REC_BLOCKED: _record(REC_BLOCKED, area="0"),
        }
        self.extracted = {
            REC_BAD: [{"land_record_id": REC_BAD, "field_name": "area", "value": "0",
                         "confidence": 0.95, "extraction_status": "EXTRACTED"}],
        }
        self.validation_rows = {}
        self.corrections = []
        self.documents = {}
        for rec in self.records.values():
            self.documents[rec["document_id"]] = {"id": rec["document_id"], "file_name": "sample.pdf",
                                                  "processing_status": "VALIDATION_FAILED"}

    def get_record(self, record_id):
        return self.records.get(record_id)

    def update_record(self, record_id, patch):
        self.records[record_id].update(patch)
        return self.records[record_id]

    def list_extracted_fields(self, record_id):
        return self.extracted.get(record_id, [])

    def replace_validation_results(self, record_id, rows):
        self.validation_rows[record_id] = rows

    def save_correction(self, row):
        saved = {"id": str(uuid.uuid4()), **row}
        self.corrections.append(saved)
        return saved

    def get_document(self, document_id):
        return self.documents.get(document_id)

    def list_reference_rows(self):
        return REF_ROWS


class FakeReviewStore:
    def __init__(self):
        self.tasks = {}

    def create_task(self, row):
        saved = {"id": str(uuid.uuid4()), "assigned_to": None, "completed_at": None,
                 "created_at": NOW, **row}
        self.tasks[saved["id"]] = saved
        return saved

    def get_task(self, task_id):
        return self.tasks.get(task_id)

    def list_tasks(self, status, assigned_to):
        rows = list(self.tasks.values())
        if status:
            rows = [r for r in rows if r["status"] == status]
        if assigned_to:
            rows = [r for r in rows if r.get("assigned_to") == assigned_to]
        return sorted(rows, key=lambda r: r["created_at"], reverse=True)

    def update_task(self, task_id, patch):
        self.tasks[task_id].update(patch)
        return self.tasks[task_id]

    def open_tasks_for_record(self, record_id):
        return [t for t in self.tasks.values()
                if t["land_record_id"] == record_id and t["status"] in ("PENDING", "IN_REVIEW")]


class FakeAuditStore:
    def __init__(self):
        self.entries = []

    def append(self, entry):
        saved = {"id": str(uuid.uuid4()), "timestamp": NOW, "metadata": {},
                 "old_value": None, "new_value": None, **entry}
        self.entries.append(saved)
        return saved

    def list_for(self, entity_type, entity_id):
        return [e for e in self.entries if e["entity_type"] == entity_type and e["entity_id"] == entity_id]


@pytest.fixture()
def fakes():
    stores = (FakeRecordStore(), FakeReviewStore(), FakeAuditStore())
    app.dependency_overrides[get_record_store] = lambda: stores[0]
    app.dependency_overrides[get_review_store] = lambda: stores[1]
    app.dependency_overrides[get_audit_store] = lambda: stores[2]
    yield stores


def _token(client, email, password):
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]


def _op(client):
    return {"Authorization": f"Bearer {_token(client, 'op@example.com', 'op-pass')}"}


def _ver(client):
    return {"Authorization": f"Bearer {_token(client, 'ver@example.com', 'ver-pass')}"}


def _user(client):
    return {"Authorization": f"Bearer {_token(client, 'user@example.com', 'user-pass')}"}


def test_review_needed_helper():
    assert review_needed("REVIEW_REQUIRED", []) is True
    assert review_needed("BLOCKED", []) is True
    assert review_needed("READY_FOR_APPROVAL", ["area"]) is True
    assert review_needed("READY_FOR_APPROVAL", []) is False


def test_low_confidence_record_creates_review(client, fakes):
    _, _, audits = fakes
    response = client.post(
        "/api/v1/reviews",
        json={"land_record_id": REC_BAD, "reason": "7/14 fields flagged LOW", "priority": "HIGH"},
        headers=_op(client),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "PENDING" and body["priority"] == "HIGH"
    actions = [e["action"] for e in audits.list_for("land_record", REC_BAD)]
    assert "REVIEW_CREATED" in actions


def test_user_role_is_denied_every_privileged_review_action(client, fakes):
    """The read-only role must be refused the whole review/approval surface."""
    created = client.post("/api/v1/reviews", json={"land_record_id": REC_BAD, "reason": "r"},
                          headers=_op(client)).json()
    task_id = created["id"]
    user = _user(client)
    assert client.post("/api/v1/reviews", json={"land_record_id": REC_BAD, "reason": "r"},
                       headers=user).status_code == 403
    assert client.get("/api/v1/reviews", headers=user).status_code == 403
    assert client.get(f"/api/v1/reviews/{task_id}", headers=user).status_code == 403
    assert client.patch(f"/api/v1/reviews/{task_id}/fields/area",
                        json={"value": "2.45", "reason": "r"}, headers=user).status_code == 403
    assert client.post(f"/api/v1/reviews/{task_id}/complete", json={},
                       headers=user).status_code == 403
    assert client.post(f"/api/v1/records/{REC_BAD}/approve", json={},
                       headers=user).status_code == 403
    assert client.post(f"/api/v1/records/{REC_BAD}/reject", json={"reason": "r"},
                       headers=user).status_code == 403
    assert client.get(f"/api/v1/records/{REC_BAD}/audit", headers=user).status_code == 403


def test_operator_retains_former_verifier_capabilities(client, fakes):
    """Capability mapping: what `verifier` used to do, `operator` now does."""
    created = client.post("/api/v1/reviews", json={"land_record_id": REC_BAD, "reason": "r"},
                          headers=_op(client)).json()
    task_id = created["id"]
    op = _op(client)
    assert client.get("/api/v1/reviews", headers=op).status_code == 200
    assert client.get(f"/api/v1/reviews/{task_id}", headers=op).status_code == 200
    assert client.patch(f"/api/v1/reviews/{task_id}/fields/area",
                        json={"value": "2.45", "reason": "r"}, headers=op).status_code == 200
    assert client.get(f"/api/v1/records/{REC_BAD}/audit", headers=op).status_code == 200


def test_reviewer_corrects_field_and_validation_reruns(client, fakes):
    records, _, audits = fakes
    task_id = client.post("/api/v1/reviews", json={"land_record_id": REC_BAD, "reason": "r"},
                          headers=_op(client)).json()["id"]
    headers = _ver(client)
    response = client.patch(f"/api/v1/reviews/{task_id}/fields/area",
                            json={"value": "2.45", "reason": "Read 2.45 from source scan"},
                            headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["record"]["area"] == "2.45"
    assert body["task"]["status"] == "IN_REVIEW"
    assert not [i for i in body["validation"] if i["rule_id"] == "FMT_AREA_002"]
    assert records.corrections[-1]["old_value"] == "0"
    assert records.corrections[-1]["new_value"] == "2.45"
    assert records.corrections[-1]["changed_by"] == VER_ID
    assert "FIELD_CORRECTED" in [e["action"] for e in audits.list_for("land_record", REC_BAD)]
    assert records.validation_rows[REC_BAD]  # refreshed rows persisted


def test_correction_requires_reason_and_known_field(client, fakes):
    task_id = client.post("/api/v1/reviews", json={"land_record_id": REC_BAD, "reason": "r"},
                          headers=_op(client)).json()["id"]
    headers = _ver(client)
    assert client.patch(f"/api/v1/reviews/{task_id}/fields/area",
                        json={"value": "2.45", "reason": "   "}, headers=headers).status_code == 422
    assert client.patch(f"/api/v1/reviews/{task_id}/fields/nonexistent",
                        json={"value": "x", "reason": "r"}, headers=headers).status_code == 404


def test_review_detail_shows_record_extracted_validation_document(client, fakes):
    task_id = client.post("/api/v1/reviews", json={"land_record_id": REC_BAD, "reason": "r"},
                          headers=_op(client)).json()["id"]
    body = client.get(f"/api/v1/reviews/{task_id}", headers=_ver(client)).json()
    assert body["record"]["id"] == REC_BAD
    assert body["extracted_fields"][0]["field_name"] == "area"
    assert any(i["rule_id"] == "FMT_AREA_002" for i in body["validation"])
    assert body["verdict"] == "BLOCKED" and body["approval_blocked"] is True
    assert body["document"]["file_name"] == "sample.pdf"


def test_approval_succeeds_when_valid_with_full_audit_chain(client, fakes):
    _, _, audits = fakes
    headers = _ver(client)
    task_id = client.post("/api/v1/reviews", json={"land_record_id": REC_BAD, "reason": "r"},
                          headers=_op(client)).json()["id"]
    client.patch(f"/api/v1/reviews/{task_id}/fields/area",
                 json={"value": "2.45", "reason": "fix"}, headers=headers)
    client.patch(f"/api/v1/reviews/{task_id}/fields/owner_name",
                 json={"value": "Ramesh Kumar", "reason": "fix"}, headers=headers)
    assert client.post(f"/api/v1/reviews/{task_id}/complete", headers=headers).json()["status"] == "COMPLETED"
    approved = client.post(f"/api/v1/records/{REC_BAD}/approve", json={"reason": "verified"}, headers=headers)
    assert approved.status_code == 200
    assert approved.json() == {"record_id": REC_BAD, "status": "APPROVED"}
    actions = [e["action"] for e in audits.list_for("land_record", REC_BAD)]
    for expected in ("REVIEW_CREATED", "FIELD_CORRECTED", "REVIEW_COMPLETED", "RECORD_APPROVED"):
        assert expected in actions
    approval = next(e for e in audits.list_for("land_record", REC_BAD) if e["action"] == "RECORD_APPROVED")
    assert approval["old_value"] == {"status": "REVIEW_REQUIRED"}
    assert approval["new_value"] == {"status": "APPROVED"}
    assert client.post(f"/api/v1/records/{REC_BAD}/approve", json={}, headers=headers).status_code == 409


def test_approval_blocked_while_required_issues_remain(client, fakes):
    _, _, audits = fakes
    headers = _ver(client)
    response = client.post(f"/api/v1/records/{REC_BLOCKED}/approve", json={}, headers=headers)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "APPROVAL_BLOCKED"
    assert "FMT_AREA_002" in response.json()["error"]["message"]
    assert not [e for e in audits.list_for("land_record", REC_BLOCKED) if e["action"] == "RECORD_APPROVED"]


def test_reject_requires_reason_and_cancels_open_reviews(client, fakes):
    _, reviews, audits = fakes
    headers = _ver(client)
    task_id = client.post("/api/v1/reviews", json={"land_record_id": REC_BAD, "reason": "r"},
                          headers=_op(client)).json()["id"]
    assert client.post(f"/api/v1/records/{REC_BAD}/reject", json={"reason": "   "},
                       headers=headers).status_code == 422
    rejected = client.post(f"/api/v1/records/{REC_BAD}/reject",
                           json={"reason": "Document illegible"}, headers=headers)
    assert rejected.json()["status"] == "REJECTED"
    assert reviews.get_task(task_id)["status"] == "CANCELLED"
    entry = next(e for e in audits.list_for("land_record", REC_BAD) if e["action"] == "RECORD_REJECTED")
    assert entry["metadata"]["cancelled_reviews"] == [task_id]


def test_duplicate_complete_rejected_and_correct_on_closed_rejected(client, fakes):
    """Phase 1E: repeated state-changing requests must not corrupt data —
    completing twice yields REVIEW_CLOSED (no second audit entry, timestamp
    unchanged), and correcting a closed review is rejected without mutation."""
    _, reviews, audits = fakes
    headers = _ver(client)
    task_id = client.post("/api/v1/reviews", json={"land_record_id": REC_BAD, "reason": "r"},
                          headers=_op(client)).json()["id"]
    first = client.post(f"/api/v1/reviews/{task_id}/complete", headers=headers)
    assert first.status_code == 200
    completed_at = reviews.get_task(task_id)["completed_at"]
    audits_before = len(audits.list_for("land_record", REC_BAD))

    second = client.post(f"/api/v1/reviews/{task_id}/complete", headers=headers)
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "REVIEW_CLOSED"
    assert reviews.get_task(task_id)["completed_at"] == completed_at
    assert len(audits.list_for("land_record", REC_BAD)) == audits_before

    corrected = client.patch(f"/api/v1/reviews/{task_id}/fields/area",
                             json={"value": "9.99", "reason": "late edit"}, headers=headers)
    assert corrected.status_code == 409
    assert corrected.json()["error"]["code"] == "REVIEW_CLOSED"
