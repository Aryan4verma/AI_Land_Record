"""Repeatable end-to-end evaluation (STEP 14, 12 section 11).

Runs every stage with the project's own CLIs and aggregates the four
stage reports into dataset/evaluation/REPORT.md plus a timestamped
report_*.json (history accumulates; REPORT.md is the rolling latest).

Freshness: free deterministic stages (OCR benchmark*, evaluate,
validation check, confidence score) always rerun. The extraction stage
spends live Gemini quota, so it reruns ONLY when outputs are missing,
failed, or stale (model/prompt mismatch) — otherwise existing
model_outputs are reused and the report says so explicitly.

*OCR reruns Tesseract locally: no quota, seconds of CPU.

Usage (from repo root):
    python scripts\\evaluate_all.py [--dry-run] [--force-ocr] [--force-extract] [--skip-pytest]

--dry-run prints the plan including the exact live-call count, then exits.
"""
import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AI_PY = ROOT / "ai" / ".venv" / "Scripts" / "python.exe"
BE_PY = ROOT / "backend" / ".venv" / "Scripts" / "python.exe"
DATASET = ROOT / "dataset"
EVAL = DATASET / "evaluation"


def run(cmd, cwd, step):
    print(f"--- {step}: {' '.join(cmd[3:])} ---", flush=True)
    completed = subprocess.run(cmd, cwd=cwd)
    if completed.returncode != 0:
        raise SystemExit(f"stage failed: {step} (exit {completed.returncode})")


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def backend_env(name, default=""):
    for line in (ROOT / "backend" / ".env").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith(name + "="):
            return line.split("=", 1)[1].strip().strip("'\"")
    return default


def prompt_version():
    text = (ROOT / "backend" / "app" / "ai" / "prompt.py").read_text(encoding="utf-8")
    match = re.search(r'PROMPT_VERSION\s*=\s*"([^"]+)"', text)
    return match.group(1) if match else "unknown"


