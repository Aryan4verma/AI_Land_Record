"""Demo Mode fixture loading and the two fixture-backed pipeline stages.

Demo Mode is a controlled demonstration path for known documents. It supplies
precomputed OCR and extraction results instead of contacting an external AI or
OCR service, while the real application handles everything after that stage:
validation, confidence, persistence, review, correction, approval and audit all
run exactly as in Live Mode.

Two design points matter:

* A document is recognised by the SHA-256 of its bytes, never by filename. A
  renamed copy of the canonical document still matches; an unrelated file never
  does, and an unmatched file is refused rather than guessed at.
* The engines below are injected through the pipeline's existing
  `PipelineDeps.ocr_engine` / `PipelineDeps.ai_service` seams. No pipeline stage
  is modified, duplicated or bypassed, so Demo Mode cannot drift away from the
  behaviour it is meant to demonstrate.

Nothing here weakens authentication, authorization or auditing.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from ..errors import AppError
from ..logging_config import get_logger

log = get_logger(__name__)

DEMO_PROVIDER = "demo-fixture"
DEMO_PIPELINE_VERSION = "v1-demo"


def fixture_root(configured: str | None = None) -> Path:
    """Resolve the fixture directory, defaulting to <repo>/demo/fixtures."""
    if configured:
        return Path(configured).expanduser().resolve()
    return Path(__file__).resolve().parents[3] / "demo" / "fixtures"


@lru_cache(maxsize=8)
def _load_manifest(root: str) -> dict:
    path = Path(root) / "manifest.json"
    if not path.is_file():
        raise AppError(
            503, "DEMO_NOT_CONFIGURED",
            "Demo configuration is incomplete. Please contact the project administrator.")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        log.warning("demo manifest unreadable: %s", type(exc).__name__)
        raise AppError(503, "DEMO_CONFIG_INVALID",
                       "Demo configuration could not be loaded.") from exc
    if not isinstance(data.get("fixtures"), list) or not data["fixtures"]:
        raise AppError(503, "DEMO_CONFIG_INVALID",
                       "Demo configuration could not be loaded.")
    return data


def find_fixture(checksum: str, *, root: str | None = None) -> dict | None:
    """Return the fixture whose SHA-256 matches, or None.

    Matching is on content, so renaming the file changes nothing.
    """
    directory = fixture_root(root)
    manifest = _load_manifest(str(directory))
    target = (checksum or "").strip().lower()
    if len(target) != 64:
        return None
    for entry in manifest["fixtures"]:
        if str(entry.get("sha256", "")).strip().lower() == target:
            return entry
    return None


def load_fixture_payloads(fixture: dict, *, root: str | None = None) -> tuple[dict, dict]:
    """Read (ocr_result, extraction_result) for a manifest entry."""
    directory = fixture_root(root)
    try:
        ocr = json.loads((directory / fixture["ocr_result"]).read_text(encoding="utf-8"))
        extraction = json.loads(
            (directory / fixture["extraction_result"]).read_text(encoding="utf-8"))
    except Exception as exc:
        log.warning("demo fixture payload unreadable: %s", type(exc).__name__)
        raise AppError(503, "DEMO_CONFIG_INVALID",
                       "Demo configuration could not be loaded.") from exc
    if not ocr.get("pages"):
        raise AppError(503, "DEMO_CONFIG_INVALID",
                       "Demo configuration could not be loaded.")
    return ocr, extraction


class DemoOcrEngine:
    """Replays the fixture's OCR pages. Contacts no OCR service.

    It accepts and ignores the rendered page image: the real storage download
    and PDF rendering still happen in Demo Mode, so that half of the workflow
    is genuinely exercised.
    """

    def __init__(self, ocr_payload: dict) -> None:
        self._payload = ocr_payload
        self._pages = ocr_payload.get("pages", [])
        self.external_calls = 0  # asserted by tests; must stay 0

    def read_image(self, image: Any, page_number: int = 1) -> tuple[Any, float]:
        from ai.ocr.base import OcrLine, OcrPage

        source = next((p for p in self._pages if p.get("page_number") == page_number), None)
        if source is None:
            # A fixture page is missing: fail loudly rather than invent text.
            raise AppError(503, "DEMO_CONFIG_INVALID",
                           "Demo configuration could not be loaded.")
        page = OcrPage(
            page_number=source["page_number"],
            text=source.get("text", ""),
            confidence=source.get("confidence"),
            lines=[OcrLine(text=ln["text"], confidence=ln["confidence"], box=list(ln["box"]))
                   for ln in source.get("lines", [])],
            width=source.get("width", 0),
            height=source.get("height", 0),
        )
        return page, 0.0


class DemoExtractionService:
    """Replays the fixture's extraction. Contacts no AI provider.

    Mirrors AIService.extract_land_record so the pipeline cannot tell the
    difference, and reports itself honestly as `demo-fixture` in the provider
    metadata that reaches the audit trail.
    """

    def __init__(self, extraction_payload: dict, fixture_id: str) -> None:
        self._payload = extraction_payload
        self.fixture_id = fixture_id
        self.external_calls = 0  # asserted by tests; must stay 0

    def extract_land_record(self, payload: Any) -> Any:
        from app.ai.types import ExtractionResult, FieldResult

        fields = {
            name: FieldResult(
                field_name=name,
                value=item.get("value"),
                confidence=item.get("confidence"),
                source_text=item.get("source_text"),
                extraction_status=item.get("extraction_status", "EXTRACTED"),
            )
            for name, item in (self._payload.get("fields") or {}).items()
        }
        return ExtractionResult(
            fields=fields,
            provider=DEMO_PROVIDER,
            model=self.fixture_id,
            prompt_version=str(self._payload.get("prompt_version", "")),
            schema_version=str(self._payload.get("schema_version_provider", "")),
            elapsed_seconds=0.0,
            raw_response="",
            attempted_routes=[{"provider": DEMO_PROVIDER, "model": self.fixture_id,
                               "outcome": "ok", "attempts": 0}],
            cache_hit=False,
        )


def build_demo_stages(checksum: str, *, root: str | None = None) -> tuple[dict, DemoOcrEngine,
                                                                         DemoExtractionService]:
    """Resolve a document's fixture and build its replay stages.

    Raises 422 when the uploaded document is not a configured demo document —
    Demo Mode never falls back to a live provider on its own.
    """
    fixture = find_fixture(checksum, root=root)
    if fixture is None:
        raise AppError(422, "DEMO_DOCUMENT_NOT_RECOGNISED",
                       "This document is not one of the configured demo documents. "
                       "Switch to Live processing to process it normally.")
    ocr_payload, extraction_payload = load_fixture_payloads(fixture, root=root)
    fixture_id = str(fixture.get("fixture_id"))
    log.info("demo fixture resolved: fixture_id=%s pages=%s external_ai_calls=0 "
             "external_ocr_calls=0", fixture_id, len(ocr_payload.get("pages", [])))
    return (fixture,
            DemoOcrEngine(ocr_payload),
            DemoExtractionService(extraction_payload, fixture_id))
