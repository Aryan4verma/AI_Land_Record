"""Processing pipeline checks with fully stubbed stages (no OCR/AI/network)."""
import io
import sys
import uuid
from pathlib import Path

import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ai.ocr.base import OcrLine, OcrPage  # noqa: E402
from ai.validation import demo_reference  # noqa: E402
from app.ai.errors import ProviderRateLimitError  # noqa: E402
from app.ai.types import ExtractionResult, FieldResult  # noqa: E402
from app.main import app  # noqa: E402
from app.processing import pipeline as pipeline_module  # noqa: E402
from app.processing.pipeline import PipelineDeps, run_pipeline  # noqa: E402
from app.processing.router import get_pipeline_runner  # noqa: E402
from app.processing.stores import get_job_store  # noqa: E402
from app.documents.store import get_document_store  # noqa: E402

NOW = "2026-09-04T00:00:00+00:00"
DOC_ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"

CLEAN_VALUES = {
    "owner_name": "Ramesh Kumar", "father_or_spouse_name": "Suresh Kumar",
    "survey_number": "145/2", "khasra_number": "78", "khata_number": "123",
    "area": "2.45", "area_unit": "hectare", "village": "Demo Village",
    "tehsil": "Demo Tehsil", "district": "Demo District",
    "land_classification": "Agricultural", "mutation_number": "M-2024-0091",
    "registration_number": None, "record_date": "2024-03-15",
}
DIRTY_VALUES = dict(CLEAN_VALUES, area="0", owner_name=None)


def _png_bytes() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (64, 64), "white").save(buffer, format="PNG")
    return buffer.getvalue()


def _page(text="Owner Name: Ramesh Kumar", conf=0.95):
    return OcrPage(page_number=1, text=text, confidence=conf,
                   lines=[OcrLine(text=text, confidence=conf, box=[0.0, 0.0, 10.0, 10.0])],
                   width=64, height=64)


def _result(values):
    return ExtractionResult(
        fields={k: FieldResult(k, v, 0.9, None, "EXTRACTED" if v is not None else "MISSING")
                for k, v in values.items()},
        provider="stub", model="stub-model", prompt_version="v1",
        schema_version="v1", elapsed_seconds=0.1, raw_response="{}")


class StubOCR:
    def __init__(self, pages=None, fail=False):
        self._pages = pages if pages is not None else [_page()]
        self.fail = fail

    def read_image(self, image, page_number=1):
        if self.fail:
            raise RuntimeError("ocr exploded")
        return self._pages[page_number - 1], 0.01


class StubAI:
    def __init__(self, values=None, error=None):
        self._values = values if values is not None else CLEAN_VALUES
        self.error = error

    def extract_land_record(self, payload):
        if self.error:
            raise self.error
        return _result(self._values)


class StubStorage:
    def __init__(self, data=None, fail=False):
        self._data = data if data is not None else _png_bytes()
        self.fail = fail

    def download(self, path):
        if self.fail:
            raise RuntimeError("storage down")
        return self._data

    def upload(self, path, data, content_type):
        return None

    def remove(self, path):
        return None


class FakeDocs:
    def __init__(self, status="UPLOADED"):
        self.doc = {"id": DOC_ID, "file_name": "sample.png", "file_type": "image/png",
                    "storage_path": "documents/x/y.png", "processing_status": status,
                    "document_type": None, "language": "en"}

    def get(self, document_id):
        return self.doc if document_id == DOC_ID else None

    def create(self, row):
        return row

    def update_status(self, document_id, status):
        self.doc["processing_status"] = status
        return self.doc

    def claim_for_processing(self, document_id):
        # Mirrors `UPDATE ... WHERE id = ? AND processing_status <> 'PROCESSING'`:
        # only the first caller observes a non-PROCESSING row and wins.
        if self.doc["processing_status"] == "PROCESSING":
            return False
        self.doc["processing_status"] = "PROCESSING"
        return True


