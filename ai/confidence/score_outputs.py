"""Score the dataset model outputs (STEP 09 evidence).

Reads dataset/ocr_outputs/<id>.json (OCR line confidences),
dataset/model_outputs/<id>.json (values + extraction confidences) and
dataset/evaluation/validation_check.json (validation outcomes), then writes
dataset/evaluation/confidence_report.json with per-field scores, bands,
review flags and explanatory reasons.

Usage (from repo root; pure stdlib):
    python ai\\confidence\\score_outputs.py
"""
import json
import sys
from pathlib import Path


def _ensure_root() -> Path:
    root = Path(__file__).resolve().parents[2]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    return root


ROOT = _ensure_root()

from ai.confidence.engine import score_record  # noqa: E402


def main() -> int:
    manifest = json.loads((ROOT / "dataset" / "manifest.json").read_text(encoding="utf-8"))
    validation = json.loads((ROOT / "dataset" / "evaluation" / "validation_check.json").read_text(encoding="utf-8"))
    issues_by_doc = {r["id"]: r.get("issues", []) for r in validation.get("results", [])}

    reports = []
    for entry in manifest["documents"]:
        doc_id = entry["id"]
        model_path = ROOT / "dataset" / "model_outputs" / f"{doc_id}.json"
        if not model_path.is_file():
            print(f"{doc_id}: no model output — skipped")
            continue
        output = json.loads(model_path.read_text(encoding="utf-8"))
        if output.get("failed"):
            print(f"{doc_id}: extraction FAILED ({output.get('error_code')}) — nothing to score")
            continue
        ocr = json.loads((ROOT / "dataset" / "ocr_outputs" / f"{doc_id}.json").read_text(encoding="utf-8"))
        ocr_lines = [line for page in ocr.get("pages", []) for line in page.get("lines", [])]
        values = output.get("values", {})
        confidences = {name: (output.get("fields", {}).get(name, {}) or {}).get("confidence") for name in values}
        record = score_record(doc_id, values, confidences, ocr_lines, issues_by_doc.get(doc_id, []))
        reports.append(record.to_dict())
        flagged = sum(1 for fc in record.fields.values() if fc.review_required)
        overall = f"{record.overall_score:.3f}" if record.overall_score is not None else "n/a"
        print(f"{doc_id}: overall={overall} {record.overall_band} review={record.review_required} fields_flagged={flagged}/14")

    out_path = ROOT / "dataset" / "evaluation" / "confidence_report.json"
    out_path.write_text(json.dumps({"reports": reports}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
