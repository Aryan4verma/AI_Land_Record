"""Page loading: PDF via PyMuPDF (Layer 2 PDF-to-image conversion),
images via Pillow. Always returns a list of PIL images in page order.
"""
import io
from pathlib import Path

from PIL import Image

_PDF_SUFFIXES = {".pdf"}
_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".tif", ".tiff"}
_MAX_RENDER_PIXELS = 20_000_000


def _scaled_pdf_matrix(page, dpi: int):
    """Keep one rasterized page below the hosted-memory pixel budget."""
    import pymupdf

    scale = dpi / 72.0
    width = max(float(page.rect.width) * scale, 1.0)
    height = max(float(page.rect.height) * scale, 1.0)
    pixels = width * height
    if pixels > _MAX_RENDER_PIXELS:
        scale *= (_MAX_RENDER_PIXELS / pixels) ** 0.5
    return pymupdf.Matrix(scale, scale)


def _bounded_image(image: Image.Image) -> Image.Image:
    """Return an RGB image within the raster budget without dropping a page."""
    rgb = image.convert("RGB")
    pixels = rgb.width * rgb.height
    if pixels <= _MAX_RENDER_PIXELS:
        return rgb
    factor = (_MAX_RENDER_PIXELS / pixels) ** 0.5
    resized = rgb.resize(
        (max(1, int(rgb.width * factor)), max(1, int(rgb.height * factor))),
        Image.Resampling.LANCZOS,
    )
    rgb.close()
    return resized


def iter_pages_from_bytes(data: bytes, suffix: str, dpi: int = 300):
    """Yield pages one at a time so multi-page jobs do not retain all rasters."""
    suffix = suffix.lower()
    if suffix in _PDF_SUFFIXES:
        import pymupdf

        with pymupdf.open(stream=data, filetype="pdf") as doc:
            for page in doc:
                pix = page.get_pixmap(matrix=_scaled_pdf_matrix(page, dpi), alpha=False)
                yield Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        return
    if suffix in _IMAGE_SUFFIXES:
        with Image.open(io.BytesIO(data)) as image:
            yield _bounded_image(image)
        return
    raise ValueError(f"unsupported file type: {suffix}")


class PageNotFoundError(ValueError):
    """The requested 1-based page is outside the source document."""


class SourceRenderError(ValueError):
    """The source bytes cannot be decoded/rendered safely."""


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
    return list(iter_pages_from_bytes(data, suffix, dpi=dpi))


def render_page_from_bytes(data: bytes, suffix: str, page_number: int,
                           dpi: int = 150) -> Image.Image:
    """Render one 1-based source page without rasterizing the whole PDF.

    PDFs are opened only for the requested page. Raster images are treated as
    one-page sources, matching the existing OCR contract. Decode failures are
    normalized so the API never leaks library or storage details.
    """
    if page_number < 1:
        raise PageNotFoundError("page number must be positive")

    suffix = suffix.lower()
    if suffix in _PDF_SUFFIXES:
        try:
            import pymupdf

            with pymupdf.open(stream=data, filetype="pdf") as doc:
                if page_number > doc.page_count:
                    raise PageNotFoundError("page is outside the document")
                page = doc.load_page(page_number - 1)
                pix = page.get_pixmap(dpi=dpi, alpha=False)
                if pix.width * pix.height > _MAX_RENDER_PIXELS:
                    raise SourceRenderError("source page is too large to render")
                return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        except PageNotFoundError:
            raise
        except Exception as exc:
            raise SourceRenderError("source PDF could not be rendered") from exc

    if suffix in _IMAGE_SUFFIXES:
        if page_number != 1:
            raise PageNotFoundError("image sources contain one page")
        try:
            with Image.open(io.BytesIO(data)) as image:
                if image.width * image.height > _MAX_RENDER_PIXELS:
                    raise SourceRenderError("source image is too large to render")
                return image.convert("RGB")
        except SourceRenderError:
            raise
        except Exception as exc:
            raise SourceRenderError("source image could not be rendered") from exc

    raise SourceRenderError("unsupported source type")