class FakeJobs:
    def __init__(self):
        self.jobs = {}

    def create_job(self, row):
        saved = {"id": str(uuid.uuid4()), "started_at": None, "completed_at": None,
                 "error_code": None, "error_message": None, **row}
        self.jobs[saved["id"]] = saved
        return saved

    def get_job(self, job_id):
        return self.jobs.get(job_id)

    def update_job(self, job_id, patch):
        self.jobs[job_id].update(patch)
        return self.jobs[job_id]

    def list_jobs_for_document(self, document_id):
        return [j for j in self.jobs.values() if j["document_id"] == document_id]

    def mark_stale_failed(self):
        count = 0
        for job in self.jobs.values():
            if job["status"] in ("PENDING", "RUNNING"):
                job.update({"status": "FAILED", "error_code": "SERVER_RESTARTED"})
                count += 1
        return count


class FakeRecords:
    def __init__(self):
        self.records = {}
        self.extracted = {}
        self.validations = {}
        self.ocr_by_doc = {}

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
        return self.extracted.get(record_id, [])

    def replace_extracted_fields(self, record_id, rows):
        self.extracted[record_id] = rows

    def replace_validation_results(self, record_id, rows):
        self.validations[record_id] = rows

    def list_validation_results(self, record_id):
        return self.validations.get(record_id, [])

    def replace_ocr_results(self, document_id, rows):
        self.ocr_by_doc[document_id] = list(rows)

    def list_record_summaries(self):
        return [{"id": r["id"], "document_id": r["document_id"], "survey_number": r.get("survey_number"),
                 "village": r.get("village"), "owner_name": r.get("owner_name")}
                for r in self.records.values()]

    def save_correction(self, row):
        return {"id": str(uuid.uuid4()), **row}

    def get_document(self, document_id):
        return None

    def list_reference_rows(self):
        return []


class FakeReviews:
    def __init__(self):
        self.tasks = {}

    def create_task(self, row):
        saved = {"id": str(uuid.uuid4()), "assigned_to": None, "completed_at": None, **row}
        self.tasks[saved["id"]] = saved
        return saved

    def get_task(self, task_id):
        return self.tasks.get(task_id)

    def list_tasks(self, status, assigned_to):
        return list(self.tasks.values())

    def update_task(self, task_id, patch):
        self.tasks[task_id].update(patch)
        return self.tasks[task_id]

    def open_tasks_for_record(self, record_id):
        return [t for t in self.tasks.values()
                if t["land_record_id"] == record_id and t["status"] in ("PENDING", "IN_REVIEW")]


class FakeAudits:
    def __init__(self):
        self.entries = []

    def append(self, entry):
        saved = {"id": str(uuid.uuid4()), **entry}
        self.entries.append(saved)
        return saved

    def list_for(self, entity_type, entity_id):
        return self.entries


@pytest.fixture()
def world():
    return {"docs": FakeDocs(), "jobs": FakeJobs(), "records": FakeRecords(),
            "reviews": FakeReviews(), "audits": FakeAudits()}


def _run(world, values=CLEAN_VALUES, ocr=None, ai_error=None, storage_fail=False):
    docs, jobs, records, reviews, audits = (world["docs"], world["jobs"], world["records"],
                                            world["reviews"], world["audits"])
    real_factory = pipeline_module._store_factory
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(pipeline_module, "_store_factory", lambda client: (jobs, docs, records, reviews, audits))
    try:
        job = jobs.create_job({"document_id": DOC_ID, "status": "PENDING", "pipeline_version": "v1"})
        run_pipeline(job["id"], DOC_ID, PipelineDeps(
            client=None, requesting_user_id="user-1",
            ai_service=StubAI(values, ai_error), ocr_engine=ocr or StubOCR(),
            storage=StubStorage(fail=storage_fail), reference=demo_reference()))
        return jobs.get_job(job["id"])
    finally:
        monkeypatch.undo()


def test_pipeline_success_creates_record_without_review(world):
    job = _run(world)
    assert job["status"] == "SUCCEEDED"
    assert world["docs"].doc["processing_status"] == "READY_FOR_APPROVAL"
    record = world["records"].get_record_by_document(DOC_ID)
    assert record["status"] == "READY_FOR_APPROVAL"
    assert record["owner_name"] == "Ramesh Kumar"
    assert len(world["records"].extracted[record["id"]]) == 14
    assert world["reviews"].tasks == {}
    actions = [e["action"] for e in world["audits"].entries]
    assert actions == ["PROCESSING_STARTED", "PROCESSING_COMPLETED"]


