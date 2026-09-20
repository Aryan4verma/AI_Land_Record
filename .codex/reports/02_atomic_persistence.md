# Atomic Processing Persistence

Date: 2026-09-20

## Problem found

The processing pipeline previously wrote OCR rows, land records, extracted
fields, validation results, document state, review tasks, job completion, and
completion audit entries through separate Supabase requests. A failure after
one of those requests could leave partial business results behind while the
job was later marked failed.

## Implemented boundary

Added migration
`supabase/migrations/20260920140000_atomic_processing_persistence.sql` with
the `public.persist_processing_result(...)` PostgreSQL function.

The function atomically commits:

- replacement OCR results;
- land-record upsert, protected by the existing one-record-per-document
  unique constraint;
- extracted fields and validation results replacement;
- final document processing status;
- review-task creation/reuse and its audit event;
- job success state;
- processing-completed audit event.

The function uses typed UUID/TEXT parameters, validates lifecycle values and
JSON shapes, converts payloads through typed `jsonb_to_record*` definitions,
uses no dynamic SQL, is `SECURITY INVOKER`, pins `search_path`, and grants
execution only to `service_role`.

The long OCR/AI work and the initial `RUNNING`/`PROCESSING` state remain
outside the transaction intentionally. Holding a database transaction across
file download, OCR, and external AI calls would create long locks and worsen
recovery. The final result commit is the atomic persistence unit. Failure
reconciliation separately marks the job failed and only changes the document
to `FAILED` if it is still `PROCESSING`.

Retries are safe: OCR/child rows are replaced as a unit, the land record is
upserted by document, open review tasks are reused, and a repeated call after
the same job already succeeded returns the existing record without duplicating
review or completion-audit rows. Terminal approved/rejected records cannot be
overwritten by a retry.

## Tests

Added failure-injection coverage for:

1. complete success;
2. failure before persistence during OCR;
3. OCR persistence failure;
4. land-record persistence failure;
5. extracted-field persistence failure;
6. validation persistence failure;
7. completion-audit failure;
8. retry after a failed atomic commit;
9. duplicate process-request serialization (existing atomic claim coverage).

Every final-persistence failure asserts no land record, OCR rows, extracted
fields, validation rows, review task, or completion audit remains.

## Verification

- Latest processing, typed-persistence, and demo tests: `84 passed`.
- Processing plus document regression tests: `100 passed`.
- Migration static validation passed: ordered file, balanced transaction,
  function/security/grant checks, and no dynamic SQL.
- Python compilation passed.
- Full backend suite: `262 passed, 5 failed, 1 skipped`; all five failures are
  the pre-existing multilingual OCR/Tesseract tests because `tesseract.exe`
  is unavailable on PATH.

## Deployment note

The new migration must be applied to the hosted Supabase project before the
updated backend workers are deployed. The current task surface does not expose
the Supabase SQL/migration execution tool, so the hosted RPC itself was not
applied or claimed as live-verified here. Until deployment, the old backend
must remain in use; do not mix the new worker with a database missing the
function.
