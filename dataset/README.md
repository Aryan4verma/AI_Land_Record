# Dataset (05_DATASET_AND_ANNOTATION.md)

## Version

`dataset_v1` — see `manifest.json` for the document list. Ground truth is
generated alongside the synthetic documents, so it is exact by construction.

## Contents (v1 — OCR POC + extraction POC)

| ID | File | Difficulty | Attributes |
|----|------|-----------|------------|
| doc01_clean | `raw_documents/doc01_clean.pdf` (+ `.png`) | EASY | printed |
| doc02_noisy | `raw_documents/doc02_noisy.png` | MEDIUM | printed, noisy, skewed |
| doc03_faded | `raw_documents/doc03_faded.png` | HARD | printed, faded, low-contrast |

All three carry the same 13 English khata-style text lines. Every page is
labeled "SAMPLE LAND RECORD — FOR TESTING ONLY". All content is fictitious.

Each document additionally has:

- `ground_truth/<id>.json` — exact OCR reference text
- `ground_truth/<id>_record.json` — structured field values using the
  `04_DATA_DICTIONARY.md` names (`registration_number` is null: absent
  from the documents, so a non-null extraction there counts HALLUCINATED)
- `ocr_outputs/<id>.json` — Tesseract result (text + boxes + confidence)
- `model_outputs/<id>.json` — LLM extraction with provider/model/prompt/
  schema versions (`ai/extract/run_extraction.py`)

## Layout

```text
dataset/
├── manifest.json        # version + per-document file/GT/difficulty
├── raw_documents/       # source PDF/image files
├── preprocessed/        # reserved for preprocessing outputs
├── ocr_outputs/         # run_ocr.py result JSON per document
├── ground_truth/        # exact reference text + structured record values
├── model_outputs/       # LLM extraction outputs with version metadata
├── evaluation/          # ocr_benchmark.json, extraction_eval.json,
│                         validation_check.json, confidence_report.json,
│                         REPORT.md (rolling) + report_*.json (history)
└── README.md
```

## Evaluating

```powershell
python scripts\evaluate_all.py --dry-run   # plan + live-call count, no-op
python scripts\evaluate_all.py             # pytest + stages + REPORT.md
```

Free stages always rerun; extraction reruns only on missing/failed/stale
outputs (`--force-extract` overrides). step08_bad record ground truth is
provisional (see `ground_truth/step08_bad.SOURCE_NOTE.txt`).

## Regenerating

```powershell
python scripts\make_sample_docs.py   # any python with pillow + numpy
```

Deterministic (seeded RNG). To extend toward the 30–50 document target,
add real collected samples with human-verified ground truth, difficulty
labels, and dev/validation/test split metadata — never silently replace
existing evaluation results (05 sections 8, 12).
