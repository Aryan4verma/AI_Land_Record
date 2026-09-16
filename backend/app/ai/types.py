"""Internal extraction contracts (06 Layer 4, 07 section 6).

Every provider returns an ExtractionResult: structured fields using the
04_DATA_DICTIONARY field names, per-field confidence/status metadata,
provider+model metadata, and timing. Failures are raised as ProviderError
(see errors.py), never returned as fake results.
"""
from dataclasses import dataclass, field

KNOWN_FIELDS = (
    "owner_name",
    "father_or_spouse_name",
    "survey_number",
    "khasra_number",
    "khata_number",
    "area",
    "area_unit",
    "village",
    "tehsil",
    "district",
    "land_classification",
    "mutation_number",
    "registration_number",
    "record_date",
)

EXTRACTION_STATUSES = ("EXTRACTED", "MISSING", "UNCERTAIN", "CONFLICT", "ERROR")


@dataclass
class ExtractionInput:
    ocr_text: str
    document_type: str | None = None
    language: str | None = None
    document_checksum: str | None = None  # preferred cache identity; else OCR-text hash


@dataclass
class FieldResult:
    field_name: str
    value: str | None
    confidence: float | None
    source_text: str | None = None
    extraction_status: str = "EXTRACTED"


@dataclass
class ExtractionResult:
    fields: dict[str, FieldResult] = field(default_factory=dict)
    provider: str = ""
    model: str = ""
    prompt_version: str = ""
    schema_version: str = ""
    elapsed_seconds: float = 0.0
    raw_response: str = ""
    attempted_routes: list[dict] = field(default_factory=list)  # observability: who handled what
    cache_hit: bool = False

    def values(self) -> dict[str, str | None]:
        """Convenience view: {field_name: value} for all known fields."""
        return {name: self.fields[name].value if name in self.fields else None for name in KNOWN_FIELDS}
