# Demo fixture: doc10_rtc_hindi_scan

Canonical demonstration document for Demo Mode.

- SHA-256: `6dd632cdeddfc7e78138cf818ab9396730f77b6092eced7b5618a51b140fd9f5`
- Size: 624612 bytes
- Pages: 1
- OCR language resolved: `hin+eng`
- Extraction provider (development-time): `gemini` / `gemini-3.6-flash`

## What this is

A SPECIMEN land record. The issuing authority, names and identifiers are
fictitious; the page is marked SPECIMEN. It is not a copy of any government
instrument.

## How it is used

At runtime Demo Mode reads `ocr_result.json` and `extraction_result.json` and
feeds them into the ordinary pipeline. Validation, confidence, persistence,
review, approval and audit all run exactly as in Live Mode. **No external AI
or OCR service is contacted.**

## Rebuilding

```
backend\.venv\Scripts\python scripts\build_demo_fixture.py
```

That is the only step that calls an external provider, and only once.
`--ocr-only` rebuilds the OCR half at zero cost.
