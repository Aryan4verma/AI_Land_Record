"""OCR interface (06_AI_ARCHITECTURE Layer 3).

Every engine must return: text + bounding boxes + confidence + page info.
Engines are swappable behind this structure; nothing here imports a
specific OCR library.
"""
from dataclasses import asdict, dataclass, field


@dataclass
class OcrLine:
    text: str
    confidence: float  # 0.0 - 1.0 as reported by the engine
    box: list[float]  # axis-aligned [x1, y1, x2, y2] in pixels


@dataclass
class OcrPage:
    page_number: int  # 1-based
    text: str  # lines joined by "\n" in engine detection order
    confidence: float | None  # mean line confidence; None when no lines
    lines: list[OcrLine] = field(default_factory=list)
    width: int = 0
    height: int = 0


@dataclass
class OcrResult:
    engine: str
    engine_version: str
    source_file: str
    pages: list[OcrPage]
    elapsed_seconds: float

    def to_dict(self) -> dict:
        return {
            "engine": self.engine,
            "engine_version": self.engine_version,
            "source_file": self.source_file,
            "elapsed_seconds": round(self.elapsed_seconds, 3),
            "pages": [asdict(p) for p in self.pages],
        }
