"""Tesseract 5 (LSTM) adapter.

Language-aware: the engine no longer assumes English. `language=None` means
"detect from the page" (Tesseract OSD), which is what the pipeline now uses;
an explicit language string still forces a configuration, which the benchmark
harness relies on to compare configurations fairly.

Language data is loaded from the project-local `tessdata/` directory when
present, so Hindi and Gujarati work without modifying the system install.

Selected after RapidOCR proved uninstallable on Python 3.14 (every release
requires Python <3.13) and PaddlePaddle has no 3.14 wheels either.
Tesseract 5.4.0 installs cleanly via winget (UB-Mannheim build, `eng`
traineddata) and returns exactly the 01 section 9 contract — recognized
text + word positions + confidence — via TSV output. EasyOCR (multi-GB
torch stack) stays a deferred alternative for the handwritten benchmark.
"""
import os
import shutil
import time

from .base import OcrLine, OcrPage
from .preprocess import preprocess as preprocess_image
from .script_detect import detect_script, tess_config

ENGINE_NAME = "tesseract"

_CANDIDATE_PATHS = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
)


def find_binary() -> str:
    """Locate tesseract.exe. Overridable via TESSERACT_CMD for reproducibility."""
    override = os.environ.get("TESSERACT_CMD")
    if override:
        return override
    found = shutil.which("tesseract")
    if found:
        return found
    for candidate in _CANDIDATE_PATHS:
        if os.path.isfile(candidate):
            return candidate
    return "tesseract"  # let pytesseract raise its own descriptive error


def engine_version() -> str:
    import pytesseract

    pytesseract.pytesseract.tesseract_cmd = find_binary()
    try:
        return str(pytesseract.get_tesseract_version())
    except Exception:
        return "unknown"


class TesseractOcrEngine:
    """OCR engine.

    language:   explicit Tesseract config ("eng", "hin+eng", ...) or None to
                detect the script from each page.
    declared:   the language recorded on the document, used only as a fallback
                when detection has no opinion.
    preprocess: conditioning before recognition (see preprocess.py).
    """

    def __init__(self, language: str | None = "eng", *, declared: object = None,
                 preprocess: bool = True) -> None:
        import pytesseract

        self._pytesseract = pytesseract
        self.binary = find_binary()
        pytesseract.pytesseract.tesseract_cmd = self.binary
        self.language = language
        self.declared = declared
        self.preprocess = preprocess
        # Populated per page so the caller can persist how the page was read.
        self.last_meta: dict = {}

    def read_image(self, image, page_number: int = 1) -> tuple[OcrPage, float]:
        """Run OCR on a PIL image. Returns (page, elapsed_seconds)."""
        rgb = image.convert("RGB")

        prep = preprocess_image(rgb, enabled=self.preprocess)
        source = prep.image

        if self.language:
            language, evidence = self.language, {"source": "explicit"}
        else:
            language, evidence = detect_script(source, declared=self.declared)

        started = time.perf_counter()
        data = self._pytesseract.image_to_data(
            source, lang=language, config=tess_config(),
            output_type=self._pytesseract.Output.DICT,
        )
        elapsed = time.perf_counter() - started
        self.last_meta = {
            "language": language,
            "detection": evidence,
            "preprocess_steps": prep.steps,
            "preprocess": prep.notes,
            "engine": ENGINE_NAME,
        }

        # Group word rows (TSV level 5) into lines.
        grouped: dict[tuple, dict] = {}
        count = len(data["text"])
        for i in range(count):
            if int(data["level"][i]) != 5:
                continue
            word = (data["text"][i] or "").strip()
            if not word:
                continue
            try:
                confidence = float(data["conf"][i]) / 100.0
            except (TypeError, ValueError):
                continue
            if confidence < 0:
                continue
            key = (
                int(data["page_num"][i]),
                int(data["block_num"][i]),
                int(data["par_num"][i]),
                int(data["line_num"][i]),
            )
            entry = grouped.setdefault(key, {"words": [], "confs": [], "boxes": []})
            entry["words"].append(word)
            entry["confs"].append(confidence)
            left, top = float(data["left"][i]), float(data["top"][i])
            entry["boxes"].append((left, top, left + float(data["width"][i]), top + float(data["height"][i])))

        lines: list[OcrLine] = []
        for key in sorted(grouped):
            entry = grouped[key]
            boxes = entry["boxes"]
            lines.append(
                OcrLine(
                    text=" ".join(entry["words"]),
                    confidence=sum(entry["confs"]) / len(entry["confs"]),
                    box=[
                        min(b[0] for b in boxes),
                        min(b[1] for b in boxes),
                        max(b[2] for b in boxes),
                        max(b[3] for b in boxes),
                    ],
                )
            )
        confidence = sum(line.confidence for line in lines) / len(lines) if lines else None
        page = OcrPage(
            page_number=page_number,
            text="\n".join(line.text for line in lines),
            confidence=confidence,
            lines=lines,
            width=source.width,
            height=source.height,
        )
        return page, elapsed
