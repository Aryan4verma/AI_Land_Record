# Processing Lifecycle Reliability Audit

Date: 2026-09-21

## Scope and observed lifecycle

The implemented lifecycle is:

```text
upload
  → documents.UPLOADED
POST /process
  → conditional document claim to PROCESSING
  → processing_jobs.PENDING
background worker
  → processing_jobs.RUNNING
  → storage download → OCR → extraction → normalization/validation
final PostgreSQL RPC
  → OCR + land record + extracted fields + validation + review + audit
  → document.REVIEW_REQUIRED / VALIDATION_FAILED / READY_FOR_APPROVAL
  → processing_jobs.SUCCEEDED
failure
  → processing_jobs.FAILED + document.FAILED (only while still PROCESSING)
review workflow
  → land_records.APPROVED / REJECTED
```

`PREPROCESSING`, `OCR_PROCESSING`, `EXTRACTION`, `VALIDATION`, and `EXTRACTED`
exist in the database status vocabulary, but this pipeline persists only the
aggregate `PROCESSING` state until the final result. The frontend correctly
renders an aggregate stepper and does not claim per-stage events or timings.
Approval/rejection is authoritative on `land_records`; `documents.processing_status`
remains the ingestion/processing status. The API returns the persisted document
status rather than inferring approval from frontend state.

## Findings and fixes

### Claim/job acceptance race — fixed

The conditional document claim already serialized concurrent process requests,
but a failure after the claim and before job insertion could strand the document
in `PROCESSING` with no job. The endpoint now resolves demo fixtures before the
claim and conditionally restores the previous status when job creation fails.
If job insertion is ambiguous, it checks for an active job and retains the
claim rather than allowing a retry to create duplicate processing.

### Restart reconciliation mismatch — fixed

The previous startup reconciler marked stale jobs failed but left their
documents in `PROCESSING`, making normal retry impossible. New migration
`20260921100000_processing_lifecycle_hardening.sql` adds
`public.reconcile_stale_processing_jobs()`. It atomically marks stale
`PENDING`/`RUNNING` jobs as `FAILED` and changes only matching
`PROCESSING` documents to `FAILED`. It is idempotent, preserves jobs/audits/data,
uses no dynamic SQL, pins `search_path`, and grants execution only to
`service_role`.

### Diagnosability — fixed

`GET /api/v1/documents/{id}/status` still returns the original `document_id`
and `status` fields, and now includes the latest job id/status, safe error code,
and start/completion timestamps when available. Raw provider error text is not
exposed through this endpoint.

### Duplicate processing — verified

The database conditional claim prevents two concurrent requests from creating
two jobs or spending a second AI call. A completed job cannot be reprocessed
through the endpoint when its document/record is finalized. The atomic result
RPC is retry-safe and refuses a non-running job or a terminal land record.

### Failure, timeout, and restart behavior

Storage, OCR, provider, validation, and persistence exceptions are classified
into a failed job and retryable document state. Provider adapters already apply
configured HTTP timeouts; OCR failures are caught per page. The background
worker does not silently retry external calls. A process restart makes in-flight
jobs diagnosable as `SERVER_RESTARTED` and retryable after the new migration is
applied. No billing subsystem exists in the repository; no duplicate billing
path was found.

## Transition review

- `UPLOADED`, `FAILED`, `VALIDATION_FAILED`, `EXTRACTED`, `REVIEW_REQUIRED`,
  and `READY_FOR_APPROVAL` are accepted retry inputs.
- `PROCESSING`, `APPROVED`, and `REJECTED` are rejected by the process route.
- The conditional claim is the concurrency control; the initial status read is
  advisory only.
- Final result persistence requires a `RUNNING` job and `PROCESSING` document,
  and validates verdict/document-state pairs in PostgreSQL.
- Successful final persistence updates the document result state and job to
  `SUCCEEDED` in the same database transaction, so a successful job cannot
  remain stuck in `PROCESSING` after the RPC returns.
- Review approval/rejection uses server-side operator authorization and
  updates `land_records`; its audit entry is append-only. The separate
  document processing status is intentionally not used as the record approval
  source of truth.

## Deployment and verification notes

The new migration is ordered after the atomic persistence migration and must be
applied to the hosted Supabase project before deploying this backend. The
connected Supabase tooling available in this task allowed live read-only
inspection but did not expose SQL migration execution, so live application of
the new function is not claimed.

Focused verification:

- Backend processing/document tests: **38 passed**.
- Frontend processing/upload/dashboard tests: **34 passed**.
- Full frontend suite: **163 passed** across 20 test files.
- Frontend TypeScript check: passed.
- Frontend production build: passed.
- Python compilation and `git diff --check`: passed.

The full backend suite completed at **265 passed, 5 failed, 1 skipped**. All
five failures are the known multilingual OCR tests that require `tesseract.exe`
on PATH; no processing-lifecycle test failed.

## Remaining

- Apply and smoke-test migrations `20260920140000_atomic_processing_persistence.sql`
  and `20260921100000_processing_lifecycle_hardening.sql` against the live
  Supabase project before deployment.
- If detailed per-stage progress is later required, add persisted stage events
  deliberately; this pass does not invent a second state machine.
