"""Field-by-field extraction evaluation (05 section 10, 12 section 4).

Compares dataset/model_outputs/<id>.json against
dataset/ground_truth/<id>_record.json and classifies every target field:
CORRECT / INCORRECT / MISSING / HALLUCINATED / PARTIALLY_CORRECT.
Writes dataset/evaluation/extraction_eval.json and prints a table.

Usage (from repo root):
    python ai\\extract\\evaluate.py
"""
import difflib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

VERDICTS = ("CORRECT", "INCORRECT", "MISSING", "HALLUCINATED", "PARTIALLY_CORRECT")

_STRICT_FIELDS = frozenset(
    {
        "survey_number",
        "khasra_number",
        "khata_number",
        "mutation_number",
        "registration_number",
        "record_date",
    }
)


def normalize(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


def _numbers_equal(expected: object, got: object) -> bool:
    try:
        return abs(float(str(expected)) - float(str(got))) < 1e-9
    except (TypeError, ValueError):
        return False


def classify_field(expected: object, got: object, field_name: str = "") -> str:
    """Deterministic verdict for one field. No LLM involved.

    Identifiers (survey/khasra/khata/mutation/registration numbers, dates)
    are strict: any difference is INCORRECT, never PARTIALLY_CORRECT — a
    near-miss identifier points at a different parcel/record.
    """
    if expected is None:
        return "CORRECT" if got is None else "HALLUCINATED"
    if got is None:
        return "MISSING"
    if field_name == "area" and _numbers_equal(expected, got):
        return "CORRECT"
    exp, actual = normalize(expected), normalize(got)
    if exp == actual:
        return "CORRECT"
    if field_name in _STRICT_FIELDS:
        return "INCORRECT"
    if exp and actual and (exp in actual or actual in exp):
        return "PARTIALLY_CORRECT"
    if difflib.SequenceMatcher(None, exp, actual).ratio() >= 0.8:
        return "PARTIALLY_CORRECT"
    return "INCORRECT"


def evaluate_record(gt_fields: dict, output: dict) -> dict:
    """Compare one model output against its record ground truth."""
    if output.get("failed"):
        return {
            "failed": True,
            "error_code": output.get("error_code"),
            "fields": {},
            "counts": {},
            "accuracy": None,
        }
    values = output.get("values", {})
    per_field = {}
    counts: dict[str, int] = {}
    for name, expected in gt_fields.items():
        if name == "id":
            continue
        verdict = classify_field(expected, values.get(name), name)
        per_field[name] = {"expected": expected, "got": values.get(name), "verdict": verdict}
        counts[verdict] = counts.get(verdict, 0) + 1
    total = sum(counts.values())
    accuracy = round(counts.get("CORRECT", 0) / total, 4) if total else None
    return {"failed": False, "fields": per_field, "counts": counts, "accuracy": accuracy}


def main() -> int:
    manifest = json.loads((ROOT / "dataset" / "manifest.json").read_text(encoding="utf-8"))
    results = []
    for entry in manifest["documents"]:
        doc_id = entry["id"]
        gt = json.loads((ROOT / "dataset" / "ground_truth" / f"{doc_id}_record.json").read_text(encoding="utf-8"))
        out_path = ROOT / "dataset" / "model_outputs" / f"{doc_id}.json"
        output = json.loads(out_path.read_text(encoding="utf-8")) if out_path.is_file() else {"failed": True, "error_code": "NO_OUTPUT"}
        verdict = evaluate_record(gt, output)
        verdict.update(
            {
                "id": doc_id,
                "difficulty": entry["difficulty"],
                "provider": output.get("provider"),
                "model": output.get("model"),
                "elapsed_seconds": output.get("elapsed_seconds"),
            }
        )
        results.append(verdict)

    ok = [r for r in results if not r["failed"]]
    accuracies = [r["accuracy"] for r in ok if r["accuracy"] is not None]
    totals: dict[str, int] = {}
    for record in ok:
        for verdict, count in record["counts"].items():
            totals[verdict] = totals.get(verdict, 0) + count
    payload = {
        "dataset_version": manifest["version"],
        "date": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "results": results,
        "summary": {
            "documents": len(results),
            "failures": len(results) - len(ok),
            "mean_accuracy": round(sum(accuracies) / len(accuracies), 4) if accuracies else None,
            "verdict_totals": totals,
        },
    }
    out_path = ROOT / "dataset" / "evaluation" / "extraction_eval.json"
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"{'doc':<14}{'difficulty':<10}{'accuracy':>10}{'breakdown'}")
    for record in results:
        if record["failed"]:
            print(f"{record['id']:<14}{record['difficulty']:<10}{'FAILED':>10}  {record.get('error_code')}")
            continue
        acc = f"{record['accuracy']:.4f}" if record["accuracy"] is not None else "n/a"
        breakdown = " ".join(f"{k}={v}" for k, v in sorted(record["counts"].items()))
        print(f"{record['id']:<14}{record['difficulty']:<10}{acc:>10}  {breakdown}")
    print(f"wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
