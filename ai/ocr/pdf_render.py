"""Page loading: PDF via PyMuPDF (Layer 2 PDF-to-image conversion),
images via Pillow. Always returns a list of PIL images in page order.
"""
import io
from pathlib import Path

from PIL import Image

_PDF_SUFFIXES = {".pdf"}
_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".tif", ".tiff"}


def load_pages(path: str | Path, dpi: int = 300) -> list[Image.Image]:
    src = Path(path)
    suffix = src.suffix.lower()
    if suffix in _PDF_SUFFIXES:
        import pymupdf

        images: list[Image.Image] = []
        with pymupdf.open(src) as doc:
            for page in doc:
                pix = page.get_pixmap(dpi=dpi)
                images.append(Image.frombytes("RGB", (pix.width, pix.height), pix.samples))
        return images
    if suffix in _IMAGE_SUFFIXES:
        with Image.open(src) as img:
            return [img.convert("RGB")]
    raise ValueError(f"unsupported file type: {src.suffix}")


def load_pages_from_bytes(data: bytes, suffix: str, dpi: int = 300) -> list[Image.Image]:
    """Same as load_pages but from in-memory bytes (pipeline downloads)."""
    suffix = suffix.lower()
    if suffix in _PDF_SUFFIXES:
        import pymupdf

        images: list[Image.Image] = []
        with pymupdf.open(stream=data, filetype="pdf") as doc:
            for page in doc:
                pix = page.get_pixmap(dpi=dpi)
                images.append(Image.frombytes("RGB", (pix.width, pix.height), pix.samples))
        return images
    if suffix in _IMAGE_SUFFIXES:
        with Image.open(io.BytesIO(data)) as img:
            return [img.convert("RGB")]
    raise ValueError(f"unsupported file type: {suffix}")
