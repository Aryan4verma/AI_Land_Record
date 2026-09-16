"""OCR pipeline unit checks (12 section 3). Pure metric/string functions —
no Tesseract binary needed (the adapter itself is covered live by the
benchmark harness in ai/.venv).
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ai.ocr.benchmark import error_rate, levenshtein, normalize  # noqa: E402


def test_normalize_collapses_and_lowers():
    assert normalize("  Survey   Number: 145/2\n") == "survey number: 145/2"
    assert normalize("") == ""


def test_levenshtein_known_distances():
    assert levenshtein("", "") == 0
    assert levenshtein("abc", "") == 3
    assert levenshtein("kitten", "sitting") == 3
    assert levenshtein("145/2", "145/2") == 0


def test_error_rate_char_and_word():
    assert error_rate("abc", "abc", "char") == 0.0
    assert error_rate("", "", "word") == 0.0
    assert error_rate("", "x", "word") == 1.0
    assert 0.0 < error_rate("145/2", "4145/2", "char") < 0.5
    assert error_rate("a b c", "a x c", "word") == 1 / 3


def test_manifest_contract():
    """Every manifest entry carries the keys the harnesses require."""
    manifest = json.loads((ROOT / "dataset" / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["version"]
    assert manifest["documents"]
    for entry in manifest["documents"]:
        assert {"id", "file", "ground_truth", "difficulty"} <= set(entry)
        assert (ROOT / "dataset" / entry["file"]).is_file()
