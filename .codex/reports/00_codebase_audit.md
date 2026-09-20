# Codebase and Live Supabase Audit

Date: 2026-09-20  
Scope: read-only audit requested by the first-run task. No application code, migrations, or production data were modified.

## Actual architecture

- Frontend: temporary React 19 + Vite QA application in `frontend/`, hash navigation, session-storage bearer token, and API client under `frontend/src/api/`. The permanent Stitch redesign is not yet integrated.
- Backend: FastAPI under `backend/app/`, versioned application routes under `/api/v1`, local bcrypt + PyJWT authentication, server-side RBAC, request IDs, structured error envelopes, and Supabase service-role access.
- Persistence: Supabase PostgreSQL plus private Storage bucket `land-record-documents`. The browser has no privileged database or storage access.
- Processing: repository-level `ai/` packages provide Tesseract OCR, PyMuPDF rendering, script detection/preprocessing, extraction evaluation, deterministic validation, duplicate checks, and confidence scoring. Backend adapters expose `extract_land_record()` with Gemini primary and OpenRouter fallback support.
- Execution: upload is synchronous through storage/metadata creation; processing is a FastAPI `BackgroundTasks` job. Demo mode injects fixture OCR/extraction stages while sharing validation, persistence, review, approval, and audit stages with live mode.

Important modules:

- `backend/app/auth`: configuration-backed JWT auth, registration, role checks, login rate limiter, and user store.
- `backend/app/documents`: upload validation, private storage, document metadata, extraction/validation reads.
- `backend/app/processing`: job state, atomic processing claim, pipeline orchestration, stale-job reconciliation.
- `backend/app/ai`: provider abstraction, Gemini/OpenRouter adapters, retry/failover, cache, prompt/schema mapping.
- `backend/app/reviews`: review tasks, corrections, revalidation, approval/rejection, audit writes.
- `backend/app/records`: search, dashboard aggregates, export, mock LRMS, typed persistence coercion.
- `ai/ocr`, `ai/validation`, `ai/confidence`, `ai/extract`: deterministic and benchmarkable document-processing components.

The current authorization behavior is shared-workspace semantics: any authenticated user can read documents/records; only `operator` can mutate workflow state. Ownership filtering is not implemented. This matches an institutional workspace, but that product decision should be stated explicitly in the authoritative documentation.

## API route map

Health routes are unversioned: `GET /health`, `/health/database`, `/health/ai`.

All other routes are under `/api/v1`:

- Auth: `POST /auth/login`, `POST /auth/register`, `POST /auth/logout`, `GET /auth/me`.
- Documents: `POST /documents` (operator), `GET /documents/{id}`, `GET /documents/{id}/status`, `GET /documents/{id}/extraction`, `GET /documents/{id}/validation`.
- Processing: `POST /documents/{id}/process` (operator; live/demo mode).
- Reviews: `POST /reviews`, `GET /reviews`, `GET /reviews/{id}`, `PATCH /reviews/{id}/fields/{field}`, `POST /reviews/{id}/complete` (all operator).
- Decisions/audit: `POST /records/{id}/approve`, `POST /records/{id}/reject`, `GET /records/{id}/audit` (operator).
- Records: `GET /records`, `GET /records/{id}`, `GET /records/{id}/export` (authenticated).
- Dashboards: `GET /dashboard/summary`, `/dashboard/processing`, `/dashboard/validation` (authenticated).
- Integration: `POST /integrations/mock-lrms` (operator; APPROVED records only; explicitly not a government integration).

The route implementation is broader than the old `backend/README.md` table, which still labels operator endpoints `verifier+`.

## Processing pipeline map

`POST /documents/{id}/process` validates mode and document state, atomically claims the document with a conditional update, creates a `PENDING` job, and schedules the background runner.

The runner performs:

`storage download → PDF/image render → conservative preprocessing → per-page script detection → Tesseract OCR with text/boxes/confidence → OCR persistence → provider-independent AI extraction → normalization → deterministic required/format/reference/geo/duplicate validation → typed land-record persistence → extracted fields and validation results → automatic review task when needed → document/job status updates → audit entries`.

Live and demo paths share all stages after OCR/extraction. AI retry/fallback is transient-error-only and cache keys include source, pipeline, route chain, prompt, and schema versions.

The confidence engine exists in `ai/confidence`, but the production pipeline does not call it. Persisted field confidence currently comes from extraction output; the OCR/extraction mean, validation caps, and record-level confidence routing are not integrated into the pipeline/API.

## Database table map

The migration set defines 12 application tables:

`roles` defines the role vocabulary used by `users.role` (there is intentionally no FK); `reference_data` is a self-parented vocabulary chain; `documents → processing_jobs` and `ocr_results`; `documents → land_records → extracted_fields`, `validation_results`, `review_tasks`, and `field_corrections`; `audit_logs` is polymorphic with a nullable user FK.

Constraints/indexes include immutable UUID keys, document-record uniqueness, one OCR row per document/page, field uniqueness per record, status CHECKs, approval pair consistency, timestamp ordering, foreign-key delete actions, search/status indexes, and append-only protections for audit/correction tables. RLS is enabled on all 12 tables with no permissive policies; the backend uses service-role access and enforces RBAC.

Live read-only probe results:

| Table/resource | Live rows | Result |
|---|---:|---|
| roles | 3 | reachable |
| users | 6 | 4 active operators, 2 active users |
| reference_data | 5 | reachable; DEMO reference chain |
| documents | 12 | reachable |
| processing_jobs | 14 | 12 succeeded, 2 failed |
| ocr_results | 14 | reachable |
| land_records | 11 | 7 review-required, 3 approved, 1 rejected |
| extracted_fields | 154 | reachable |
| validation_results | 22 | reachable |
| review_tasks | 10 | reachable |
| field_corrections | 1 | reachable |
| audit_logs | 77 | reachable; zero rows without actor |
| private bucket | 1 | `land-record-documents` exists |

