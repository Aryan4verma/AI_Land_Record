"""Document pipeline: download -> OCR -> extract -> validate -> persist.

Runs as a FastAPI BackgroundTask (long AI work stays off the request
path); progress is observable through processing_jobs + document status.
Every stage failure marks the job FAILED with a classified error_code and
leaves the document retryable. Stage functions are injected, so tests run
the whole pipeline with stub OCR/AI and no network.
"""
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _ensure_repo_root() -> None:
    root = Path(__file__).resolve().parents[3]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))


_ensure_repo_root()

from ai.validation import (  # noqa: E402
    duplicate_issue,
    find_duplicates,
    normalize_record,
    record_verdict,
    validate_record,
)

from ..ai.errors import ProviderError
from ..documents.storage_backend import SupabaseStorageBackend
from ..errors import AppError
from ..records.typed_values import coerce_typed_columns
from ..documents.store import SupabaseDocumentStore
from ..logging_config import get_logger
from ..reviews.service import build_reference
from ..reviews.stores import SupabaseAuditStore, SupabaseRecordStore, SupabaseReviewStore

log = get_logger(__name__)

PIPELINE_VERSION = "v1"


class PipelineFail(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass
class PipelineDeps:
    client: Any
    requesting_user_id: str
    ai_service: Any = None  # default: real AIService (get_ai_service)
    ocr_engine: Any = None  # default: real TesseractOcrEngine
    storage: Any = None  # default: SupabaseStorageBackend
    reference: Any = None  # default: built from DB reference rows
    dpi: int = 300
    execution_mode: str = "live"  # "live" | "demo" — recorded in the audit trail
    fixture_id: str | None = None  # set only in demo mode


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _audit(audits: Any, document_id: str, user_id: str, action: str, metadata: dict) -> None:
    audits.append(
        {"user_id": user_id, "entity_type": "document", "entity_id": document_id,
         "action": action, "metadata": metadata}
    )


def _bucket() -> str:
    from ..config import get_settings

    return get_settings().storage_bucket


def _store_factory(client: Any):
    """Build live stores. Tests monkeypatch this to inject fakes."""
    from .stores import SupabaseJobStore

    return (
        SupabaseJobStore(client),
        SupabaseDocumentStore(client),
        SupabaseRecordStore(client),
        SupabaseReviewStore(client),
        SupabaseAuditStore(client),
    )


def run_pipeline(job_id: str, document_id: str, deps: PipelineDeps) -> None:
    """Execute every stage. Never raises — all outcomes land in the DB."""
    jobs, documents, records, reviews, audits = _store_factory(deps.client)
    try:
        _run(job_id, document_id, deps, jobs, documents, records, reviews, audits)
    except PipelineFail as exc:
        log.exception(
            "pipeline failed: job_id=%s document_id=%s code=%s",
            job_id, document_id, exc.code,
        )
        _fail(jobs, documents, audits, job_id, document_id, deps.requesting_user_id,
              exc.code, exc.message)
    except Exception as exc:  # noqa: BLE001 — last-resort guard, type only in logs
        log.exception("pipeline crashed: job_id=%s document_id=%s", job_id, document_id)
        _fail(jobs, documents, audits, job_id, document_id, deps.requesting_user_id,
              "PIPELINE_ERROR", "Unexpected processing failure.")


def _fail(jobs: Any, documents: Any, audits: Any, job_id: str, document_id: str,
          user_id: str, code: str, message: str) -> None:
    fail_if_processing = getattr(documents, "mark_failed_if_processing", None)
    for action, label in (
        (lambda: jobs.update_job(job_id, {"status": "FAILED", "completed_at": _now(),
                                          "error_code": code, "error_message": message}), "job"),
        (lambda: (fail_if_processing(document_id) if fail_if_processing
                  else documents.update_status(document_id, "FAILED")), "document"),
        (lambda: _audit(audits, document_id, user_id, "PROCESSING_FAILED",
                        {"job_id": job_id, "error_code": code}), "audit"),
    ):
        try:
            action()
        except Exception:
            log.warning("could not mark %s failed", label)


def _run(job_id: str, document_id: str, deps: PipelineDeps,
         jobs: Any, documents: Any, records: Any, reviews: Any, audits: Any) -> None:
    jobs.update_job(job_id, {"status": "RUNNING", "started_at": _now()})
    document = documents.get(document_id)
    if document is None:
        raise PipelineFail("DOCUMENT_NOT_FOUND", "Document disappeared after the job was created.")
    documents.update_status(document["id"], "PROCESSING")
    _audit(audits, str(document["id"]), deps.requesting_user_id, "PROCESSING_STARTED",
           {"job_id": job_id, "execution_mode": deps.execution_mode,
            **({"fixture_id": deps.fixture_id} if deps.fixture_id else {})})

    storage = deps.storage or SupabaseStorageBackend(deps.client, _bucket())
    try:
        raw = storage.download(document["storage_path"])
    except Exception as exc:
        raise PipelineFail(
            "STORAGE_DOWNLOAD_FAILED",
            "Could not retrieve the source document from private storage.",
        ) from exc

    pages = _ocr(raw, document.get("file_name", ""), deps, document.get("language"))
    ocr_text = "\n".join(page.text for page in pages)

    if deps.ai_service is not None:
        ai_service = deps.ai_service
    else:
        from ..ai.service import get_ai_service

        ai_service = get_ai_service()
    from ..ai.types import ExtractionInput

    try:
        result = ai_service.extract_land_record(
            ExtractionInput(ocr_text=ocr_text, document_type=document.get("document_type"),
                            language=document.get("language"))
        )
    except ProviderError as exc:
        raise PipelineFail(exc.code, exc.message) from exc

    normalized = normalize_record(result.values())["normalized"]
    reference = deps.reference
    if reference is None:
        reference = build_reference(records.list_reference_rows())
    issues = validate_record(normalized, reference)
    issues = _with_duplicates(records, document_id, normalized, issues)
    verdict = record_verdict(issues)

    bind_context = getattr(records, "bind_processing_context", None)
    if bind_context is not None:
        bind_context(jobs=jobs, documents=documents, reviews=reviews, audits=audits)
    _persist(job_id, records, document, pages, result, normalized, issues, verdict, deps)


def _ocr(raw: bytes, file_name: str, deps: PipelineDeps, declared_language: object = None) -> list:
    from ai.ocr.pdf_render import iter_pages_from_bytes

    suffix = Path(file_name or "").suffix.lower() or ".pdf"
    try:
        images = iter_pages_from_bytes(raw, suffix, dpi=deps.dpi)
    except ValueError as exc:
        raise PipelineFail("UNSUPPORTED_FILE_TYPE", str(exc)) from exc
    except Exception as exc:
        raise PipelineFail("RENDER_FAILED", f"Could not render pages ({type(exc).__name__}).") from exc
    ocr_engine = deps.ocr_engine
    if ocr_engine is None:
        from ai.ocr.tesseract_adapter import TesseractOcrEngine, binary_available

        if not binary_available():
            raise PipelineFail(
                "OCR_ENGINE_UNAVAILABLE",
                "The server OCR engine is unavailable. Install Tesseract or configure TESSERACT_CMD.",
            )

        # language=None -> detect the script per page (Latin / Devanagari /
        # Gujarati). The uploader's declared language is only a fallback when
        # detection has no opinion; it is never trusted over the page itself.
        ocr_engine = TesseractOcrEngine(language=None, declared=declared_language)
    pages = []
    try:
        for number, image in enumerate(images, start=1):
            try:
                page, _elapsed = ocr_engine.read_image(image, page_number=number)
            except Exception as exc:
                if type(exc).__name__ == "TesseractNotFoundError":
                    raise PipelineFail(
                        "OCR_ENGINE_UNAVAILABLE",
                        "The server OCR engine is unavailable. Install Tesseract or configure TESSERACT_CMD.",
                    ) from exc
                raise PipelineFail("OCR_FAILED", f"OCR failed on page {number}.") from exc
            pages.append(page)
    except PipelineFail:
        raise
    except ValueError as exc:
        code = "UNSUPPORTED_FILE_TYPE" if suffix not in {".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff"} else "RENDER_FAILED"
        message = str(exc) if code == "UNSUPPORTED_FILE_TYPE" else "Could not render document pages."
        raise PipelineFail(code, message) from exc
    except Exception as exc:
        raise PipelineFail("RENDER_FAILED", "Could not render document pages.") from exc
    if not any(page.text.strip() for page in pages):
        raise PipelineFail("OCR_FAILED", "OCR produced no text on any page.")
    return pages


def _with_duplicates(records: Any, document_id: str, normalized: dict, issues: list) -> list:
    """Append a possible-duplicate issue (08 duplicate layer).

    Compares against all OTHER documents' records. Degrades to no-check
    (with a warning) if the lookup itself fails — never blocks processing.
    """
    try:
        summaries = records.list_record_summaries()
    except Exception:
        log.warning("duplicate check unavailable")
        return issues
    others = [s for s in summaries if str(s.get("document_id")) != str(document_id)]
    verdict, matches = find_duplicates(
        {"survey_number": normalized.get("survey_number"),
         "village": normalized.get("village"),
         "owner_name": normalized.get("owner_name")},
        others,
    )
    if verdict == "POSSIBLE_DUPLICATE":
        return issues + [duplicate_issue(normalized, matches)]
    return issues


def _persist(job_id: str, records: Any, document: dict, pages: list, result: Any,
             normalized: dict, issues: list, verdict: str, deps: PipelineDeps) -> tuple[str, dict]:
    doc_id = str(document["id"])
    record_status = "READY_FOR_APPROVAL" if verdict == "READY_FOR_APPROVAL" else "REVIEW_REQUIRED"
    # Typed columns (DATE/NUMERIC) only ever receive values Postgres can
    # represent. An unparseable value becomes NULL *here* and nowhere else:
    # extracted_fields below still stores the raw string verbatim, and the
    # validation issue that flagged it is persisted with the record, so the
    # document reaches human review instead of aborting the whole insert.
    row, dropped = coerce_typed_columns({**normalized, "status": record_status})
    if dropped:
        log.info("typed columns not representable, stored NULL: %s",
                 ",".join(sorted(dropped)))
    if verdict == "READY_FOR_APPROVAL":
        doc_status = "READY_FOR_APPROVAL"
    elif verdict == "BLOCKED":
        doc_status = "VALIDATION_FAILED"
    else:
        doc_status = "REVIEW_REQUIRED"
    metadata = {"job_id": job_id, "verdict": verdict,
                "execution_mode": deps.execution_mode,
                **({"fixture_id": deps.fixture_id} if deps.fixture_id else {}),
                **({"external_ai_calls": 0, "external_ocr_calls": 0}
                   if deps.execution_mode == "demo" else {}),
                "provider": getattr(result, "provider", ""), "model": getattr(result, "model", ""),
                "prompt_version": getattr(result, "prompt_version", ""),
                "schema_version": getattr(result, "schema_version", "")}
    if dropped:
        # Auditability: name the columns stored as NULL and the exact raw
        # value that could not be represented. The raw value also remains in
        # extracted_fields; this makes the coercion visible in the trail.
        metadata["unrepresentable_values"] = {k: str(v) for k, v in sorted(dropped.items())}
    ocr_rows = [
        {"page_number": page.page_number, "text": page.text,
         "ocr_confidence": page.confidence,
         "structured_output_reference": {"lines": len(page.lines), "width": page.width, "height": page.height}}
        for page in pages
    ]
    extracted_rows = [
        {"field_name": name, "value": item.value, "confidence": item.confidence,
         "source_page": None, "source_text": None, "bounding_box": None,
         "extraction_status": getattr(item, "extraction_status", "EXTRACTED"),
         "validation_status": "NOT_CHECKED"}
        for name, item in result.fields.items()
    ]
    validation_rows = [
        {"rule_id": issue.rule_id, "field_name": issue.field_name,
         "status": issue.status, "severity": issue.severity, "message": issue.message}
        for issue in issues
    ]
    review_priority = "HIGH" if verdict == "BLOCKED" else "MEDIUM"
    review_reason = f"Automatic review: validation verdict {verdict} ({len(issues)} issue(s))"
    try:
        committed = records.persist_processing_result(
            p_job_id=job_id,
            p_document_id=doc_id,
            p_user_id=deps.requesting_user_id,
            p_ocr_results=ocr_rows,
            p_record=row,
            p_extracted_fields=extracted_rows,
            p_validation_results=validation_rows,
            p_document_status=doc_status,
            p_verdict=verdict,
            p_review_priority=review_priority,
            p_review_reason=review_reason,
            p_completion_metadata=metadata,
        )
    except AppError as exc:
        raise PipelineFail(exc.code, exc.message) from exc
    except Exception as exc:
        raise PipelineFail("PERSIST_FAILED", "Could not commit the processing result.") from exc
    return str(committed["record_id"]), dropped
