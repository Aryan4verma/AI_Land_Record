"""Document processing endpoints (10 section 3).

POST /process accepts the job (202) and runs the pipeline as a
BackgroundTask — long OCR/LLM work never blocks the response. Progress is
observable via processing_jobs rows and GET /status. Only the pipeline
runner construction is injectable, so tests assert acceptance without
running AI.
"""
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Request

from ..auth.dependencies import require_role
from ..config import get_settings
from ..database import require_db
from ..demo.fixtures import DEMO_PIPELINE_VERSION, build_demo_stages
from ..documents.store import DocumentStore, get_document_store
from ..errors import AppError
from .pipeline import PipelineDeps, run_pipeline
from .schemas import ProcessAcceptedOut
from .stores import JobStore, get_job_store

router = APIRouter(prefix="/api/v1/documents", tags=["processing"])

REPROCESSABLE = ("UPLOADED", "FAILED", "VALIDATION_FAILED", "EXTRACTED")


EXECUTION_MODES = ("live", "demo")


def get_pipeline_runner(request: Request):
    """Build the background runner from live infrastructure.

    `mode` selects the source of the OCR/extraction stages only. Every later
    stage — validation, confidence, persistence, review, approval, audit — is
    the same code in both modes.
    """
    client = require_db(request)

    def run(job_id: str, document_id: str, user_id: str,
            mode: str = "live", checksum: str | None = None) -> None:
        deps = PipelineDeps(client=client, requesting_user_id=user_id)
        if mode == "demo":
            fixture, ocr_engine, ai_service = build_demo_stages(
                checksum or "", root=get_settings().demo_fixture_directory or None)
            deps = PipelineDeps(
                client=client, requesting_user_id=user_id,
                ocr_engine=ocr_engine, ai_service=ai_service,
                execution_mode="demo", fixture_id=str(fixture.get("fixture_id")),
            )
        run_pipeline(job_id, document_id, deps)

    return run


@router.post("/{document_id}/process", status_code=202, response_model=ProcessAcceptedOut)
def start_processing(
    document_id: UUID,
    request: Request,
    background_tasks: BackgroundTasks,
    mode: str = "live",
    user: dict = Depends(require_role("operator")),
    documents: DocumentStore = Depends(get_document_store),
    jobs: JobStore = Depends(get_job_store),
    run: object = Depends(get_pipeline_runner),
) -> dict:
    mode = (mode or "live").strip().lower()
    if mode not in EXECUTION_MODES:
        raise AppError(422, "UNKNOWN_EXECUTION_MODE",
                       "Processing mode must be 'live' or 'demo'.")
    if mode == "demo" and not get_settings().demo_mode:
        # Security must not depend on the UI hiding the selector.
        raise AppError(403, "DEMO_MODE_DISABLED",
                       "Demo processing is not enabled on this server.")

    document = documents.get(str(document_id))
    if document is None:
        raise AppError(404, "DOCUMENT_NOT_FOUND", "The requested document was not found.")
    status = document.get("processing_status")
    if status == "PROCESSING":
        raise AppError(409, "PROCESSING_IN_PROGRESS", "This document is already being processed.")
    if status in ("APPROVED", "REJECTED"):
        raise AppError(409, "DOCUMENT_FINALIZED", f"Documents in status {status} cannot be reprocessed.")
    if status not in REPROCESSABLE and status not in ("REVIEW_REQUIRED", "READY_FOR_APPROVAL"):
        raise AppError(409, "DOCUMENT_NOT_PROCESSABLE", f"Documents in status {status} cannot be processed.")
    if mode == "demo":
        # Resolve the fixture before claiming the document. An invalid demo
        # input must not create a claim that has no corresponding job.
        build_demo_stages(document.get("checksum") or "",
                          root=get_settings().demo_fixture_directory or None)

    # Atomic claim BEFORE creating the job. The status checks above are
    # advisory (they produce precise 409 messages); this is the one that
    # actually serializes concurrent requests, so a double-submit cannot
    # start two pipelines — and cannot spend a second AI call.
    if not documents.claim_for_processing(str(document["id"])):
        raise AppError(409, "PROCESSING_IN_PROGRESS", "This document is already being processed.")
    try:
        job = jobs.create_job({
            "document_id": str(document["id"]), "status": "PENDING",
            # Existing column, documented values: distinguishes the two paths in
            # the database without a migration.
            "pipeline_version": DEMO_PIPELINE_VERSION if mode == "demo" else "v1",
        })
    except Exception:
        # A claim without a job is not retryable through the normal API. Undo
        # only this request's claim; the conditional store operation protects
        # against releasing a claim that another worker has already advanced.
        # If the insert committed but its response was lost, keep PROCESSING:
        # releasing it would let a client retry and create a duplicate job.
        active_job_exists = True
        try:
            has_active = getattr(jobs, "has_active_job_for_document", None)
            if callable(has_active):
                active_job_exists = bool(has_active(str(document["id"])))
            else:
                active_job_exists = any(
                    item.get("status") in ("PENDING", "RUNNING")
                    for item in jobs.list_jobs_for_document(str(document["id"]))
                )
        except Exception:
            # Unknown job state is safer as a retained claim; startup
            # reconciliation can recover it once the database is reachable.
            pass
        release = getattr(documents, "release_processing_claim", None)
        if release is not None and not active_job_exists:
            try:
                release(str(document["id"]), status)
            except Exception:
                # Preserve the original job-creation error. Startup
                # reconciliation remains the last-resort recovery path.
                pass
        raise
    background_tasks.add_task(run, str(job["id"]), str(document["id"]), user["id"],  # type: ignore[arg-type]
                              mode, document.get("checksum"))
    return {"job_id": job["id"], "status": job["status"]}