def test_pipeline_dirty_values_create_review_task(world):
    job = _run(world, values=DIRTY_VALUES)
    assert job["status"] == "SUCCEEDED"
    # area "0" is a FAIL -> BLOCKED verdict -> document VALIDATION_FAILED,
    # record stays REVIEW_REQUIRED, HIGH-priority review auto-created.
    assert world["docs"].doc["processing_status"] == "VALIDATION_FAILED"
    tasks = list(world["reviews"].tasks.values())
    assert len(tasks) == 1 and tasks[0]["status"] == "PENDING" and tasks[0]["priority"] == "HIGH"
    assert "BLOCKED" in tasks[0]["reason"]


def test_pipeline_ocr_failure_marks_failed(world):
    job = _run(world, ocr=StubOCR(fail=True))
    assert job["status"] == "FAILED" and job["error_code"] == "OCR_FAILED"
    assert world["docs"].doc["processing_status"] == "FAILED"
    assert world["records"].records == {}


def test_pipeline_provider_failure_classified(world):
    job = _run(world, ai_error=ProviderRateLimitError("stub", "slow down"))
    assert job["status"] == "FAILED" and job["error_code"] == "PROVIDER_RATE_LIMITED"


def test_pipeline_storage_failure(world):
    job = _run(world, storage_fail=True)
    assert job["status"] == "FAILED" and job["error_code"] == "STORAGE_DOWNLOAD_FAILED"


def _token(client, email="op@example.com", password="op-pass"):
    return client.post("/api/v1/auth/login", json={"email": email, "password": password}).json()["access_token"]


def test_concurrent_process_requests_start_only_one_pipeline(client, world):
    """STEP 5 found two live jobs (6b1d1fe7 / f509d617) for one document.

    The old guard read documents.processing_status, but PROCESSING was only set
    later by the background task, so a second request ~1s behind still passed
    and spent a second AI call. The claim is now atomic, so exactly one of two
    back-to-back requests may start a pipeline.
    """
    docs, jobs = world["docs"], world["jobs"]
    app.dependency_overrides[get_document_store] = lambda: docs
    app.dependency_overrides[get_job_store] = lambda: jobs
    # Background work is irrelevant here: the point is the claim, not the run.
    app.dependency_overrides[get_pipeline_runner] = lambda: (lambda *a, **k: None)
    try:
        headers = {"Authorization": f"Bearer {_token(client)}"}
        first = client.post(f"/api/v1/documents/{DOC_ID}/process", headers=headers)
        second = client.post(f"/api/v1/documents/{DOC_ID}/process", headers=headers)

        assert first.status_code == 202
        assert second.status_code == 409
        assert second.json()["error"]["code"] == "PROCESSING_IN_PROGRESS"
        # Exactly one job — the second request must not have created one.
        assert len(jobs.list_jobs_for_document(DOC_ID)) == 1
        assert docs.doc["processing_status"] == "PROCESSING"
    finally:
        app.dependency_overrides.clear()


def test_claim_is_released_for_retry_after_failure(client, world):
    """A failed run must stay reprocessable: the claim is not a permanent lock."""
    docs, jobs = world["docs"], world["jobs"]
    docs.doc["processing_status"] = "FAILED"
    app.dependency_overrides[get_document_store] = lambda: docs
    app.dependency_overrides[get_job_store] = lambda: jobs
    app.dependency_overrides[get_pipeline_runner] = lambda: (lambda *a, **k: None)
    try:
        headers = {"Authorization": f"Bearer {_token(client)}"}
        assert client.post(f"/api/v1/documents/{DOC_ID}/process",
                           headers=headers).status_code == 202
    finally:
        app.dependency_overrides.clear()


