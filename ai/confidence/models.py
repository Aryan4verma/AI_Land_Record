"""Confidence contracts."""
from dataclasses import dataclass, field

HIGH_THRESHOLD = 0.80
MEDIUM_THRESHOLD = 0.60
FAIL_CAP = 0.39
WARNING_CAP = 0.69

BANDS = ("HIGH", "MEDIUM", "LOW", "REVIEW_REQUIRED")


@dataclass
class FieldConfidence:
    field_name: str
    score: float | None  # 0.0-1.0, or None when unscorable
    band: str  # HIGH | MEDIUM | LOW | REVIEW_REQUIRED
    review_required: bool
    ocr_confidence: float | None = None
    extraction_confidence: float | None = None
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "field": self.field_name,
            "score": round(self.score, 4) if self.score is not None else None,
            "band": self.band,
            "review_required": self.review_required,
            "ocr_confidence": self.ocr_confidence,
            "extraction_confidence": self.extraction_confidence,
            "reasons": self.reasons,
        }


@dataclass
class RecordConfidence:
    document_id: str
    fields: dict[str, FieldConfidence]
    overall_score: float | None
    overall_band: str
    review_required: bool
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.document_id,
            "overall_score": round(self.overall_score, 4) if self.overall_score is not None else None,
            "overall_band": self.overall_band,
            "review_required": self.review_required,
            "reasons": self.reasons,
            "fields": {name: fc.to_dict() for name, fc in self.fields.items()},
        }
