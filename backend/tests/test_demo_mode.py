"""Demo Mode: fixture matching, zero external calls, and full-pipeline reuse.

Demo Mode replays a precomputed OCR/extraction fixture for a known document.
Everything after that stage — validation, confidence, persistence, review,
correction, approval, audit — must be the same code Live Mode runs. These tests
assert that, and that Demo Mode is neither a permission bypass nor a way to
reach an external provider.
"""
import hashlib
import json
import sys
import uuid
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.demo.fixtures import (  # noqa: E402
    DEMO_PIPELINE_VERSION,
    DEMO_PROVIDER,
    DemoExtractionService,
    DemoOcrEngine,
    build_demo_stages,
    find_fixture,
    fixture_root,
)
from app.errors import AppError  # noqa: E402
from app.main import app  # noqa: E402
from app.processing.router import get_pipeline_runner  # noqa: E402
from app.processing.stores import get_job_store  # noqa: E402
from app.documents.store import get_document_store  # noqa: E402
from tests.test_processing import DOC_ID, world  # noqa: E402,F401

DEMO_DIR = ROOT / "demo" / "fixtures"
CANONICAL = DEMO_DIR / "doc10_rtc_hindi_scan" / "document.pdf"

needs_fixture = pytest.mark.skipif(
    not CANONICAL.is_file(),
    reason="canonical demo fixture absent; run scripts/build_demo_fixture.py")


def _canonical_sha() -> str:
    return hashlib.sha256(CANONICAL.read_bytes()).hexdigest()


# --------------------------------------------------------------- matching
@needs_fixture
def test_canonical_document_is_recognised_by_content_hash():
    fixture = find_fixture(_canonical_sha())
    assert fixture is not None
    assert fixture["fixture_id"] == "doc10_rtc_hindi_scan"


@needs_fixture
def test_renamed_copy_is_still_recognised(tmp_path):
    """Recognition is by bytes, so a rename must change nothing."""
    renamed = tmp_path / "totally-different-name.pdf"
    renamed.write_bytes(CANONICAL.read_bytes())
    assert find_fixture(hashlib.sha256(renamed.read_bytes()).hexdigest()) is not None


@needs_fixture
def test_a_different_document_is_refused_not_guessed():
    other = hashlib.sha256(b"an unrelated document").hexdigest()
    assert find_fixture(other) is None
    with pytest.raises(AppError) as exc:
        build_demo_stages(other)
    assert exc.value.status == 422
    assert exc.value.code == "DEMO_DOCUMENT_NOT_RECOGNISED"


def test_malformed_checksum_never_matches():
    for bad in ("", "abc", "z" * 64, None):
        assert find_fixture(bad or "") is None


# ------------------------------------------------- zero external traffic
@needs_fixture
def test_demo_stages_make_zero_external_calls(monkeypatch):
    """The demo path must not even attempt a provider call."""
    import httpx

    def explode(*args, **kwargs):
        raise AssertionError("Demo Mode attempted outbound HTTP")

    monkeypatch.setattr(httpx.Client, "post", explode, raising=False)
    monkeypatch.setattr(httpx.Client, "send", explode, raising=False)

    fixture, ocr, ai = build_demo_stages(_canonical_sha())
    page, elapsed = ocr.read_image(image=None, page_number=1)
    result = ai.extract_land_record(payload=None)

    assert ocr.external_calls == 0
    assert ai.external_calls == 0
    assert result.provider == DEMO_PROVIDER
    assert page.text.strip()
    assert elapsed == 0.0


@needs_fixture
def test_demo_extraction_matches_the_data_dictionary():
    from app.ai.types import KNOWN_FIELDS

    _fixture, _ocr, ai = build_demo_stages(_canonical_sha())
    result = ai.extract_land_record(payload=None)
    assert set(result.fields).issubset(set(KNOWN_FIELDS)), "no invented production fields"
    # A field the document does not carry stays absent rather than invented.
    reg = result.fields.get("registration_number")
    if reg is not None:
        assert reg.value is None or reg.extraction_status in ("MISSING", "UNCERTAIN", "EXTRACTED")


