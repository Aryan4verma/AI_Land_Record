"""Script detection -> Tesseract language configuration.

Why this exists
---------------
The pipeline previously constructed `TesseractOcrEngine()` with no language at
all, so every page was read as `eng`. A Devanagari or Gujarati page produced
either empty output or Latin noise, regardless of what the uploader declared.

Strategy
--------
Evidence from the page comes first, the uploader's declaration second, and a
safe default last:

  1. Tesseract's own orientation-and-script detection (OSD, `--psm 0`) reports
     the dominant script. This is the engine's own evidence, not a heuristic
     of ours, and it needs no extra language pack beyond `osd`.
  2. If OSD cannot decide (too little text, tiny page, low confidence), fall
     back to the `language` the uploader recorded on the document.
  3. Otherwise `eng`.

Local scripts are always paired with `eng` (`hin+eng`, `guj+eng`) because real
land records mix English labels, digits and identifiers with local-script
values. Passing every installed language on every page is deliberately NOT
done: it measurably slows recognition and lets the wrong model win on short
strings.

Nothing here corrects or translates text. It only chooses which language pack
reads the page.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

# Tesseract OSD script name -> language configuration.
SCRIPT_TO_LANG = {
    "Latin": "eng",
    "Devanagari": "hin+eng",
    "Gujarati": "guj+eng",
}

DEFAULT_LANG = "eng"

# What an uploader may record on the document, normalised to a config.
DECLARED_TO_LANG = {
    "en": "eng", "eng": "eng", "english": "eng",
    "hi": "hin+eng", "hin": "hin+eng", "hindi": "hin+eng", "devanagari": "hin+eng",
    "gu": "guj+eng", "guj": "guj+eng", "gujarati": "guj+eng",
    "eng+hin": "hin+eng", "hin+eng": "hin+eng",
    "eng+guj": "guj+eng", "guj+eng": "guj+eng",
}

_SCRIPT_RE = re.compile(r"Script:\s*(\w+)")
_SCRIPT_CONF_RE = re.compile(r"Script confidence:\s*([\d.]+)")

# OSD below this confidence is treated as "no opinion" rather than trusted.
MIN_SCRIPT_CONFIDENCE = 1.0


def tessdata_dir() -> str | None:
    """Project-local tessdata, so hin/guj work without touching the install.

    TESSDATA_PREFIX wins if the deployment already sets one.
    """
    env = os.environ.get("TESSDATA_PREFIX")
    if env:
        return env
    local = Path(__file__).resolve().parent / "tessdata"
    return str(local) if local.is_dir() else None


_TESSDATA_APPLIED = False


def ensure_tessdata() -> None:
    """Point Tesseract at our language data via TESSDATA_PREFIX.

    Deliberately NOT passed as --tessdata-dir: pytesseract splits the config
    string on whitespace, so a path containing spaces (the norm on Windows)
    arrives at the binary broken. The environment variable has no such
    quoting problem.
    """
    global _TESSDATA_APPLIED
    if _TESSDATA_APPLIED:
        return
    directory = tessdata_dir()
    if directory:
        os.environ["TESSDATA_PREFIX"] = directory
    # Also pin the binary: detection must work standalone (benchmarks, tests),
    # not only when an engine instance happened to configure pytesseract first.
    try:
        import pytesseract

        from .tesseract_adapter import find_binary

        if not pytesseract.pytesseract.tesseract_cmd or                 pytesseract.pytesseract.tesseract_cmd == "tesseract":
            pytesseract.pytesseract.tesseract_cmd = find_binary()
    except Exception:
        pass
    _TESSDATA_APPLIED = True


def tess_config(extra: str = "") -> str:
    """Extra Tesseract flags. Language data is located via TESSDATA_PREFIX."""
    ensure_tessdata()
    return extra


def normalize_declared(language: object) -> str | None:
    """Map a document's recorded language to a config, or None if unusable."""
    if not isinstance(language, str):
        return None
    return DECLARED_TO_LANG.get(language.strip().lower())


# Unicode blocks that identify each script unambiguously.
DEVANAGARI = (0x0900, 0x097F)
GUJARATI = (0x0A80, 0x0AFF)

