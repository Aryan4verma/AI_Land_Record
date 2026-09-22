"""Hosted OCR rendering stays page-bounded without changing the OCR contract."""

import io
import sys
from pathlib import Path

import pymupdf
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ai.ocr.pdf_render import iter_pages_from_bytes  # noqa: E402


def _pdf_bytes(page_count: int = 2) -> bytes:
    document = pymupdf.open()
    for index in range(page_count):
        page = document.new_page(width=612, height=792)
        page.insert_text((72, 96), f"Page {index + 1}")
    data = document.tobytes()
    document.close()
    return data


def test_pdf_pages_are_yielded_individually():
    pages = iter_pages_from_bytes(_pdf_bytes(), ".pdf", dpi=150)

    first = next(pages)
    assert first.width > 0 and first.height > 0
    assert next(pages).width > 0
    try:
        next(pages)
    except StopIteration:
        pass
    else:
        raise AssertionError("renderer yielded more pages than the source")


def test_oversized_image_is_bounded_without_dropping_the_page():
    image = Image.new("RGB", (5000, 5000), "white")
    output = io.BytesIO()
    image.save(output, format="PNG")

    page = next(iter_pages_from_bytes(output.getvalue(), ".png"))

    assert page.width * page.height <= 20_000_000
    assert page.width > 0 and page.height > 0
