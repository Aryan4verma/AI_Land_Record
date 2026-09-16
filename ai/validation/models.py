"""Validation contracts (08 sections 9-10, 09 validation_results table).

Status: NOT_CHECKED | PASS | WARNING | FAIL | REVIEW_REQUIRED
Severity: INFO | WARNING | ERROR | CRITICAL
"""
from dataclasses import dataclass, field


@dataclass
class ValidationIssue:
    rule_id: str
    field_name: str | None
    status: str
    severity: str
    message: str

    def to_dict(self) -> dict:
        return {
            "rule_id": self.rule_id,
            "field": self.field_name,
            "status": self.status,
            "severity": self.severity,
            "message": self.message,
        }


@dataclass
class ReferenceData:
    """Trusted vocabularies for reference checks (08 section 6).

    Names are matched case-insensitively after whitespace normalization.
    `version`/`source` are recorded with every check that uses them.
    """

    version: str = "v1"
    source: str = "demo-seed"
    villages: set[str] = field(default_factory=set)
    tehsils: set[str] = field(default_factory=set)
    districts: set[str] = field(default_factory=set)
    village_to_tehsil: dict[str, str] = field(default_factory=dict)
    tehsil_to_district: dict[str, str] = field(default_factory=dict)


def demo_reference() -> ReferenceData:
    """The DEMO chain seeded in the database (NOT real government data)."""
    return ReferenceData(
        version="v1",
        source="demo-seed",
        villages={"demo village"},
        tehsils={"demo tehsil"},
        districts={"demo district"},
        village_to_tehsil={"demo village": "demo tehsil"},
        tehsil_to_district={"demo tehsil": "demo district"},
    )