# Below this share of a page's letters, a script is treated as incidental
# noise rather than real content worth loading a language model for.
MIN_SCRIPT_SHARE = 0.06

# OSD's script confidence is only trusted well above its noise floor. Measured
# on this project's fixtures it reported "Latin" at 1.17 for a page that is
# entirely Gujarati, so a low-confidence OSD verdict decides nothing.
TRUST_OSD_ABOVE = 3.0


def _count_scripts(text: str) -> dict:
    counts = {"latin": 0, "devanagari": 0, "gujarati": 0}
    for ch in text or "":
        code = ord(ch)
        if DEVANAGARI[0] <= code <= DEVANAGARI[1]:
            counts["devanagari"] += 1
        elif GUJARATI[0] <= code <= GUJARATI[1]:
            counts["gujarati"] += 1
        elif ch.isascii() and ch.isalpha():
            counts["latin"] += 1
    return counts


def _probe(image) -> tuple[dict, str | None]:
    """Read the page once with every installed script, then count codepoints.

    This is direct evidence — characters actually recognised — rather than
    OSD's opinion about glyph shapes. It is the only reliable way found to
    separate Gujarati from Latin here, and the only way to notice that a page
    carries BOTH English labels and local-script values.
    """
    try:
        import pytesseract

        text = pytesseract.image_to_string(image, lang="eng+hin+guj", config=tess_config())
        return _count_scripts(text), None
    except Exception as exc:
        return {"latin": 0, "devanagari": 0, "gujarati": 0}, type(exc).__name__


def _config_from_counts(counts: dict) -> str | None:
    total = sum(counts.values())
    if total == 0:
        return None
    dev = counts["devanagari"] / total
    guj = counts["gujarati"] / total
    latin = counts["latin"] / total

    local = None
    if dev >= MIN_SCRIPT_SHARE and dev >= guj:
        local = "hin"
    elif guj >= MIN_SCRIPT_SHARE:
        local = "guj"

    if local is None:
        return "eng"
    # Pair with English whenever Latin is genuinely present: land records mix
    # English labels, digits and identifiers with local-script values, and
    # dropping eng loses them.
    return f"{local}+eng" if latin >= MIN_SCRIPT_SHARE else local


def detect_script(image, *, declared: object = None) -> tuple[str, dict]:
    """Return (language_config, evidence).

    Order of authority: a confident OSD verdict, then recognised-codepoint
    evidence, then the uploader's declaration, then English. `evidence`
    records how the decision was reached so it can be persisted and audited
    rather than being an invisible guess.
    """
    evidence: dict = {"source": None, "script": None, "script_confidence": None,
                      "declared": declared if isinstance(declared, str) else None}

    try:
        import pytesseract

        raw = pytesseract.image_to_osd(image, config=tess_config())
        script_match = _SCRIPT_RE.search(raw or "")
        conf_match = _SCRIPT_CONF_RE.search(raw or "")
        script = script_match.group(1) if script_match else None
        confidence = float(conf_match.group(1)) if conf_match else None
        evidence["script"] = script
        evidence["script_confidence"] = confidence
        # Only a CONFIDENT non-Latin verdict short-circuits the probe. A Latin
        # verdict never does: that is exactly the case OSD gets wrong here.
        if (script in SCRIPT_TO_LANG and script != "Latin"
                and confidence is not None and confidence >= TRUST_OSD_ABOVE):
            evidence["source"] = "osd"
            return SCRIPT_TO_LANG[script], evidence
    except Exception as exc:  # OSD is best-effort: never block a page on it
        evidence["osd_error"] = type(exc).__name__

    counts, probe_error = _probe(image)
    evidence["codepoints"] = counts
    if probe_error:
        evidence["probe_error"] = probe_error
    config = _config_from_counts(counts)
    if config:
        evidence["source"] = "codepoints"
        return config, evidence

    declared_lang = normalize_declared(declared)
    if declared_lang:
        evidence["source"] = "declared"
        return declared_lang, evidence

    evidence["source"] = "default"
    return DEFAULT_LANG, evidence