The anonymous Supabase client returned zero rows for every application table, consistent with deny-by-default RLS. No configured Supabase MCP/schema tool was exposed in this task, so this live check used the repository's configured Supabase client in read-only mode; no SQL mutation was issued.

## Migration/live-schema differences

- The initial foundation migration intentionally creates `operator/verifier/admin`; the later two-role migration removes `verifier`, adds `user`, and narrows both CHECK constraints. Live state matches the later migration: roles are `user/operator/admin`, and user rows are only `operator/user`.
- `20260905130000_add_users_id_number.sql` is reflected in the live `users` columns, but `supabase/database.types.ts` is stale and omits `id_number` from Row/Insert/Update types. Its header also still describes generation immediately after the foundation migration.
- Documentation drift remains: `AGENTS.md`, `backend/README.md`, `03_USER_FLOW.md`, and parts of `02_PRD.md` retain retired `verifier` terminology. `11_SECURITY_DESIGN.md` still states that authorization waits for token expiry, while code now re-reads the database for privileged actions.
- Live data has no orphaned records, OCR rows, fields, validation rows, or reviews. Two documents have multiple historical processing jobs, and two approved records still have documents whose processing status is `REVIEW_REQUIRED`; this confirms the known document-status synchronization gap.

## Major security issues

1. `opencode.json` contains a plaintext Google API credential. It is ignored by Git and the value was not displayed, but it remains a local secret-exposure incident. Revocation/rotation is an external action still required.
2. CORS uses `allow_methods=["*"]`, `allow_headers=["*"]`, and `allow_credentials=True`; production deployment should use an explicit origin/method/header allow-list and HTTPS.
3. Login throttling is in-process and fixed-window. It resets on restart and is not shared across workers/instances; it is useful local protection, not deployment-grade abuse control.
4. All backend database operations use the Supabase service-role key. This is consistent with the current RLS design but gives the backend broad database authority; a least-privilege split remains a deployment hardening item.
5. Source documents remain private and there is no authenticated page/file rendering endpoint. The frontend can show metadata but cannot show the original scan/evidence image.

Positive controls verified in code/tests include server-only provider keys, upload type/size/magic-byte checks, generated storage paths, prompt-injection fencing, fail-closed retired-role handling, privileged role freshness checks, append-only audit access, and escaped record search wildcards.

## Major data-integrity and runtime risks

- Pipeline persistence is not transactional across OCR, land record, extracted fields, validation results, review task, audit, document status, and job status. Several `replace_*` operations are delete-then-insert, and correction/approval workflows perform multiple writes; mid-sequence failures can leave partial state.
- Processing claim occurs before job creation. If job creation fails, the document can remain `PROCESSING` without a corresponding job. `_finish` updates document status before marking the job `SUCCEEDED`, so short-lived polling inconsistency is possible.
- Automatic review creation failures are logged and swallowed, while the job can still succeed; a review-required record can therefore be left without its mandatory review task.
- Mock LRMS acceptance does not append an audit event, despite being a privileged external-facing action.
- Review listing has no server-side pagination. Dashboard methods fetch whole tables and aggregate in Python; duplicate checking also loads all record summaries. This is acceptable only at MVP scale.
- Storage cleanup after a database failure is best effort and there is no reconciliation path for orphaned objects.
- FastAPI `BackgroundTasks` is not a durable queue. A process crash loses in-flight work; startup marks stale jobs failed but does not resume them.
- The current application does not persist the combined confidence score or use it as a review-routing input. High model self-confidence can remain visible even when the independent confidence caps would require review.

## Existing test coverage

Backend tests cover auth/RBAC/rate limiting, upload validation/storage seams, provider parsing/retry/fallback/cache, OCR units and multilingual routing, deterministic validation/duplicates, confidence functions, processing, persistence coercion, review/approval/audit, records, error envelopes, demo mode, and security boundaries. `test_supabase_live.py` is opt-in and skipped by default.

Current verification in this environment:

- Backend: `246 passed, 5 failed, 1 skipped` in `python -m pytest -q`. All five failures are multilingual OCR tests because `tesseract.exe` is not installed/on PATH in this environment; the project-local traineddata exists, but the external Tesseract binary dependency is missing.
- Frontend: `20 test files, 163 passed`; `npm run typecheck`, `npm run lint`, and `npm run build` all pass.
- Live database: read-only service-role/anonymous probes passed as described above; no live end-to-end mutation test was run during this audit.

Coverage is strong for pure rules and in-memory API behavior, but weak for transactional failure injection across the complete pipeline, durable worker recovery, authenticated source rendering, production multi-worker rate limiting, and calibrated confidence evaluation.

## Top implementation dependencies

1. Restore and pin the Tesseract executable in local/hosted environments, then rerun the multilingual/OCR suite.
2. Regenerate `supabase/database.types.ts` from the current live schema, including `id_number` and any future migration changes.
3. Decide and document shared-workspace versus ownership semantics before adding authorization filters.
4. Add transactional/idempotent persistence boundaries and explicit recovery for claim/job creation and partial pipeline writes.
5. Integrate persisted/calibrated confidence with review routing, or document the current extraction-confidence limitation as deliberate scope.
6. Add authenticated source-document rendering/download with strict authorization, range/size controls, and safe content handling.
7. Close secret rotation, production CORS, and multi-instance rate-limit deployment actions.
8. Replace DEMO-only reference data and expand the stable evaluation set toward real legacy scans/handwriting before making accuracy claims.
