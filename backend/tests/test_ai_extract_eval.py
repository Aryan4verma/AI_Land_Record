"""Offline checks for the OCR->LLM connector and the GT evaluator.

Uses canned provider results (monkeypatched) — no live calls, no key.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ai.extract import evaluate as ev  # noqa: E402
from ai.extract import run_extraction as rx  # noqa: E402
from app.ai.errors import ProviderBadResponseError  # noqa: E402
from app.ai.types import ExtractionInput, ExtractionResult, FieldResult  # noqa: E402


def _canned(fields: dict) -> ExtractionResult:
    return ExtractionResult(
        fields={k: FieldResult(k, v, 0.9, None, "EXTRACTED" if v is not None else "MISSING") for k, v in fields.items()},
        provider="canned",
        model="canned-model",
        prompt_version="v1",
        schema_version="v1",
        elapsed_seconds=0.1,
        raw_response="{}",
    )


def test_build_input_joins_pages_in_order():
    ocr = {"pages": [{"text": "line one"}, {"text": "line two"}], "engine": "t", "engine_version": "1"}
    payload = rx.build_input(ocr, document_type="khata")
    assert isinstance(payload, ExtractionInput)
    assert payload.ocr_text == "line one\nline two"
    assert payload.document_type == "khata"


def test_extract_document_maps_result_and_preserves_versions(monkeypatch):
    monkeypatch.setattr(
        rx, "extract_land_record", lambda payload: _canned({"owner_name": "Ramesh Kumar", "area": "2.45"})
    )
    record = rx.extract_document("docX", {"source_file": "s.pdf", "engine": "t", "engine_version": "1", "pages": []})
    assert record["failed"] is False
    assert record["provider"] == "canned"
    assert record["values"]["owner_name"] == "Ramesh Kumar"
    assert record["fields"]["area"] == {"value": "2.45", "confidence": 0.9, "status": "EXTRACTED"}
    assert record["ocr_engine"] == "t"


def test_extract_document_records_provider_failure(monkeypatch):
    def boom(payload):
        raise ProviderBadResponseError("canned", "bad json")

    monkeypatch.setattr(rx, "extract_land_record", boom)
    record = rx.extract_document("docX", {"pages": []})
    assert record["failed"] is True
    assert record["error_code"] == "PROVIDER_BAD_RESPONSE"
    assert "values" not in record


@pytest.mark.parametrize(
    ("expected", "got", "field", "verdict"),
    [
        ("Ramesh Kumar", "Ramesh Kumar", "owner_name", "CORRECT"),
        ("Ramesh Kumar", "  ramesh   KUMAR ", "owner_name", "CORRECT"),
        (2.45, "2.45", "area", "CORRECT"),
        ("Hectare", "hectare", "area_unit", "CORRECT"),
        ("Demo Village", None, "village", "MISSING"),
        (None, None, "registration_number", "CORRECT"),
        (None, "XYZ-1", "registration_number", "HALLUCINATED"),
        ("145/2", "145/3", "survey_number", "INCORRECT"),
        ("Agricultural", "Agriculture", "land_classification", "PARTIALLY_CORRECT"),
        ("M-2024-0091", "M-2024", "mutation_number", "INCORRECT"),
    ],
)
def test_classify_field(expected, got, field, verdict):
    assert ev.classify_field(expected, got, field) == verdict


def test_evaluate_record_counts_and_accuracy():
    gt = {"id": "d", "owner_name": "A", "village": "B", "area": 1.5, "registration_number": None}
    output = {"failed": False, "values": {"owner_name": "A", "village": None, "area": "1.5", "registration_number": "X"}}
    verdict = ev.evaluate_record(gt, output)
    assert verdict["counts"] == {"CORRECT": 2, "MISSING": 1, "HALLUCINATED": 1}
    assert verdict["accuracy"] == 0.5
    assert verdict["fields"]["area"]["verdict"] == "CORRECT"


def test_evaluate_record_failed_output():
    verdict = ev.evaluate_record({"id": "d"}, {"failed": True, "error_code": "PROVIDER_TIMEOUT"})
    assert verdict["failed"] is True
    assert verdict["accuracy"] is None
