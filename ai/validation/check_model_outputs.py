"""Validate the live model outputs (STEP 08 evidence, no DB writes).

Reads dataset/model_outputs/*.json, normalizes values, runs the rule
engine against the DEMO reference chain, checks each record against the
other two for duplicates, and writes dataset/evaluation/validation_check.json.

Usage (from repo root; backend venv not required — pure stdlib):
    python ai\\validation\\check_model_outputs.py
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

from ai.validation import (  # noqa: E402
    approval_blocked,
    demo_reference,
    duplicate_issue,
    find_duplicates,
    normalize_record,
    record_verdict,
    validate_record,
)


def main() -> int:
    manifest = json.loads((ROOT / "dataset" / "manifest.json").read_text(encoding="utf-8"))
    reference = demo_reference()
    outputs = {}
    for entry in manifest["documents"]:
        path = ROOT / "dataset" / "model_outputs" / f"{entry['id']}.json"
        outputs[entry["id"]] = json.loads(path.read_text(encoding="utf-8"))

    normalized = {doc_id: normalize_record(out.get("values", {})) for doc_id, out in outputs.items()}
    results = []
    for entry in manifest["documents"]:
        doc_id = entry["id"]
        out = outputs[doc_id]
        if out.get("failed"):
            results.append({"id": doc_id, "failed": True, "error_code": out.get("error_code")})
            print(f"{doc_id}: extraction FAILED ({out.get('error_code')}) — nothing to validate")
            continue
        norm = normalized[doc_id]["normalized"]
        issues = validate_record(norm, reference)
        others = [normalized[other]["normalized"] for other in outputs if other != doc_id]
        verdict_dup, matches = find_duplicates(norm, others)
        dup_issue = None
        if verdict_dup == "POSSIBLE_DUPLICATE":
            dup_issue = duplicate_issue(norm, matches)
            issues.append(dup_issue)
        verdict = record_verdict(issues)
        results.append(
            {
                "id": doc_id,
                "difficulty": entry["difficulty"],
                "verdict": verdict,
                "approval_blocked": approval_blocked(issues),
                "duplicate_check": verdict_dup,
                "duplicate_matches": [m.get("survey_number") for m in matches],
                "issues": [i.to_dict() for i in issues],
            }
        )
        print(f"{doc_id}: verdict={verdict} issues={len(issues)} duplicates={verdict_dup}")

    summary = {
        "ready": sum(1 for r in results if r.get("verdict") == "READY_FOR_APPROVAL"),
        "review": sum(1 for r in results if r.get("verdict") == "REVIEW_REQUIRED"),
        "blocked": sum(1 for r in results if r.get("verdict") == "BLOCKED"),
    }
    payload = {"reference": {"source": reference.source, "version": reference.version}, "results": results, "summary": summary}
    out_path = ROOT / "dataset" / "evaluation" / "validation_check.json"
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"summary={summary}")
    print(f"wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
