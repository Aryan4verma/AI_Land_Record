# Demo Mode

Demo Mode is a controlled demonstration path for known documents. It supplies
precomputed OCR and extraction results instead of contacting an external AI or
OCR service, while the real application handles everything after that stage.

It is **not** fake data and it is **not** live AI processing. It is the real
workflow with one stage replayed from a fixture.

## Why it exists

A live demonstration should not depend on provider quota, network conditions or
model variability. Demo Mode makes the demonstration deterministic: the same
document always produces the same result, with no external call.

## What runs, and what does not

```
upload  ->  storage  ->  PDF render  ->  [ OCR ]  ->  [ extraction ]  ->  validation
         ->  confidence  ->  land record  ->  extracted fields  ->  review
         ->  correction  ->  approval  ->  audit
                 ^                ^
                 |                |
        replayed from fixture in Demo Mode; everything else is the same code
```

**Does not run in Demo Mode:** Gemini, OpenRouter, Groq, NVIDIA, any external
LLM or OCR service. The demo path never attempts a call and then falls back —
the fixture-backed stages are injected before the pipeline starts.

**Still runs in Demo Mode:** authentication, RBAC, file upload and validation,
private storage, PDF rendering, the deterministic validation engine, confidence
handling, database persistence, review, correction, approval and audit.

## Enabling and disabling

Server-side only. The frontend cannot enable it.

```
DEMO_MODE=true      # backend/.env  -> selector appears, demo requests accepted
DEMO_MODE=false     # production default -> selector hidden AND requests refused
```

With `DEMO_MODE=false` the backend answers `403 DEMO_MODE_DISABLED` regardless
of what the client sends. Security does not depend on the UI hiding a control.

Optional: `DEMO_FIXTURE_DIRECTORY` overrides the fixture location (defaults to
`<repo>/demo/fixtures`).

## Using it

1. Sign in as an **operator** (read-only users cannot upload or process).
2. On Upload, choose **Processing mode → Demo**.
3. Upload the canonical demo PDF through the normal upload form.
4. Processing runs, and the result appears in the ordinary result, review and
   audit screens.

Uploading any other document in Demo Mode returns:

> This document is not one of the configured demo documents. Switch to Live
> processing to process it normally.

Demo Mode never guesses which fixture a file might be.

## How a document is recognised

By the **SHA-256 of its bytes**, never by filename. The upload path already
stores that checksum on the `documents` row, so matching is a lookup against
`demo/fixtures/manifest.json`.

- A renamed copy of the canonical document still matches.
- An unrelated file never matches, whatever it is called.

## Fixtures

```
demo/fixtures/
├── manifest.json                     fixture id, SHA-256, page count, versions
└── doc10_rtc_hindi_scan/
    ├── document.pdf                  the canonical demonstration document
    ├── ocr_result.json               precomputed OCR pages, lines, confidence
    ├── extraction_result.json        precomputed field extraction
    └── README.md
```

The canonical document is a **SPECIMEN** land record: fictitious authority,
names and identifiers, marked SPECIMEN on the page. It is not a copy of any
government instrument.

## Rebuilding a fixture

```
backend\.venv\Scripts\python scripts\build_demo_fixture.py
```

This is the **only** step that contacts an external provider, and only once
during development. `--ocr-only` rebuilds the OCR half at zero cost.

## Auditability

Every demo run is recorded in the ordinary audit trail:

```json
{
  "execution_mode": "demo",
  "fixture_id": "doc10_rtc_hindi_scan",
  "external_ai_calls": 0,
  "external_ocr_calls": 0,
  "provider": "demo-fixture"
}
```

`processing_jobs.pipeline_version` is `v1-demo` for demo runs and `v1` for live
runs, so the two paths are distinguishable in the database without a schema
change. Live runs are never tagged demo.

## Known behaviour of the current canonical document

The fixture is a genuine capture: the AI misread three identifiers on the worn
scan (`survey_number` 445/2 for 145/2, `khasra_number` 76 for 78,
`khata_number` 23 for 123). Those values are preserved exactly as extracted —
they are not silently corrected, because correcting them is the reviewer's job
and demonstrating that is the point.

Note that this document currently validates **clean** (`READY_FOR_APPROVAL`,
zero findings): its village/tehsil/district match the seeded DEMO reference
data, and the misread identifiers are still format-valid, so no rule fires. The
demonstration therefore shows the straight-through path. To demonstrate the
review-and-correction path, a fixture whose values genuinely trip a validation
rule is needed — do not force a failure in the UI.
