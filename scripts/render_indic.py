"""Correctly-shaped Indic text rendering for document fixtures.

WHY THIS EXISTS
---------------
Pillow renders text without a complex-text-shaping engine unless it was built
against libraqm. This environment reports `features.check("raqm") is False`,
so Pillow places Devanagari and Gujarati glyphs in logical order: pre-base
matras land AFTER their consonant ("अधिकार" renders as "अधकिार") and conjuncts
break apart.

That is fatal for an OCR fixture. The ground truth would hold correct Unicode
while the rendered page showed something else, so the benchmark would be
measuring the renderer's bug rather than the engine's accuracy.

MuPDF (PyMuPDF, already a project dependency) shapes properly via HarfBuzz.
This module therefore composes pages as:

    PIL          -> decorative raster layers (security lattice, stamp,
                    signature, verification block) where shaping is irrelevant
    PyMuPDF      -> ALL text, so every glyph is positioned correctly
    PIL          -> optional post-render degradation (skew, noise, contrast)

Verified: "अधिकार अभिलेख हिस्सा दिनांक क्षेत्रफल" and
"અધિકાર રેકોર્ડ હિસ્સા ક્ષેત્રફળ" render with matras and conjuncts intact.
"""
from __future__ import annotations

import io

import pymupdf
from PIL import Image

# Nirmala UI ships with Windows and covers Devanagari + Gujarati. MuPDF
# resolves it by family name; the fallbacks keep Latin text sane elsewhere.
FONT_STACK = "Nirmala UI, Noto Sans, DejaVu Sans, sans-serif"


def has_shaping() -> bool:
    """True when text will be shaped correctly (always, via MuPDF)."""
    return True


def page_from_layers(width_px: int, height_px: int, dpi: int,
                     background: Image.Image | None,
                     html: str, css: str,
                     overlay: Image.Image | None = None) -> tuple[bytes, Image.Image]:
    """Compose one page. Returns (pdf_bytes, rendered_image).

    Text is inserted as real PDF text (selectable, correctly shaped); raster
    layers sit beneath and above it.
    """
    scale = 72.0 / dpi
    w_pt, h_pt = width_px * scale, height_px * scale

    doc = pymupdf.open()
    page = doc.new_page(width=w_pt, height=h_pt)
    full = pymupdf.Rect(0, 0, w_pt, h_pt)

    if background is not None:
        buf = io.BytesIO()
        background.convert("RGB").save(buf, format="PNG")
        page.insert_image(full, stream=buf.getvalue())

    page.insert_htmlbox(full, html, css=css)

    if overlay is not None:
        buf = io.BytesIO()
        overlay.convert("RGBA").save(buf, format="PNG")
        page.insert_image(full, stream=buf.getvalue(), overlay=True)

    pdf_bytes = doc.tobytes()
    pix = page.get_pixmap(dpi=dpi)
    image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    doc.close()
    return pdf_bytes, image


def degrade(image: Image.Image, seed: int, *, angle: float = -1.6,
            noise: float = 7.5, contrast: float = 0.86,
            blur: float = 0.45) -> Image.Image:
    """Simulate a worn scan: slight skew, sensor noise, reduced contrast."""
    import numpy as np
    from PIL import ImageFilter

    out = image.rotate(angle, resample=Image.BICUBIC, expand=False,
                       fillcolor=(253, 252, 249))
    arr = np.asarray(out).astype("float32")
    rng = np.random.default_rng(seed)
    arr += rng.normal(0, noise, arr.shape)
    arr = 128 + (arr - 128) * contrast
    out = Image.fromarray(arr.clip(0, 255).astype("uint8"))
    return out.filter(ImageFilter.GaussianBlur(blur))


class Placer:
    """Explicit coordinate placement with correct Indic shaping.

    MuPDF's HTML engine collapses percentage table columns unpredictably, which
    overlapped label and value text. Placing every run in its own rectangle
    gives Pillow-style layout control while MuPDF still does the shaping.
    """

    def __init__(self, width_px: int, height_px: int, dpi: int = 200):
        self.dpi = dpi
        self.scale = 72.0 / dpi
        self.doc = pymupdf.open()
        self.page = self.doc.new_page(width=width_px * self.scale,
                                      height=height_px * self.scale)
        self.width_px, self.height_px = width_px, height_px

    def _rect(self, x, y, w, h):
        s = self.scale
        return pymupdf.Rect(x * s, y * s, (x + w) * s, (y + h) * s)

    def image(self, pil_image, overlay: bool = False):
        import io
        buf = io.BytesIO()
        mode = "RGBA" if overlay else "RGB"
        pil_image.convert(mode).save(buf, format="PNG")
        self.page.insert_image(self._rect(0, 0, self.width_px, self.height_px),
                               stream=buf.getvalue(), overlay=overlay)

    def text(self, x, y, w, h, content, *, size=12.5, bold=False, align="left",
             color="#12161f", spacing="normal"):
        weight = "bold" if bold else "normal"
        html = (f'<div style="font-family:{FONT_STACK};font-size:{size}pt;'
                f'font-weight:{weight};color:{color};text-align:{align};'
                f'letter-spacing:{spacing};line-height:1.25;margin:0">{content}</div>')
        self.page.insert_htmlbox(self._rect(x, y, w, h), html)

    def finish(self):
        pdf_bytes = self.doc.tobytes()
        pix = self.page.get_pixmap(dpi=self.dpi)
        image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        self.doc.close()
        return pdf_bytes, image
