# Evaluation Report (STEP 14, 12 section 11)

Date: 2026-09-04T20:29:20+00:00 | Dataset: dataset_v1 (4 docs) | Provider: gemini/gemini-3.6-flash
Model: gemini-3.6-flash | Prompt: v1 | Schema: v1
Live extraction calls this run: 0

## Field accuracy

Mean: 0.9821 | Totals: {'CORRECT': 55, 'INCORRECT': 1}

| Field | Accuracy |
|-------|----------|
| area | 1.0 |
| area_unit | 1.0 |
| district | 1.0 |
| father_or_spouse_name | 1.0 |
| khasra_number | 1.0 |
| khata_number | 1.0 |
| land_classification | 1.0 |
| mutation_number | 1.0 |
| owner_name | 1.0 |
| record_date | 1.0 |
| registration_number | 1.0 |
| survey_number | 0.75 |
| tehsil | 1.0 |
| village | 1.0 |

## Failures

OCR: none | Extraction: none

## Latency (seconds)

OCR per doc: {'doc01_clean': 0.43, 'doc02_noisy': 0.64, 'doc03_faded': 0.33, 'step08_bad': 0.69}
Extraction per doc: {'doc01_clean': 41.3, 'doc02_noisy': 45.83, 'doc03_faded': 33.5, 'step08_bad': 5.71}
API: not measured by this command (see pytest for functional API coverage)

## Review rate

Records needing review: 0.75 | Confidence-flagged fields: 12/56

## Validation

{'ready': 1, 'review': 2, 'blocked': 1} | severities: {'WARNING': 8, 'ERROR': 1} | reference: {'source': 'demo-seed', 'version': 'v1'}

## Explicit gaps (not measured / not claimed)

- no train/test split yet — dataset_v1 doubles as dev and eval
- handwriting and real legacy scans absent from dataset_v1
- API latency not measured; human-review timing not measured
- confidence bands uncalibrated by design (operational routing only)
- live multi-provider failover proven once via script, not in this report