def main() -> int:
    args = _parse()
    manifest = read_json(DATASET / "manifest.json")
    docs = manifest["documents"]
    model = backend_env("AI_MODEL", "gemini-2.0-flash") or "gemini-2.0-flash"
    prompt_v = prompt_version()

    missing_ocr = [d["id"] for d in docs if not (DATASET / "ocr_outputs" / f"{d['id']}.json").is_file()]
    stale_extract, missing_extract = [], []
    for d in docs:
        path = DATASET / "model_outputs" / f"{d['id']}.json"
        if not path.is_file():
            missing_extract.append(d["id"])
            continue
        try:
            out = read_json(path)
        except ValueError:
            missing_extract.append(d["id"])
            continue
        if out.get("failed") or out.get("model") != model or out.get("prompt_version") != prompt_v:
            stale_extract.append(d["id"])
    need_extract = sorted(set(missing_extract + stale_extract)) if not args.force_extract else [d["id"] for d in docs]
    need_ocr = ([d["id"] for d in docs] if args.force_ocr else missing_ocr)

    print(f"dataset={manifest['version']} docs={len(docs)} model={model} prompt={prompt_v}")
    print(f"OCR rerun: {need_ocr or 'none (reuse)'}")
    print(f"extraction rerun: {need_extract or 'none (reuse)'} "
          f"-> {len(need_extract)} live Gemini call(s) if executed")
    if args.dry_run:
        print("dry run: no stages executed")
        return 0

    if not args.skip_pytest:
        run([str(BE_PY), "-m", "pytest", "-q"], ROOT / "backend", "pytest")
    if need_ocr:
        run([str(AI_PY), "-m", "ai.ocr.benchmark"], ROOT, "ocr-benchmark")
    if need_extract:
        run([str(BE_PY), "ai/extract/run_extraction.py"], ROOT, "extraction")
    run([str(BE_PY), "ai/extract/evaluate.py"], ROOT, "extraction-eval")
    run([str(BE_PY), "ai/validation/check_model_outputs.py"], ROOT, "validation-check")
    run([str(BE_PY), "ai/confidence/score_outputs.py"], ROOT, "confidence-score")

    report = aggregate(manifest, model, prompt_v, need_extract)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    (EVAL / f"report_{stamp}.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (EVAL / "REPORT.md").write_text(render_markdown(report), encoding="utf-8")
    print(f"wrote evaluation/report_{stamp}.json + evaluation/REPORT.md")
    return 0


def _parse():
    parser = argparse.ArgumentParser(description="Repeatable project evaluation")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force-ocr", action="store_true")
    parser.add_argument("--force-extract", action="store_true")
    parser.add_argument("--skip-pytest", action="store_true")
    return parser.parse_args()


def aggregate(manifest, model, prompt_v, reran_extract):
    docs = manifest["documents"]
    ocr = read_json(EVAL / "ocr_benchmark.json")
    ext = read_json(EVAL / "extraction_eval.json")
    val = read_json(EVAL / "validation_check.json")
    conf = read_json(EVAL / "confidence_report.json")

    providers = sorted({(r.get("provider"), r.get("model")) for r in ext["results"] if not r.get("failed")})
    field_stats: dict[str, dict[str, int]] = {}
    for record in ext["results"]:
        for name, item in (record.get("fields") or {}).items():
            slot = field_stats.setdefault(name, {"correct": 0, "total": 0})
            slot["total"] += 1
            if item.get("verdict") == "CORRECT":
                slot["correct"] += 1
    per_field = {name: round(s["correct"] / s["total"], 4) if s["total"] else None
                 for name, s in sorted(field_stats.items())}
    severities: dict[str, int] = {}
    for record in val["results"]:
        for issue in record.get("issues", []):
            sev = issue.get("severity", "UNKNOWN")
            severities[sev] = severities.get(sev, 0) + 1
    conf_flagged = sum(1 for r in conf["reports"] for f in r["fields"].values() if f["review_required"])
    conf_total = sum(len(r["fields"]) for r in conf["reports"])
    ocr_latency = {r["id"]: r.get("seconds") for r in ocr["results"]}
    ext_latency = {}
    for d in docs:
        out = read_json(DATASET / "model_outputs" / f"{d['id']}.json")
        ext_latency[d["id"]] = out.get("elapsed_seconds")
    review_docs = sum(1 for r in val["results"] if r.get("verdict") in ("REVIEW_REQUIRED", "BLOCKED"))
    return {
        "date": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "dataset_version": manifest["version"],
        "documents": len(docs),
        "provider": [f"{p}/{m}" for p, m in providers],
        "model": model,
        "prompt_version": prompt_v,
        "schema_version": "v1",
        "extraction_reran_live_calls": len(reran_extract),
        "field_accuracy_mean": ext["summary"].get("mean_accuracy"),
        "field_accuracy_per_field": per_field,
        "verdict_totals": ext["summary"].get("verdict_totals", {}),
        "failures": {
            "ocr": [r["id"] for r in ocr["results"] if r.get("failed")],
            "extraction": [r["id"] for r in ext["results"] if r.get("failed")],
        },
        "latency_seconds": {"ocr_per_doc": ocr_latency, "extraction_per_doc": ext_latency,
                            "api": "not measured by this command (see pytest for functional API coverage)"},
        "review_rate_by_record": round(review_docs / len(docs), 4) if docs else None,
        "confidence_flagged_fields": f"{conf_flagged}/{conf_total}",
        "validation": {"summary": val["summary"], "severity_counts": severities,
                       "reference": val.get("reference")},
        "explicit_gaps": [
            "no train/test split yet — dataset_v1 doubles as dev and eval",
            "handwriting and real legacy scans absent from dataset_v1",
            "API latency not measured; human-review timing not measured",
            "confidence bands uncalibrated by design (operational routing only)",
            "live multi-provider failover proven once via script, not in this report",
        ],
    }


def render_markdown(report):
    lines = [
        "# Evaluation Report (STEP 14, 12 section 11)",
        "",
        f"Date: {report['date']} | Dataset: {report['dataset_version']} "
        f"({report['documents']} docs) | Provider: {', '.join(report['provider']) or 'none succeeded'}",
        f"Model: {report['model']} | Prompt: {report['prompt_version']} | Schema: {report['schema_version']}",
        f"Live extraction calls this run: {report['extraction_reran_live_calls']}",
        "",
        "## Field accuracy",
        "",
        f"Mean: {report['field_accuracy_mean']} | Totals: {report['verdict_totals']}",
        "",
        "| Field | Accuracy |",
        "|-------|----------|",
    ]
    lines += [f"| {name} | {acc} |" for name, acc in report["field_accuracy_per_field"].items()]
    lines += [
        "",
        "## Failures",
        "",
        f"OCR: {report['failures']['ocr'] or 'none'} | "
        f"Extraction: {report['failures']['extraction'] or 'none'}",
        "",
        "## Latency (seconds)",
        "",
        f"OCR per doc: {report['latency_seconds']['ocr_per_doc']}",
        f"Extraction per doc: {report['latency_seconds']['extraction_per_doc']}",
        f"API: {report['latency_seconds']['api']}",
        "",
        "## Review rate",
        "",
        f"Records needing review: {report['review_rate_by_record']} | "
        f"Confidence-flagged fields: {report['confidence_flagged_fields']}",
        "",
        "## Validation",
        "",
        f"{report['validation']['summary']} | severities: {report['validation']['severity_counts']} | "
        f"reference: {report['validation']['reference']}",
        "",
        "## Explicit gaps (not measured / not claimed)",
        "",
    ]
    lines += [f"- {gap}" for gap in report["explicit_gaps"]]
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