def test_process_endpoint_accepts_and_runs_background(client, world, monkeypatch):
    calls = []

    def fake_run(job_id, document_id, user_id, mode="live", checksum=None):
        calls.append((job_id, document_id, user_id, mode))

    app.dependency_overrides[get_document_store] = lambda: world["docs"]
    app.dependency_overrides[get_job_store] = lambda: world["jobs"]
    app.dependency_overrides[get_pipeline_runner] = lambda: fake_run
    try:
        headers = {"Authorization": f"Bearer {_token(client)}"}
        response = client.post(f"/api/v1/documents/{DOC_ID}/process", headers=headers)
        assert response.status_code == 202
        assert response.json()["status"] == "PENDING"
        assert len(calls) == 1 and calls[0][1] == DOC_ID and calls[0][2] != ""
    finally:
        app.dependency_overrides.clear()


def test_process_endpoint_guards(client, world):
    app.dependency_overrides[get_document_store] = lambda: world["docs"]
    app.dependency_overrides[get_job_store] = lambda: world["jobs"]
    app.dependency_overrides[get_pipeline_runner] = lambda: (lambda *a: None)
    try:
        headers = {"Authorization": f"Bearer {_token(client)}"}
        assert client.post("/api/v1/documents/00000000-0000-4000-8000-000000000000/process",
                           headers=headers).status_code == 404
        assert client.post(f"/api/v1/documents/{DOC_ID}/process").status_code == 401
        world["docs"].doc["processing_status"] = "PROCESSING"
        assert client.post(f"/api/v1/documents/{DOC_ID}/process", headers=headers).status_code == 409
        world["docs"].doc["processing_status"] = "APPROVED"
        assert client.post(f"/api/v1/documents/{DOC_ID}/process", headers=headers).status_code == 409
    finally:
        app.dependency_overrides.clear()


def test_reprocess_replaces_ocr_rows_without_conflict(world):
    first = _run(world)
    assert first["status"] == "SUCCEEDED"
    record = world["records"].get_record_by_document(DOC_ID)
    assert len(world["records"].ocr_by_doc[DOC_ID]) == 1
    second = _run(world)  # retry/reprocess path
    assert second["status"] == "SUCCEEDED"
    assert len(world["records"].ocr_by_doc[DOC_ID]) == 1  # replaced, not duplicated
    assert world["records"].get_record_by_document(DOC_ID)["id"] == record["id"]  # same record updated


def test_pipeline_duplicate_detection_flags_review(world):
    world["records"].records["other"] = {
        "id": "other", "document_id": "OTHER-DOC", "survey_number": "145/2",
        "village": "Demo Village", "owner_name": "Ramesh Kumar",
    }
    job = _run(world)  # CLEAN_VALUES match the other document's parcel
    assert job["status"] == "SUCCEEDED"
    assert world["docs"].doc["processing_status"] == "REVIEW_REQUIRED"
    record = world["records"].get_record_by_document(DOC_ID)
    rule_ids = [row["rule_id"] for row in world["records"].validations[record["id"]]]
    assert "DUP_CANDIDATE_001" in rule_ids
    tasks = list(world["reviews"].tasks.values())
    assert len(tasks) == 1 and tasks[0]["status"] == "PENDING"


def test_processing_completed_audit_carries_versions(world):
    _run(world)
    entries = [e for e in world["audits"].entries if e["action"] == "PROCESSING_COMPLETED"]
    assert len(entries) == 1
    metadata = entries[0]["metadata"]
    assert metadata["provider"] == "stub" and metadata["model"] == "stub-model"
    assert metadata["prompt_version"] == "v1" and metadata["schema_version"] == "v1"
    assert metadata["verdict"] == "READY_FOR_APPROVAL"


def test_mark_stale_failed_reconciles(world):
    jobs = world["jobs"]
    running = jobs.create_job({"document_id": DOC_ID, "status": "RUNNING", "pipeline_version": "v1"})
    pending = jobs.create_job({"document_id": DOC_ID, "status": "PENDING", "pipeline_version": "v1"})
    done = jobs.create_job({"document_id": DOC_ID, "status": "SUCCEEDED", "pipeline_version": "v1"})
    assert jobs.mark_stale_failed() == 2
    assert jobs.get_job(running["id"])["status"] == "FAILED"
    assert jobs.get_job(running["id"])["error_code"] == "SERVER_RESTARTED"
    assert jobs.get_job(pending["id"])["status"] == "FAILED"
    assert jobs.get_job(done["id"])["status"] == "SUCCEEDED"