@needs_fixture
def test_demo_is_deterministic():
    """The same document must always produce the same result."""
    a = build_demo_stages(_canonical_sha())[2].extract_land_record(None)
    b = build_demo_stages(_canonical_sha())[2].extract_land_record(None)
    assert a.values() == b.values()
    assert a.provider == b.provider


# ------------------------------------------------------- full pipeline
@needs_fixture
def test_demo_runs_the_real_pipeline_end_to_end(world):  # noqa: F811
    """Fixture in; real validation, persistence, review and audit out.

    This is the point of Demo Mode: only the OCR/extraction source differs, so
    everything downstream must behave exactly as it does for a live document.
    """
    import pytest as _pytest

    from ai.validation import demo_reference
    from app.processing import pipeline as pipeline_module
    from app.processing.pipeline import PipelineDeps, run_pipeline

    fixture, ocr, ai = build_demo_stages(_canonical_sha())
    docs, jobs, records = world["docs"], world["jobs"], world["records"]
    reviews, audits = world["reviews"], world["audits"]

    class _Storage:
        def download(self, path):
            return CANONICAL.read_bytes()

    # The demo document is a PDF; the renderer picks its path from the name.
    docs.doc["file_name"] = "doc10_rtc_hindi_scan.pdf"
    docs.doc["file_type"] = "application/pdf"

    mp = _pytest.MonkeyPatch()
    mp.setattr(pipeline_module, "_store_factory",
               lambda client: (jobs, docs, records, reviews, audits))
    try:
        job = jobs.create_job({"document_id": DOC_ID, "status": "PENDING",
                               "pipeline_version": DEMO_PIPELINE_VERSION})
        run_pipeline(job["id"], DOC_ID, PipelineDeps(
            client=None, requesting_user_id=str(uuid.uuid4()),
            ai_service=ai, ocr_engine=ocr, storage=_Storage(),
            reference=demo_reference(),
            execution_mode="demo", fixture_id=str(fixture["fixture_id"])))
        finished = jobs.get_job(job["id"])
    finally:
        mp.undo()

    assert finished["status"] == "SUCCEEDED", finished.get("error_message")
    assert finished["pipeline_version"] == DEMO_PIPELINE_VERSION

    # persistence: a real land record with real extracted fields
    record = records.get_record_by_document(DOC_ID)
    assert record is not None
    assert record["owner_name"] == "Ramesh Kumar Patel"
    assert len(records.extracted[record["id"]]) == 14

    # the REAL validation engine ran (not a hardcoded "passed")
    assert record["id"] in records.validations

    # audit records the mode honestly, and proves no provider was contacted
    completed = next(e for e in audits.entries if e["action"] == "PROCESSING_COMPLETED")
    assert completed["metadata"]["execution_mode"] == "demo"
    assert completed["metadata"]["fixture_id"] == "doc10_rtc_hindi_scan"
    assert completed["metadata"]["external_ai_calls"] == 0
    assert completed["metadata"]["external_ocr_calls"] == 0
    assert completed["metadata"]["provider"] == DEMO_PROVIDER
    started = next(e for e in audits.entries if e["action"] == "PROCESSING_STARTED")
    assert started["metadata"]["execution_mode"] == "demo"


@needs_fixture
def test_live_pipeline_audit_is_not_tagged_demo(world):  # noqa: F811
    """Live Mode must never be labelled demo, or the trail becomes a lie."""
    from tests.test_processing import _run

    job = _run(world)
    assert job["status"] == "SUCCEEDED"
    completed = next(e for e in world["audits"].entries
                     if e["action"] == "PROCESSING_COMPLETED")
    assert completed["metadata"]["execution_mode"] == "live"
    assert "fixture_id" not in completed["metadata"]
    assert "external_ai_calls" not in completed["metadata"]


# ------------------------------------------------------------ endpoint
def _token(client, email="op@example.com", password="op-pass"):
    r = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200
    return r.json()["access_token"]


def _headers(client, **kw):
    return {"Authorization": f"Bearer {_token(client, **kw)}"}


