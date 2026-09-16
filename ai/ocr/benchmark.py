"""OCR benchmark (12_EVALUATION_AND_TESTING section 3).

Reads dataset/manifest.json, runs the POC engine over each document,
compares against ground-truth text (CER/WER on normalized text), and
writes dataset/evaluation/ocr_benchmark.json. Prints a compact table.

Usage (from repo root):
    .\\ai\\.venv\\Scripts\\python -m ai.ocr.benchmark
"""
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


def _ensure_root() -> None:
    root = Path(__file__).resolve().parents[2]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))


_ensure_root()

from ai.ocr.pdf_render import load_pages  # noqa: E402
from ai.ocr.tesseract_adapter import ENGINE_NAME, TesseractOcrEngine, engine_version  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def levenshtein(a: str, b: str) -> int:
    if len(a) < len(b):
        a, b = b, a
    previous = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        current = [i]
        for j, cb in enumerate(b, start=1):
            current.append(min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (ca != cb)))
        previous = current
    return previous[-1]


def error_rate(reference: str, hypothesis: str, unit: str) -> float:
    ref = normalize(reference)
    hyp = normalize(hypothesis)
    ref_seq = ref.split(" ") if unit == "word" else ref
    hyp_seq = hyp.split(" ") if unit == "word" else hyp
    if not ref_seq:
        return 0.0 if not hyp_seq else 1.0
    if unit == "word":
        return levenshtein(ref_seq, hyp_seq) / max(len(ref_seq), 1)
    return levenshtein(ref, hyp) / max(len(ref), 1)


def main() -> int:
    manifest_path = ROOT / "dataset" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    # language=None -> per-page script detection, matching the pipeline.
    engine = TesseractOcrEngine(language=None)
    version = engine_version()
    results = []
    for entry in manifest["documents"]:
        doc_path = ROOT / "dataset" / entry["file"]
        gt = json.loads((ROOT / "dataset" / entry["ground_truth"]).read_text(encoding="utf-8"))
        started = time.perf_counter()
        failed, error, text, confidences, n_lines = False, "", "", [], 0
        try:
            for number, image in enumerate(load_pages(doc_path), start=1):
                page, _elapsed = engine.read_image(image, page_number=number)
                text += ("\n" if text else "") + page.text
                n_lines += len(page.lines)
                confidences.extend(line.confidence for line in page.lines)
            if not text.strip():
                failed, error = True, "empty OCR output"
        except Exception as exc:  # noqa: BLE001 — benchmark must record, not crash
            failed, error = True, f"{type(exc).__name__}: {exc}"
        seconds = time.perf_counter() - started
        mean_conf = sum(confidences) / len(confidences) if confidences else None
        results.append(
            {
                "id": entry["id"],
                "difficulty": entry["difficulty"],
                "cer": round(error_rate(gt["text"], text, "char"), 4),
                "wer": round(error_rate(gt["text"], text, "word"), 4),
                "mean_confidence": round(mean_conf, 4) if mean_conf is not None else None,
                "lines_detected": n_lines,
                "lines_expected": len(gt["lines"]),
                "seconds": round(seconds, 2),
                "failed": failed,
                "error": error,
            }
        )

    ok = [r for r in results if not r["failed"]]
    payload = {
        "engine": ENGINE_NAME,
        "engine_version": version,
        "dataset_version": manifest["version"],
        "date": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "results": results,
        "summary": {
            "documents": len(results),
            "failures": len(results) - len(ok),
            "mean_cer": round(sum(r["cer"] for r in ok) / len(ok), 4) if ok else None,
            "mean_wer": round(sum(r["wer"] for r in ok) / len(ok), 4) if ok else None,
            "total_seconds": round(sum(r["seconds"] for r in results), 2),
        },
    }
    out_path = ROOT / "dataset" / "evaluation" / "ocr_benchmark.json"
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"{'doc':<16}{'difficulty':<10}{'CER':>8}{'WER':>8}{'conf':>8}{'lines':>8}{'secs':>8}  status")
    for r in results:
        conf = f"{r['mean_confidence']:.3f}" if r["mean_confidence"] is not None else "n/a"
        status = f"FAILED {r['error']}" if r["failed"] else "ok"
        print(
            f"{r['id']:<16}{r['difficulty']:<10}{r['cer']:>8.4f}{r['wer']:>8.4f}"
            f"{conf:>8}{r['lines_detected']:>4}/{r['lines_expected']:<3}{r['seconds']:>8.2f}  {status}"
        )
    print(f"wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
