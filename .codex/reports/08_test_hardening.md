# Backend Test Hardening

## Scope

The existing backend suite was mapped against the requested highest-risk workflows. No Gemini, Supabase, or other external API key was used; all provider tests use mocked transports and injected fakes.

This pass added only regression coverage for gaps found in the existing suite:

- API-boundary expired bearer tokens return the implemented `401 TOKEN_EXPIRED` contract.
- A malformed provider response fails the processing job diagnostically and leaves no record, extracted fields, or validation rows.
- Repeated rejection returns `409 RECORD_FINALIZED` and does not create a second audit event.

The existing suite already covered login/registration, invalid and expired token primitives, disabled accounts, roles and rate limiting; upload MIME/magic/size/corrupt-source/page rendering; provider fallback/timeout/malformed responses; processing concurrency, stale jobs, rollback and retry; validation and duplicate signals; review correction/approval/rejection; audit events; and database-persistence failure simulation.

## Verification

Focused security/workflow suite:

```text
210 passed, 1 warning
```

Full backend suite:

```text
287 passed, 1 skipped, 5 failed, 1 warning
```

The five failures are the pre-existing multilingual OCR tests that require the external Tesseract executable (`TesseractNotFoundError` on this machine): four script-routing cases and one original-script preservation case. They are unrelated to this test pass.

`pytest-cov` is not installed in the configured backend virtual environment, so coverage percentages were not measured or claimed.

## Remaining

- Install/configure Tesseract and its language data before treating the five OCR failures as executable-suite regressions.
- Run the optional live Supabase tests only in an explicitly configured environment; the normal suite keeps live access disabled.
