"""Script detection + language routing (offline, no AI provider calls).

Locks in the two failures found during the OCR upgrade:
  * Gujarati pages were detected as "Latin" by Tesseract OSD (confidence 1.17)
    and read with the English model.
  * Mixed pages (English labels + local-script values) routed to `eng` only,
    silently dropping every local-script value.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ai.ocr.script_detect import (  # noqa: E402
    _config_from_counts,
    _count_scripts,
    normalize_declared,
)

RAW = ROOT / "dataset" / "raw_documents"
needs_fixtures = pytest.mark.skipif(
    not (RAW / "doc05_gujarati.png").is_file(),
    reason="multilingual fixtures absent; run scripts/make_multilingual_docs.py",
)


def test_counts_separate_the_three_scripts():
    counts = _count_scripts("Village गाँव ગામ 145/2")
    assert counts["latin"] > 0
    assert counts["devanagari"] > 0
    assert counts["gujarati"] > 0


def test_digits_and_punctuation_are_not_counted_as_a_script():
    # Identifiers must not drag a page toward the wrong language model.
    assert _count_scripts("145/2 - 2024-03-15") == {
        "latin": 0, "devanagari": 0, "gujarati": 0}


def test_pure_scripts_route_to_their_own_model():
    assert _config_from_counts({"latin": 200, "devanagari": 0, "gujarati": 0}) == "eng"
    assert _config_from_counts({"latin": 0, "devanagari": 150, "gujarati": 0}) == "hin"
    assert _config_from_counts({"latin": 0, "devanagari": 0, "gujarati": 150}) == "guj"


def test_mixed_pages_keep_english_alongside_the_local_script():
    """The regression: English labels + local values must load BOTH models."""
    assert _config_from_counts({"latin": 155, "devanagari": 46, "gujarati": 0}) == "hin+eng"
    assert _config_from_counts({"latin": 156, "devanagari": 0, "gujarati": 45}) == "guj+eng"


def test_incidental_noise_does_not_load_a_language_model():
    # A couple of stray glyphs on an English page must not pull in Devanagari.
    assert _config_from_counts({"latin": 300, "devanagari": 2, "gujarati": 0}) == "eng"


def test_empty_page_has_no_opinion():
    assert _config_from_counts({"latin": 0, "devanagari": 0, "gujarati": 0}) is None


def test_declared_language_normalisation():
    assert normalize_declared("Hindi") == "hin+eng"
    assert normalize_declared(" GU ") == "guj+eng"
    assert normalize_declared("en") == "eng"
    assert normalize_declared("klingon") is None
    assert normalize_declared(None) is None


@needs_fixtures
@pytest.mark.parametrize("doc_id,expected", [
    ("doc01_clean", "eng"),
    ("doc04_hindi", "hin"),
    ("doc05_gujarati", "guj"),
    ("doc06_mixed_en_hi", "hin+eng"),
    ("doc07_mixed_en_gu", "guj+eng"),
])
def test_detection_routes_each_fixture_to_the_right_model(doc_id, expected):
    from PIL import Image

    from ai.ocr.script_detect import detect_script

    lang, evidence = detect_script(Image.open(RAW / f"{doc_id}.png"))
    assert lang.startswith(expected.split("+")[0]), (
        f"{doc_id} routed to {lang!r}, expected {expected!r}; evidence={evidence}")


@needs_fixtures
def test_original_script_is_preserved_not_transliterated():
    """OCR must return the source script verbatim — never a translation."""
    from PIL import Image

    from ai.ocr.tesseract_adapter import TesseractOcrEngine

    engine = TesseractOcrEngine(language=None)
    page, _ = engine.read_image(Image.open(RAW / "doc05_gujarati.png"))
    assert any(0x0A80 <= ord(c) <= 0x0AFF for c in page.text), (
        "Gujarati output contains no Gujarati codepoints")
    assert engine.last_meta["language"].startswith("guj")


@needs_fixtures
def test_preprocessing_never_empties_a_page():
    from PIL import Image

    from ai.ocr.preprocess import preprocess

    for doc_id in ("doc01_clean", "doc03_faded", "doc05_gujarati"):
        result = preprocess(Image.open(RAW / f"{doc_id}.png").convert("RGB"))
        assert result.image.width > 0 and result.image.height > 0
        # Conditioning may upscale but must never shrink content away.
        assert result.image.width >= Image.open(RAW / f"{doc_id}.png").width
