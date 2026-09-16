"""Pre-OCR image conditioning for scanned land records.

Design rule: every operation here is conservative and reversible in effect —
none of them may invent, remove or "repair" glyphs. The original uploaded
document is never modified; this works on an in-memory copy used solely as OCR
input, and the raw OCR text remains the authoritative record.

Deliberately NOT done, because each measurably destroys evidence on the kind
of pages this system handles:

  * global binarisation / aggressive thresholding — erases faint and faded
    strokes, which is exactly the text a reviewer most needs to see;
  * unsharp masking — manufactures edge artefacts that Tesseract reads as
    punctuation, and mangles Devanagari matras and Gujarati diacritics;
  * despeckling by morphology — removes the dots and nuktas that distinguish
    characters in both Indic scripts;
  * cropping — can silently drop marginalia and stamps.

What remains is the set that measured positively or neutrally on the project's
own fixtures: upscaling small pages toward the ~300 DPI Tesseract's models
expect, gentle contrast normalisation, and orientation correction.

Grayscale conversion was TRIED and REMOVED on measured evidence - see the
comment in preprocess().
"""
from __future__ import annotations

from dataclasses import dataclass, field

# Tesseract's LSTM models are trained around 300 DPI. Text much smaller than
# this loses stroke detail; upscaling recovers a measurable amount.
TARGET_MIN_WIDTH = 1600
MAX_UPSCALE = 3.0

# Deskew is only worth doing when the page is actually crooked; rotating a
# straight page resamples it for nothing.
MIN_DESKEW_DEGREES = 0.35
MAX_DESKEW_DEGREES = 15.0


@dataclass
class PreprocessResult:
    image: object
    steps: list = field(default_factory=list)
    notes: dict = field(default_factory=dict)


def _upscale(image, notes: dict):
    width = image.width
    if width >= TARGET_MIN_WIDTH:
        return image, False
    factor = min(TARGET_MIN_WIDTH / max(width, 1), MAX_UPSCALE)
    if factor <= 1.05:
        return image, False
    from PIL import Image as _Image

    new = image.resize(
        (int(image.width * factor), int(image.height * factor)),
        _Image.LANCZOS,
    )
    notes["upscale_factor"] = round(factor, 3)
    return new, True


def _grayscale(image, notes: dict):
    if image.mode == "L":
        return image, False
    return image.convert("L"), True


def _normalize_contrast(image, notes: dict):
    """Stretch the histogram only when the page is genuinely low-contrast.

    A faded scan benefits; a healthy scan is left alone so nothing is
    amplified into noise.
    """
    try:
        from PIL import ImageOps
    except Exception:
        return image, False
    if image.mode == "L":
        lo, hi = image.getextrema()
    else:
        # Work from luminance to decide, but stretch the colour image itself.
        lo, hi = image.convert("L").getextrema()
    spread = hi - lo
    notes["contrast_spread"] = spread
    if spread >= 200:
        return image, False
    # cutoff=0 keeps every real pixel value; it only rescales the range.
    return ImageOps.autocontrast(image, cutoff=0), True


def _deskew(image, notes: dict):
    """Rotate using Tesseract's own OSD angle — measured, not estimated."""
    try:
        import pytesseract

        from .script_detect import tess_config

        raw = pytesseract.image_to_osd(image, config=tess_config())
        angle = 0.0
        for line in (raw or "").splitlines():
            if line.startswith("Rotate:"):
                angle = float(line.split(":")[1].strip())
                break
        notes["osd_rotate"] = angle
        # OSD reports the rotation needed in 90-degree steps for orientation.
        if angle in (90.0, 180.0, 270.0):
            return image.rotate(-angle, expand=True, fillcolor=255), True
    except Exception as exc:
        notes["deskew_error"] = type(exc).__name__
    return image, False


def preprocess(image, *, enabled: bool = True) -> PreprocessResult:
    """Condition a page for OCR. Returns the image plus what was applied."""
    notes: dict = {"original_size": [image.width, image.height]}
    if not enabled:
        return PreprocessResult(image=image, steps=[], notes={"enabled": False})

    steps: list[str] = []
    current = image
    # Grayscale is deliberately ABSENT. Measured on doc11 (noisy degraded
    # Gujarati scan) it drove CER from 0.0712 to 0.3988: Tesseract performs its
    # own adaptive thresholding and does that better from the colour original,
    # because converting first discards the chroma separation between faint ink
    # and the security lattice. _grayscale() is kept for callers that need it,
    # but it is not part of the default pipeline.
    for name, op in (
        ("orientation", _deskew),
        ("upscale", _upscale),
        ("contrast", _normalize_contrast),
    ):
        try:
            current, applied = op(current, notes)
            if applied:
                steps.append(name)
        except Exception as exc:  # never let conditioning fail a page
            notes[f"{name}_error"] = type(exc).__name__
    notes["final_size"] = [current.width, current.height]
    return PreprocessResult(image=current, steps=steps, notes=notes)