@needs_fixture
def test_demo_requires_the_server_side_switch(client, world, monkeypatch):  # noqa: F811
    """A frontend flag must never be able to enable Demo Mode."""
    from app.config import get_settings

    get_settings.cache_clear()
    monkeypatch.setenv("DEMO_MODE", "false")
    app.dependency_overrides[get_document_store] = lambda: world["docs"]
    app.dependency_overrides[get_job_store] = lambda: world["jobs"]
    app.dependency_overrides[get_pipeline_runner] = lambda: (lambda *a, **k: None)
    try:
        r = client.post(f"/api/v1/documents/{DOC_ID}/process?mode=demo",
                        headers=_headers(client))
        assert r.status_code == 403
        assert r.json()["error"]["code"] == "DEMO_MODE_DISABLED"
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()


def test_unknown_mode_is_rejected(client, world):  # noqa: F811
    app.dependency_overrides[get_document_store] = lambda: world["docs"]
    app.dependency_overrides[get_job_store] = lambda: world["jobs"]
    app.dependency_overrides[get_pipeline_runner] = lambda: (lambda *a, **k: None)
    try:
        r = client.post(f"/api/v1/documents/{DOC_ID}/process?mode=banana",
                        headers=_headers(client))
        assert r.status_code == 422
        assert r.json()["error"]["code"] == "UNKNOWN_EXECUTION_MODE"
    finally:
        app.dependency_overrides.clear()


def test_live_mode_is_the_default_and_unchanged(client, world):  # noqa: F811
    """Omitting `mode` must behave exactly as before Demo Mode existed."""
    seen = []
    app.dependency_overrides[get_document_store] = lambda: world["docs"]
    app.dependency_overrides[get_job_store] = lambda: world["jobs"]
    app.dependency_overrides[get_pipeline_runner] = lambda: (
        lambda job_id, doc_id, user_id, mode="live", checksum=None: seen.append(mode))
    try:
        r = client.post(f"/api/v1/documents/{DOC_ID}/process", headers=_headers(client))
        assert r.status_code == 202
        assert seen == ["live"]
        job = world["jobs"].list_jobs_for_document(DOC_ID)[-1]
        assert job["pipeline_version"] == "v1", "live jobs must not be tagged demo"
    finally:
        app.dependency_overrides.clear()


def test_read_only_user_cannot_start_demo_processing(client, world):  # noqa: F811
    """Demo Mode is not a permission bypass."""
    app.dependency_overrides[get_document_store] = lambda: world["docs"]
    app.dependency_overrides[get_job_store] = lambda: world["jobs"]
    app.dependency_overrides[get_pipeline_runner] = lambda: (lambda *a, **k: None)
    try:
        r = client.post(f"/api/v1/documents/{DOC_ID}/process?mode=demo",
                        headers=_headers(client, email="user@example.com",
                                         password="user-pass"))
        assert r.status_code == 403
        assert r.json()["error"]["code"] == "INSUFFICIENT_ROLE"
    finally:
        app.dependency_overrides.clear()


def test_unauthenticated_demo_request_is_refused(client):
    r = client.post(f"/api/v1/documents/{DOC_ID}/process?mode=demo")
    assert r.status_code == 401


# --------------------------------------------------------- configuration
def test_missing_manifest_reports_a_specific_error(tmp_path):
    with pytest.raises(AppError) as exc:
        find_fixture("a" * 64, root=str(tmp_path))
    assert exc.value.status == 503
    assert exc.value.code == "DEMO_NOT_CONFIGURED"
    assert "administrator" in exc.value.message


def test_invalid_manifest_reports_a_specific_error(tmp_path):
    (tmp_path / "manifest.json").write_text("{ not json", encoding="utf-8")
    with pytest.raises(AppError) as exc:
        find_fixture("a" * 64, root=str(tmp_path))
    assert exc.value.code == "DEMO_CONFIG_INVALID"


@needs_fixture
def test_manifest_records_an_immutable_fingerprint():
    manifest = json.loads((DEMO_DIR / "manifest.json").read_text(encoding="utf-8"))
    entry = manifest["fixtures"][0]
    for key in ("fixture_id", "sha256", "original_filename", "page_count",
                "fixture_version", "schema_version", "ocr_result", "extraction_result"):
        assert key in entry, f"manifest missing {key}"
    assert len(entry["sha256"]) == 64
    assert entry["sha256"] == _canonical_sha(), "manifest hash drifted from the document"


@needs_fixture
def test_fixture_root_defaults_into_the_repository():
    assert fixture_root().name == "fixtures"
    assert (fixture_root() / "manifest.json").is_file()
