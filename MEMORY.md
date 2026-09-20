# MEMORY.md

# Intelligent Land Record Digitization and Validation System

## Project Memory / AI Handoff Log

**Purpose:** Maintain current project state across AI tools, developers, and development sessions.

---

# 1. How This File Works

This file records the **current state of the project**, important decisions, completed work, known problems, and next actions.

Do NOT record every trivial action.

Record changes that affect:

```text
architecture
technology
scope
data
AI behavior
API
database
security
deployment
testing
```

---

# 2. Current Status

```text
Current Phase:
Master MVP reliability remediation COMPLETE (2026-09-07)

Current Milestone:
Provision operator/user accounts → P0 pipeline fixes → hosted deploy

Overall Status:
IN PROGRESS
```

---

# 3. Completed

```text
- AGENTS.md created (project rules, constraints, build order)
- Docs renamed from .md.txt to .md (cross-references now resolve)
- STEP 02 Database Foundation (2026-09-03):
  - Applied migration land_records_foundation: all 12 tables from
    09_DATABASE_SCHEMA.md with PKs/FKs/CHECKs/UNIQUEs/indexes/triggers
  - Applied migration land_records_foundation_fixes: pinned
    set_updated_at search_path + 3 covering indexes for FKs
  - RLS enabled on all 12 tables (deny-by-default, backend via service_role)
  - Seeded roles (operator/verifier/admin) + DEMO reference chain
    (district→tehsil→village, 2 land classifications, version v1)
  - Saved reproducible SQL in supabase/migrations/, TS types in
    supabase/database.types.ts, .env.example + .gitignore at root
- STEP 03 Backend Foundation (2026-09-03):
  - FastAPI skeleton in backend/app: config (env-only), logging with
    request IDs, standard error envelope, RequestID middleware, dev CORS
  - Supabase service_role client created at startup, stored on app.state
    (None when unconfigured; /health/database reports 503, app still boots)
  - Health endpoints: /health, /health/database, /health/ai + /docs live
  - Auth foundation: bcrypt passwords, PyJWT Bearer tokens, RBAC deps
    (operator<verifier<admin), login/logout/me under /api/v1/auth
  - 18/18 pytest passing; live local run verified all endpoints
- STEP 04 Document Upload and Storage (2026-09-03):
  - Private bucket land-record-documents (10 MB + PDF/PNG/JPEG/TIFF guards)
    via migration storage_documents_bucket
  - backend/app/documents: validation (ext/MIME/size/filename/magic bytes,
    SHA-256, generated storage paths), Supabase storage backend + document
    store (protocol-based, faked in tests), upload service (validates,
    stores bytes, inserts row, cleans up orphans on DB failure)
  - Endpoints: POST /api/v1/documents (201 {document_id, UPLOADED}),
    GET /api/v1/documents/{id}, GET /api/v1/documents/{id}/status
  - 31/31 pytest passing; live run verified routes + auth enforcement
- STEP 05 OCR POC (2026-09-04):
  - Engine: Tesseract 5.4.0 (UB-Mannheim, eng) via pytesseract; RapidOCR
    rejected (all releases need Python <3.13, we run 3.14)
  - ai/ocr: engine-neutral interface (text+boxes+confidence+pages),
    Tesseract adapter, PyMuPDF PDF rendering, run_ocr CLI, CER/WER benchmark
  - dataset_v1: 3 synthetic English khata-style docs (EASY/MEDIUM/HARD) +
    exact ground truth + manifest; per-doc JSON outputs saved
  - Benchmark: CER 0.0000/0.0032/0.0000, WER 0.0000/0.0222/0.0000,
    conf ~0.93-0.95, 13/13 lines each, <1 s/page, 0 failures
- STEP 06 AI Provider Layer (2026-09-04):
  - backend/app/ai: extract_land_record() interface, Gemini-first adapter
    (httpx REST, no SDK), classified ProviderError, prompt v1; 17 mocked
    checks; live smoke blocked then (retired default model 404)
  - Diagnostic: redacted failure details on ProviderError; test guards
    key redaction; root cause was model retirement, not auth/quota/bug
- STEP 07 Structured Extraction (2026-09-04):
  - ai/extract: OCR JSON -> extract_land_record() -> model_outputs with
    provider/model/prompt/schema versions; per-doc failure records
  - Structured record GT added (*_record.json, registration_number null)
  - Live on dataset_v1 (gemini-3.6-flash): 0 failures; accuracy
    1.0000/0.9286/1.0000, mean 0.9762; sole error is OCR-propagated
    survey_number on noisy doc ("4145/2" vs "145/2") — no hallucination
  - Strict-identifier eval rule adopted (near-miss IDs are INCORRECT)
  - 64/64 pytest passing (16 new offline connector/evaluator checks)
```

---

# 4. Currently Working On

```text
- Frontend ownership (Stitch design in existing React app): Stitch MCP
  reachable via direct MCP-over-HTTP (agent has no stitch_* tools; helper in
  temp dir); project/design tokens/Login spec retrieved; foundation landed
  (tokens.css, primitives.css, Button/TextInput/Alert/StatusBadge, Inter +
  JetBrains Mono). Next: Login screen prompt.
```

---

# 5. Next Tasks

```text
1. Hosted deploy execution: push backend (Procfile) + frontend (Vercel/Netlify
   + VITE_API_URL) with production env separation, then hosted smoke tests
2. Permanent frontend via Google Stitch (API contracts proven; QA app is
   disposable reference)
2. Grow dataset toward 30–50 with real collected samples + human-verified
   ground truth (incl. handwritten); re-benchmark OCR, try EasyOCR there
3. Seed one operator/verifier/admin user (password_hash) for local testing
   once SUPABASE_SERVICE_ROLE_KEY is available to the backend
4. Live end-to-end upload against hosted Supabase (needs service_role key)
```

---

# 6. Important Decisions

## Decision 2026-09-07 — Two user-facing roles (operator + user)

```text
Date: 2026-09-07
Decision:
The role model is now exactly two user-facing roles:
  user     read-only  (search/view records, extraction, validation, export)
  operator full workflow (upload, process, review, correct, complete,
           approve, reject, record audit, mock-LRMS)
`verifier` is RETIRED: every capability it gated moved to `operator`, and
the value is removed from both the hierarchy and the DB CHECK constraints,
so a stale verifier token or row fails closed (401) instead of being
reinterpreted. `admin` is kept as an INTERNAL escalation rank only —
never user-facing, never self-registerable, and no endpoint requires it.
Self-registration now creates `user` (was `operator`); operator accounts
are provisioned out-of-band only (13_DEPLOYMENT_RUNBOOK).
Role values are normalized to lowercase before every comparison.

Reason:
Requested product direction: one privileged workflow role plus a read-only
role. Note this INVERTS the meaning of `operator` — previously the least-
privileged role, now the most privileged. The two pre-existing live
accounts (both `operator`) therefore gained the review/approval workflow;
no user row was modified.

Migration safety (verified on live data before applying):
  users: 2 rows, both `operator`, 0 violate the new CHECK -> 0 rows changed
  users.role has NO FK to roles.name -> roles edits cannot cascade
  0 role strings embedded in audit_logs / review_tasks / field_corrections
  / validation_results -> audit history is role-agnostic and preserved
  roles table is decorative (only read by the /health/database ping)

Affected files:
backend/app/auth/{dependencies,router,schemas}.py,
backend/app/{reviews,records}/router.py,
supabase/migrations/20260907102842_two_role_architecture.sql,
frontend role guards + vocabulary, backend/frontend tests, docs 02/09/10/11/13
```

## Decision 2026-09-03 — DB access model

```text
Date: 2026-09-03
Decision:
RLS enabled on all tables with NO permissive policies (deny-by-default).
All data access goes through the FastAPI backend using the service_role
key; RBAC (operator/verifier/admin) is enforced server-side, not in RLS.
The rls_enabled_no_policy INFO lints are therefore intentional.

Reason:
Matches 11_SECURITY_DESIGN (least privilege, RBAC server-side, audit
protection) and keeps the MVP permission surface minimal.

Affected files:
supabase/migrations/20260903170000_land_records_foundation.sql
```

## Decision 2026-09-03 — History protection via FK actions

```text
Date: 2026-09-03
Decision:
land_records.document_id is UNIQUE + ON DELETE RESTRICT (one record per
document; documents with records cannot be deleted). All land_records
children CASCADE. All user references SET NULL. reference_data.parent_id
RESTRICT. audit_logs.entity_id is polymorphic UUID with no FK so audit
survives entity deletion. REVOKE UPDATE/DELETE on audit_logs and
field_corrections from anon/authenticated as defense in depth.

Reason:
Preserves audit/correction history (09 Rule 2, 11 section 7) while
allowing user offboarding without destroying records.

Affected files:
supabase/migrations/20260903170000_land_records_foundation.sql
```

## Decision 2026-09-03 — Value storage + role mapping

```text
Date: 2026-09-03
Decision:
extracted_fields.value stored as TEXT (NULL when MISSING/UNCERTAIN per
04 section 5); typed interpretation happens in app/validation layers.
users.role is TEXT CHECK mapped to roles.name (roles table holds the
permission sets). DEMO-prefixed reference seed data is explicitly NOT
real government data and must be replaced by the controlled reference
dataset before real validation.

Reason:
Preserves raw extraction verbatim for auditability; avoids inventing
regional formats (08 section 4); keeps seed data honest.

Affected files:
supabase/migrations/20260903170000_land_records_foundation.sql
```

## Decision 2026-09-03 — Local JWT auth for MVP

```text
Date: 2026-09-03
Decision:
MVP auth is local: bcrypt password hashes in users.password_hash plus
self-contained PyJWT Bearer tokens (sub=user id, role, exp). users.auth_id
is reserved for optional future Supabase Auth linkage. App refuses to boot
without AUTH_SECRET (fail-fast). Login returns identical 401 for unknown
user / wrong password / inactive account (no enumeration). Identity comes
only from the verified token; /me refetches the user and rejects
inactive/deleted accounts. RBAC hierarchy operator<verifier<admin via
require_role(). Auth endpoints live under /api/v1 per 10 section 15.

Reason:
Self-contained and testable without extra Supabase Auth configuration;
matches 11 sections 2-3 (backend-verified identity, server-side RBAC)
while keeping the Supabase Auth migration path open.

Affected files:
backend/app/auth/*, backend/app/main.py
```

## Decision 2026-09-03 — Upload storage design

```text
Date: 2026-09-03
Decision:
Source bytes live in private bucket land-record-documents (server-side
10 MB + MIME guards mirror the API validation); DB row in documents holds
file_name (sanitized display only), MIME, size, SHA-256 checksum, generated
storage_path documents/<uuid>/<uuid>.<ext>, uploaded_by + timestamps,
status UPLOADED. Validation order: extension/MIME cross-check, streaming
size cap, magic bytes, then store bytes, then insert row; DB failure after
upload triggers best-effort storage cleanup (no orphans). Upload requires
operator+ role; reads require any authenticated user. No processing_jobs
row and no pipeline trigger — that belongs to the AI pipeline step.

Reason:
Matches 03 upload flow, 04 document metadata, 10 section 3, 11 section 5
(generated internal names, content sniffing, no credential exposure).

Affected files:
backend/app/documents/*, backend/app/main.py, backend/app/config.py,
supabase bucket via migration storage_documents_bucket
```

## Decision 2026-09-04 — Tesseract 5 as POC OCR engine

```text
Date: 2026-09-04
Decision:
POC engine is Tesseract 5.4.0 (UB-Mannheim winget build, eng traineddata)
behind an engine-neutral interface (ai/ocr/base.py: text + boxes +
confidence + pages). RapidOCR was rejected only on installability (every
release requires Python <3.13; project runs 3.14); PaddlePaddle has no 3.14
wheels either. EasyOCR (GB-scale torch stack) stays a deferred alternative
for the handwritten benchmark. Evidence on dataset_v1 synthetic prints:
CER 0.0000/0.0032/0.0000, WER 0.0000/0.0222/0.0000, conf 0.93–0.95,
13/13 lines on all 3 docs, <1 s/page, zero failures. Verdict: good enough
to proceed to extraction POC + validation + human review. Explicitly NOT
proven for handwriting or real legacy scans — must re-benchmark when the
dataset grows toward 30–50 real samples.

Reason:
07 strategy demands measured selection on our data; Tesseract is the only
candidate that installs cleanly here and its TSV output natively supplies
the 01 section 9 contract (text + positions + confidence).

Affected files:
ai/ocr/*, ai/requirements.txt, scripts/make_sample_docs.py, dataset/*
```

## Decision 2026-09-04 — Gemini-first provider layer, no new dependency

```text
Date: 2026-09-04
Decision:
First provider is Gemini (first-listed candidate in 06/07/.env.example;
NOT a final primary-model selection — that still requires benchmarking
per 07 section 4). backend/app/ai exposes only extract_land_record();
adapters share constructor (api_key, model, timeout_seconds) and register
in AIService._REGISTRY, so OpenRouter/NVIDIA plug in without touching
callers. GeminiAdapter uses plain httpx REST (generateContent +
responseMimeType application/json, temperature 0) — no SDK install.
Model/key/timeout env-driven: AI_PROVIDER/AI_MODEL (default
gemini-2.0-flash)/AI_TIMEOUT_SECONDS/GEMINI_API_KEY, server-side only.
Failures map to classified ProviderError (transient flag reserved for the
later fallback step); no fallback logic in this step. Prompt v1 demands
JSON-only, exact 04 field names, null-when-absent, and fences the OCR text
as untrusted input (11 section 9).

Reason:
Satisfies 06 section 4 + 07 section 6 interface contract with the smallest
dependency footprint; keeps primary-model choice honestly open.

Affected files:
backend/app/ai/*, backend/tests/test_ai_service.py,
backend/scripts/smoke_gemini.py, backend/app/config.py, .env.example,
backend/README.md
```

## Decision 2026-09-04 — Strict identifiers in extraction eval

```text
Date: 2026-09-04
Decision:
ai/extract/evaluate.py treats survey/khasra/khata/mutation/registration
numbers and dates as strict: any difference is INCORRECT, never
PARTIALLY_CORRECT. Rationale: a near-miss identifier points at a different
parcel/record, and partial credit would hide exactly the errors validation
+ human review must catch (proven live: OCR "4145/2" vs GT "145/2" on the
noisy doc). Partial credit remains only for names/places/descriptions.

Reason:
Keeps the eval honest about land-record risk; aligns with 08 severity
thinking (identifier errors are blocking, not cosmetic).

Affected files:
ai/extract/evaluate.py, backend/tests/test_ai_extract_eval.py
```

## Decision 2026-09-04 — Deterministic validation, duplicates never confirm

```text
Date: 2026-09-04
Decision:
ai/validation implements 08 layers as pure functions: required-field
REVIEW_REQUIRED, area numeric/positive FAIL/ERROR, unknown unit or date
WARNING (regional variation is never a rejection), reference checks against
injected vocabularies (None reference yields NOT_CHECKED/INFO, never a
false PASS), geo-chain consistency, and survey+village duplicate matching
that returns only NO_MATCH or POSSIBLE_DUPLICATE — never auto-confirmed,
never fraud-labeled. Normalization is non-mutating (originals preserved
for audit). Verdicts: READY_FOR_APPROVAL / REVIEW_REQUIRED / BLOCKED;
approval_blocked gates automatic approval only. Renamed
ai/validation/types.py to models.py after it shadowed the stdlib `types`
module and crashed direct script runs.

Reason:
08 principle (AI proposes; rules + humans dispose) with honest uncertainty
at every layer; stdlib shadowing is a hard crash class worth one rename.

Affected files:
ai/validation/*, backend/tests/test_validation.py,
dataset/evaluation/validation_check.json
```

## Decision 2026-09-04 — Uncalibrated confidence with validation caps

```text
Date: 2026-09-04
Decision:
ai/confidence combines OCR line confidence (value located in OCR text by
documented containment heuristic), extraction self-reported confidence,
and validation outcomes as mean-of-available-components, then applies
caps: FAIL/ERROR caps at 0.39 (forces LOW), WARNING/REVIEW_REQUIRED caps
at 0.69 (at most MEDIUM). Bands HIGH>=0.80 / MEDIUM>=0.60 / LOW, with
REVIEW_REQUIRED when unscorable. Thresholds are INITIAL OPERATIONAL
values, explicitly NOT calibrated probabilities (08 section 8, 12
section 6); confidence never implies legal correctness. Missing values,
LOW bands, and any actionable issue force human review; every score
carries explanatory reasons. Renamed ai/confidence/types.py to models.py
(same stdlib shadowing crash as STEP 08). Live proof on step08_bad: LLM
reported 0.95 almost everywhere yet area was forced LOW and 7/14 fields
flagged — validation overrules self-confidence by design.

Reason:
06 Layer 7 inputs with honest uncertainty routing; caps prevent confident
errors from flowing to approval; reasons give reviewers the full picture.

Affected files:
ai/confidence/*, backend/tests/test_confidence.py,
dataset/evaluation/confidence_report.json
```

## Decision 2026-09-04 — Review workflow is API-first, audit everything

```text
Date: 2026-09-04
Decision:
backend/app/reviews implements the 03/10 workflow without any frontend:
review tasks (PENDING/IN_REVIEW/COMPLETED/CANCELLED), field corrections
with mandatory reasons, fresh deterministic revalidation persisted per
correction, approval blocked (409 + enumerated reasons) while FAIL/ERROR/
CRITICAL issues, unresolved required fields, or open reviews remain, and
rejection requiring a reason while cancelling open reviews. Every action
appends to audit_logs with old/new values; terminal records are immutable;
source tables are never touched by review code. Stores follow the existing
Protocol + Supabase-impl + dependency-override pattern, so all of this is
tested against in-memory fakes.

Reason:
API-first keeps the permanent (teammate) frontend unblocked while proving
the full verify-correct-approve-audit loop required by 02 acceptance
criteria.

Affected files:
backend/app/reviews/*, backend/app/main.py, backend/tests/test_reviews.py,
backend/tests/conftest.py (added verifier user), backend/README.md
```

## Decision 2026-09-04 — Full pipeline runs in BackgroundTasks

```text
Date: 2026-09-04
Decision:
POST /documents/{id}/process returns 202 immediately and runs
download→OCR→extract→validate→persist→auto-review as a BackgroundTask with
stage-classified job error codes; document/land_record statuses follow the
03 state model (READY verdict→READY_FOR_APPROVAL, BLOCKED→VALIDATION_FAILED
document + REVIEW_REQUIRED record, else REVIEW_REQUIRED); a PENDING/HIGH
review task is auto-created for non-READY verdicts. Records search uses
ilike filters + validated pagination; mock-lrms accepts APPROVED records
only with an explicit not-a-live-integration disclaimer.

Reason:
Keeps 15-40s AI work off the request path while making every pipeline
state pollable; completes the 10_API_SPECIFICATION surface (26 routes, 0 dups).

Affected files:
backend/app/processing/*, backend/app/records/*,
backend/app/documents/{router,schemas,storage_backend},
backend/app/reviews/stores.py, backend/app/main.py,
backend/requirements.txt, backend/tests/test_processing.py,
backend/tests/test_records.py, backend/README.md, ai/ocr/pdf_render.py
```

## Decision 2026-09-04 — Disposable QA frontend, contracts rule

```text
Date: 2026-09-04
Decision:
frontend/ is a minimal Vite+React QA app (login, upload/process/status,
extraction+confidence, validation, review queue, record detail with
correction/approve/reject/audit, records search) built ONLY against the
exact 10_API_SPECIFICATION contracts. No branding, no router library
(hash nav), token in sessionStorage, API URL editable in-app. It is
explicitly disposable: the permanent Google Stitch build replaces it.
Verified serving (vite build + dev 200) and drove one full live
upload→process→correct→approve flow through the same calls (1 Gemini
extraction); all temp rows cleaned, baseline restored.

Reason:
Unblocks manual backend verification without over-investing in throwaway
UI; contract-first wiring doubles as executable API documentation.

Affected files:
frontend/* (new QA app; permanent UI will replace it)
```

## Decision 2026-09-04 — Reliability: retry-once, fallback chain, cache

```text
Date: 2026-09-04
Decision:
AIService walks an ordered route chain (primary + AI_FALLBACKS
"provider:model" lanes): one attempt per route plus ONE retry on transient
failures only (rate limit, timeout, unavailable); terminal failures raise
immediately with no retry or failover. Second provider is OpenRouter via
its OpenAI-compatible API, using its NATIVE "models" fallback list for
model-level failover; provider-level Gemini->OpenRouter lives in
AIService. Repeat extractions hit a bounded TTL cache keyed by document
checksum (or OCR-text hash) + pipeline + full route chain + prompt/schema
versions. Every result records attempted_routes; no SDK added (httpx
REST); keys server-side only, never in messages/URLs/logs.
Field-mapping code shared between adapters (fields.py).

Reason:
06 section 5 + 07 sections 8-9 reliability with minimum quota burn and
honest observability; native OpenRouter fallback instead of a redundant
custom model loop.

Affected files:
backend/app/ai/{fields,openrouter,cache}.py (new), service.py, types.py,
base.py, gemini.py, config.py, tests/test_ai_resilience.py (17 checks),
.env.example, backend/README.md
```

## Decision 2026-09-05 — Repeatable evaluation, reuse-if-fresh, honest gaps

```text
Date: 2026-09-05
Decision:
scripts/evaluate_all.py runs pytest + all four stage CLIs and aggregates
dataset/evaluation/REPORT.md plus timestamped report_*.json (history
accumulates, REPORT.md is the rolling latest). Free stages always rerun;
extraction reruns ONLY on missing/failed/stale outputs, with the live-call
count printed upfront (--dry-run shows the plan); --force-*/--skip-pytest
override. The report carries dataset/model/prompt/schema versions, field
accuracy, failures, latency, review rate, validation results — plus an
explicit-gaps section instead of invented numbers. step08_bad record GT
was transcribed from its clean OCR reading with a SOURCE_NOTE caveat
(source-PDF check still owed before final metrics). New pytest: OCR metric
units, manifest contract, consolidated security boundaries (auth matrix,
secret hygiene, prompt-injection fencing), opt-in live Supabase CRUD
(LIVE_DB_TESTS=1, default skip).

Reason:
12 section 11 traceability with zero surprise quota spend; gaps written
down beat gaps hidden.

Affected files:
scripts/evaluate_all.py, backend/tests/{test_ocr_units,test_security,
test_supabase_live}.py, dataset/ground_truth/step08_bad*.json (+note),
dataset/evaluation/{REPORT.md,report_*.json}
```

## Decision 2026-09-05 — Security audit: one boundary fixed, rest verified

```text
Date: 2026-09-05
Decision:
Full 15-point audit (11_SECURITY_DESIGN): no hardcoded secrets anywhere
(all secret-pattern hits are vendored CSS/license noise), no secret
logging, no raw-SQL string building (PostgREST parameterized throughout),
prompt-injection fencing intact, generic 500s without tracebacks,
validation errors exclude submitted values, audit append-only with no
mutating endpoints, private bucket with no signed/public URLs, HS256
pinned with required exp, bcrypt+SHA256 prehash, RLS deny-by-default
unchanged on all 12 tables. ONE confirmed issue fixed: ilike search
wildcards (%, _, \) from user input acted as LIKE patterns — now escaped
(Postgres backslash default) with regression tests proving the escaped
pattern reaches the query. Accepted pre-deployment gaps (not built):
API rate limiting, explicit CORS method/header lists + HTTPS enforcement,
httpOnly-cookie auth for the permanent frontend, pip-audit availability,
single-service_role least-privilege split.

Reason:
Fix confirmed boundaries only; speculative rewrites and functionality
removal both rejected per task rules.

Affected files:
backend/app/records/stores.py (_escape_like), backend/tests/test_records.py
```

## Decision 2026-09-05 — Deploy prep without redesign

```text
Date: 2026-09-05
Decision:
STEP 16 verified all 14 deployment requirements and closed only real gaps:
fixed /health/ai lying "not_configured" (now reports live provider/model/
lanes/cache, keys never included); added Procfile + runtime.txt (3.14.2)
for hosted Python; added VITE_API_URL build-time default to the QA client
(still in-app overridable); documented AUTH_TOKEN_EXPIRE_MINUTES +
ENVIRONMENT in .env.example. Verified: env parity, 3/3 migrations, boot+
health, AI chain (2 lanes), Tesseract live, demo docs, fallback evidence.
Demo Mode confirmed NOT implemented (flag only) and marked as such in the
runbook — no fake demo built. Runbook updated only where it differed (§2
actual tree, §4 real env list, §5 exact commands, §14 demo-mode status).

Reason:
Deployment readiness = verified truth + minimal standard hosting files;
no feature work, no quota burn (0 live AI calls this step).

Affected files:
backend/app/routers/health.py, backend/tests/test_health.py,
backend/{Procfile,runtime.txt}, frontend/src/api.js, .env.example,
13_DEPLOYMENT_RUNBOOK.md (§2/§4/§5/§14)
```

## Decision 2026-09-05 — Clean-environment gate passed unchanged

```text
Date: 2026-09-05
Decision:
Strict clean-env verification used ONLY documented runbook commands:
fresh temp backend venv (requirements install + full pytest 140/140),
fresh temp ai venv (install + adapter instantiate), clean npm ci + build
(0 vulns), live boot with health/database/AI/frontend checks, real CORS
preflight (Access-Control-Allow-Origin echoed for localhost:5173),
VITE_API_URL default proven baked into dist bundle, 3/3 migrations +
private bucket confirmed, AI chain + keys + cache verified by booleans,
OCR live, evaluation dry-run at 0 calls. Zero fixes required — temp venvs
removed afterward, project tree untouched.

Reason:
Reproducibility must be demonstrated, not assumed; a gate that changes
code to pass proves nothing.

Affected files:
(none — verification only)
```

## Decision 2026-09-05 — Final MVP audit: 3 fixes, pipeline now complete

```text
Date: 2026-09-05
Decision:
Final audit traced the full chain and fixed three MVP-required gaps:
(1) ocr_results used blind INSERT against UNIQUE(document_id, page) so
any retry/reprocess crashed into PERSIST_FAILED — now replace_ocr_results
(delete-then-insert, same pattern as other replace_* methods);
(2) the live pipeline never ran the 08 duplicate layer — now checks new
values against other documents' records and appends DUP_CANDIDATE_001
before the verdict; (3) provider/model/prompt/schema versions are now
recorded in the PROCESSING_COMPLETED audit metadata (no schema change).
Also: stale RUNNING/PENDING jobs reconcile to FAILED/SERVER_RESTARTED at
boot; AGENTS header and runbook user-seeding SQL corrected/documented.
Deferred (documented limitations, not MVP-blocking): rate limiting, CORS
tightening, httpOnly auth, handwriting, train/test split, Demo Mode
behavior, confidence persistence, admin user CRUD, multi-page caps.

Reason:
Fix only what a functioning MVP needs; everything else stays an explicit,
written-down limitation rather than silent scope.

Affected files:
backend/app/reviews/stores.py, backend/app/processing/{pipeline,stores}.py,
backend/app/main.py, backend/tests/test_processing.py, AGENTS.md,
13_DEPLOYMENT_RUNBOOK.md (user seeding)
```

## Decision

```text
Date:
Decision:
Reason:
Affected files:
```

Example:

```text
Decision:
Use OCR and LLM as separate pipeline stages.

Reason:
Improves traceability, debugging, evaluation, and provider replacement.

Affected:
06_AI_ARCHITECTURE.md
07_AI_MODEL_STRATEGY.md
```

---

# 7. Current Technology

```text
Frontend:
Temporary QA app (Vite+React, hash nav, session token) in frontend/;
serves on :5173, build green; disposable — Stitch build replaces it.

Backend:
FastAPI 0.117 (Python 3.14 venv) in backend/app, version 0.1.0.
Config env-only; Supabase service_role client on app.state; local JWT
auth (bcrypt + PyJWT); documents upload/storage API; reviews/approvals/
audit API (verifier+); 144 pytest green (+1 opt-in live, skipped by
default); runs locally on :8000.

Database:
Supabase Postgres, project ivmkvwudblcqhtoiqlaf
(https://ivmkvwudblcqhtoiqlaf.supabase.co), 12 MVP tables live,
migrations: land_records_foundation, land_records_foundation_fixes,
storage_documents_bucket; private bucket land-record-documents (empty)

OCR:
Tesseract 5.4.0 (eng) via ai/ocr adapter; dataset_v1 CER ~0.001/WER ~0.007
on synthetic prints; NOT yet proven on handwriting/real scans.

Primary LLM:
Gemini via extract_land_record(), live-verified as gemini-3.6-flash on
dataset_v1 (mean field accuracy 0.9762); still NOT a final primary-model
selection (needs multi-model benchmark per 07 section 4).

Fallback LLMs/providers:
OpenRouter adapter implemented (native models fallback); chain configured
via AI_FALLBACKS; fallback ordering proven by mocked simulations only —
live multi-provider benchmark still open.

Hosting:
[UPDATE — DB hosted on Supabase; app not deployed]
```

---

# 8. Current AI Configuration

```text
Provider: gemini primary + AI_FALLBACKS chain (ordering mocked-proven; live TBD)
Model: gemini-3.6-flash (user-configured AI_MODEL; code default still retired)
Prompt version: v1
Schema version: v1 (04_DATA_DICTIONARY field names)
Cache: bounded TTL, identity = checksum/text + pipeline + route chain + prompt/schema
```

Do not store API keys here.

---

# 9. Known Problems

```text
Problem: Live upload/login against hosted Supabase not yet exercised.
Impact: Supabase storage backend + user store paths verified only via fakes.
Likely cause: No SUPABASE_SERVICE_ROLE_KEY available to this environment.
Current workaround: Protocol-based fakes in tests; graceful 503s live.
Next action: Configure backend .env with service_role key, seed a test user,
upload a real PDF, confirm row + object, then delete test artifacts.
```

```text
Problem: OCR proven only on 3 synthetic printed docs; no handwriting or
real legacy-scan evidence yet.
Impact: Cannot claim production OCR accuracy; MVP scope stays printed-first.
Likely cause: dataset_v1 is generator-made (exact GT by construction).
Current workaround: Proceed to extraction POC on synthetic prints; keep
human review mandatory for low-confidence fields per design.
Next action: Collect real samples toward 30–50 docs, re-benchmark, and try
EasyOCR on the handwritten subset.
```

---

# 10. Important Constraints

```text
- Do not expose API keys.
- Do not silently expand MVP scope.
- Do not treat AI output as legal authority.
- Do not change database/API contracts without updating documentation.
- Do not claim untested accuracy.
```

---

# 11. Files Recently Changed

```text
[2026-09-03] supabase/migrations/20260903170000_land_records_foundation.sql
[created] reproducible copy of applied foundation migration (12 tables + RLS + seeds)

[2026-09-03] supabase/migrations/20260903170500_land_records_foundation_fixes.sql
[created] reproducible copy of applied fixes migration (search_path + 3 indexes)

[2026-09-03] supabase/database.types.ts
[created] generated TS types for all 12 tables

[2026-09-03] .env.example
[created] placeholders only (Supabase URL + keys, auth, storage, AI providers, DEMO_MODE)

[2026-09-03] .gitignore
[created] blocks .env / venv / node_modules / local uploads from Git

[2026-09-03] backend/app/* (main, config, database, errors, middleware,
logging_config, auth/*, routers/health)
[created] STEP 03 backend foundation (config/env, DB client, error
envelope, request IDs, dev CORS, health endpoints, JWT auth + RBAC)

[2026-09-03] backend/tests/* + pytest.ini + requirements.txt + README.md
[created] 18-test suite (health, envelope, password/JWT units, auth API
against in-memory store), run config, dependency pins, setup docs

[2026-09-03] .env.example / AGENTS.md
[updated] added FRONTEND_ORIGINS + LOG_LEVEL; real backend dev commands

[2026-09-03] migration storage_documents_bucket (applied) + bucket verified
[created] private bucket land-record-documents, 10 MB + PDF/PNG/JPEG/TIFF guards

[2026-09-03] backend/app/documents/* (schemas, validation, store,
storage_backend, service, router) + main/config/requirements/README updates
[created] STEP 04 upload/storage API; +python-multipart dep; STORAGE_BUCKET
+ MAX_UPLOAD_MB settings; endpoint table in README

[2026-09-03] backend/tests/test_documents.py + conftest/test_auth_api tweaks
[created] 13 upload/storage checks (valid PDF+PNG, 4 rejection types,
oversized, auth, 404/422, storage-fail, db-fail-cleanup, validation units);
in-memory users now use UUID ids mirroring production rows

[2026-09-04] ai/ocr/* (base, tesseract_adapter, pdf_render, run_ocr,
benchmark) + ai/requirements.txt + ai/.venv
[created] STEP 05 OCR POC: engine-neutral interface, Tesseract 5 adapter,
PDF rendering, CLI runner, CER/WER benchmark; isolated ai venv
(rapid_adapter.py removed — RapidOCR uninstallable on Python 3.14)

[2026-09-04] scripts/make_sample_docs.py + dataset/* (manifest, 3 raw docs,
3 ground truths, 3 ocr_outputs, evaluation/ocr_benchmark.json, README)
[created] dataset_v1 synthetic English khata-style set, deterministic

[2026-09-04] backend/app/ai/* (types, errors, base, prompt, gemini,
service) + tests/test_ai_service.py + scripts/smoke_gemini.py
[created] STEP 06 provider layer: extract_land_record() interface,
Gemini-first adapter (httpx REST, no SDK), classified errors, prompt v1;
17 mocked checks green; live smoke exits 2 (no key configured)

[2026-09-04] backend/app/config.py + .env.example + backend/README.md
[updated] AI_PROVIDER/AI_MODEL/AI_TIMEOUT_SECONDS/GEMINI_API_KEY settings;
AI layer docs + smoke command

[2026-09-04] ai/extract/* (run_extraction, evaluate) + 3 *_record.json GT
+ dataset/model_outputs/* + dataset/evaluation/extraction_eval.json
[created] STEP 07 connector + field-level evaluator (strict identifiers);
live: 41 CORRECT / 1 INCORRECT, mean accuracy 0.9762, 0 failures

[2026-09-04] backend/tests/test_ai_extract_eval.py
[created] 16 offline checks (connector mapping, failure records, 10
classify cases, record counts/accuracy); strict-identifier fix verified

[2026-09-04] ai/validation/* (models, normalize, rules, duplicates,
check_model_outputs) + backend/tests/test_validation.py
[created] STEP 08 deterministic rules (required/format/unit/date/ref-chain/
duplicates) + non-mutating normalization + verdicts; 12 checks green;
live model_outputs: 1 READY, 2 REVIEW (correct duplicate flags), 0 BLOCKED

[2026-09-04] ai/confidence/* (models, engine, score_outputs) +
backend/tests/test_confidence.py
[created] STEP 09 confidence engine (OCR+extraction mean, validation caps,
HIGH/MEDIUM/LOW/REVIEW_REQUIRED, review routing, reasons); 11 checks
green; confidence_report.json over 4 docs; healed transient doc03 5xx
with one targeted retry

[2026-09-04] backend/app/reviews/* (schemas, stores, service, router) +
backend/tests/test_reviews.py
[created] STEP 10 review workflow: tasks, corrections with mandatory
reasons + revalidation, approve/reject gating, full audit trail; 9 checks
green (incl. real audit-ordering bug found and fixed in service)

[2026-09-04] backend/app/processing/* + backend/app/records/* +
documents extraction/validation endpoints
[created] STEP 11 full pipeline (BackgroundTasks job + stage-classified
failures + auto-review) and missing APIs (records search/detail/export,
3 dashboards, mock-lrms); 12 checks green; +pymupdf/pillow/numpy/
pytesseract backend deps; 26 API routes, zero duplicates

[2026-09-04] STEP 11 independent verification (+1 genuine defect fixed)
[verified] 31 routes enumerated, no dup method/path, all API under /api/v1,
auth matrix confirmed from source; 111/111 pytest; live HTTP against real
Supabase with temp data only: upload 201, process 202 + 409 guard +
background STORAGE_DOWNLOAD_FAILED classification, search/pagination
(incl. out-of-range empty page), detail/extraction/validation/export,
dashboards, full 78→73 review→approve→audit chain, mock-lrms accept/refuse,
401/403/404/422/409 paths; baseline restored exactly.
[fixed] GET /records with page beyond last result returned 500
(PostgREST PGRST103 on over-offset range); now returns empty items with
honest total + regression tests

[2026-09-04] frontend/* (api client, 6 views, minimal styles)
[created] STEP 12 disposable QA app (login/upload/process/extract+confidence/
validation/reviews/record detail with correction+decision/audit/search);
vite build green, dev serves 200; one full live flow verified (upload 201,
process 202, extraction 14 fields, validation, 4145/2→145/2 correction,
approve, 4-event audit chain); baseline restored

[2026-09-04] backend/app/ai/{fields,openrouter,cache}.py + service/types/
base/gemini/config updates + tests/test_ai_resilience.py
[created] STEP 13 reliability: OpenRouter adapter (native models fallback),
retry-once-transient-only chain in AIService, bounded TTL result cache
(source+pipeline+chain+prompt/schema identity), attempted_routes
observability; 17 simulation checks green, 0 live calls; no new dependency

[2026-09-05] scripts/evaluate_all.py + backend/tests/{test_ocr_units,
test_security,test_supabase_live}.py + step08_bad record GT (+note)
[created] STEP 14 evaluation layer: repeatable command (pytest + 4 stage
CLIs, reuse-if-fresh, dry-run quota preview) aggregating REPORT.md +
timestamped report_*.json; 9 new checks green (live DB test opt-in,
proven once); full run: 137 pass + 1 skip, 0 live Gemini calls

[2026-09-05] backend/app/records/stores.py + backend/tests/test_records.py
[audit-fix] STEP 15: ilike wildcard escaping (_escape_like) + 2 regression
checks; full security audit clean otherwise (no secrets/logging/SQL/
prompt-injection/CORS-dev/error/audit/storage/auth issues confirmed);
139 pass + 1 skip

[2026-09-05] backend/{Procfile,runtime.txt} + frontend VITE_API_URL +
backend health-ai fix + 13_DEPLOYMENT_RUNBOOK.md (§2/§4/§5/§14)
[created] STEP 16 deploy prep: truthful /health/ai, standard hosting
files, exact setup commands, demo-mode gap marked NOT IMPLEMENTED;
verified env parity, 3/3 migrations, boot+health, AI chain (2 lanes),
OCR live, demo docs, fallback evidence; 140 pass + 1 skip, 0 AI calls

[2026-09-05] STEP 16 final gate: clean-environment verification
[verified] fresh temp venvs (backend install + 140/140 pytest; ai install
+ adapter boot), clean npm ci + build (0 vulns), live boot with health×3,
real CORS preflight, VITE_API_URL baked default, 3/3 migrations, private
bucket, AI chain/keys/cache, OCR live, eval dry-run at 0 calls; zero fixes
needed, temp envs removed

[2026-09-05] frontend/src/api/{types.ts,client.ts} + views rewired + tsconfig
[audit] frontend↔backend contract audit: all 20 points checked, zero
business-logic mismatches; single fix — ApiError now preserves backend
request_id (was dropped); +typescript devDep, tsc --noEmit clean, vite
build green, backend suite 144 green (untouched)

[2026-09-05] frontend Phase 1A session reliability (client.ts, App.jsx,
Login.jsx, session.test.ts, package.json)
[created] centralized 401 session-death handling (clears session, redirects
to login; never on login-form 401, never on 403, never without a token);
startup session validation with init gate (no protected calls before it);
best-effort server logout + stale-session drop on login; role display from
validated /me only. 8/8 vitest green; tsc clean; vite build green; backend
auth suites 14/14 green (untouched). Tests caught 1 real bug pre-merge:
over-broad /api/v1/auth/ exclusion skipped auto-logout for /me.

[2026-09-05] frontend Phase 1B state sync (client.ts signal support,
RecordDetail/Records/Reviews cancellation + guards, loading/empty states)
[fixed] stale-response races on navigation/remount; unmounted setState paths;
no request cancellation. 4 new request tests; 12/12 vitest, tsc clean,
vite build green, backend 144 green (untouched). Left as-is (benign):
dev-only StrictMode double-GETs, Upload doc state local-only.

[2026-09-05] frontend Phases 1C–1E (Upload workflow reliability, review
integration, final hardening) + live E2E proofs (DOCUMENT WORKFLOW PASS,
REVIEW→APPROVAL PASS): status polling + doc persistence + submit guards in
Upload; review verdict/approval_blocked/document panel + mutation guards in
RecordDetail; upload-orphan cleanup fix on AppError path; full negative-test
matrix (401/403/422/404/409) green; secrets/storage/perf audits clean.
Backend 146 green, frontend vitest 35/35, tsc/build green. Known: AUTH_SECRET
<32 bytes (rotate before shared deploy); correction writes non-atomic.

[2026-09-05] frontend Stitch foundation (tokens + primitives, no screens yet)[created] frontend/src/styles/tokens.css (navy scale, semantic tiers, Inter
type scale, spacing, radius, shadows from Stitch project 5026128240319690003
designMd) + primitives.css + components Button/TextInput/Alert/StatusBadge;
Inter + JetBrains Mono wired in index.html; title set. Stitch MCP has no
agent-exposed tools — retrieval via direct MCP-over-HTTP probe scripts (kept
in temp dir, not in repo). Found: App.jsx dead Upload branch (renders null).
vitest 35/35, tsc clean, oxlint 3 pre-existing warnings, build green.
```

[2026-09-05] frontend Stitch LOGIN screen (1a3bd1dbc5a14deda00bd6d93824e86a)
[created] views/Login.jsx rewrite (split navy brand panel + white auth panel,
TextInput/Button/Alert, password visibility, inline validation, busy/disabled
states) + styles/login.css; TextInput trailing adornment slot + Button
className passthrough; App.jsx renders login full-bleed (no topbar/apirow).
Omitted (no backend support, would be fake): forgot-password, remember-me,
prefilled demo credentials, state-inspection panel. Honest copy swaps only
(no fake seals/claims). Contract unchanged: POST /api/v1/auth/login
{email,password} -> {access_token}, landing #/records. vitest 36/36 (1 new
login-shape test), tsc clean, lint 0 errors, build green, preview 200.
```

[2026-09-05] frontend Stitch SHELL + DASHBOARD (577666b56d964c3f81e8e4b089e99447)
[created] components AppShell (nav sections, user card, health pill from
public /health/ai, mobile drawer), PageHeader, StatCard, DataTable,
Skeleton, EmptyState, ErrorState; styles/shell.css + table/stat/state CSS in
primitives.css; views/Dashboard.jsx (live summary/validation/latest-records,
single parallel load, skeleton/error+retry/empty states) + Placeholder.jsx
for Analytics/Audit/Settings/Help; App.jsx routes (#/ dashboard landing,
#/records, #/upload, #/reviews, #/record/:id), API override moved to
Settings; client opts on dashboard fns + getHealthAi; statusTone() in
types.ts. Omitted (no backend source): header search, notifications bell,
activity feed (empty state), quorum/GIS cards, review-count badge. vitest
52/52 (16 new), tsc clean, lint 0 errors (2 pre-existing warnings in old
views), build green, preview 200. Backend/database untouched.
```

[2026-09-05] frontend Stitch DOCUMENTS screen (route #/records, no separate
Stitch screen — design-system language only)
[rewrote] views/Records.jsx as Documents (PageHeader, filterbar with holder/
survey/status-select submit search, DataTable with StatusBadge, shared
Pagination, skeleton/error+retry/empty/filtered-empty states, abort-guarded,
submit-driven single requests); new shared Select, Pagination,
ConfidenceBadge (+ confidenceTone in types.ts), format.js timeAgo (shared
with Dashboard). Omitted (no search-API support): document-type/date/
confidence filters, document-ID lookup, Confidence column. vitest 62/62
(10 new), tsc clean, lint 0 errors, build green, preview 200.
Backend/database untouched.

[2026-09-05] frontend Stitch UPLOAD screen (babc23151d0e41268b20a9ccd4801eb6)
[rewrote] views/Upload.jsx (PageHeader, drop zone + file picker, staged file
chip with remove, doc-type/language metadata, Upload & Process / Cancel,
indeterminate progress, backend tracker with auto-polling + persisted
results); new styles/upload.css; client uploadDocument(meta, opts-signal)
for Cancel-abort; uploadFileCheck() mirror in types.ts. Preserved: guards,
polling caps, doc persistence, mount restore, terminal auto-results.
Omitted (no API/device source): % progress, client SHA-256, SRO reference
field, demo telemetry panels; post-upload stays in-route tracker until the
Document Processing screen lands. vitest 69/69 (7 new), tsc clean, lint 0
errors (1 pre-existing warning), build green, preview 200.
Backend/database untouched.

[2026-09-05] frontend Stitch PROCESSING screen (3ddcbec77d5047a9ba5f00a55c4622dd)
[new] route #/document/:id + views/DocumentProcessing.jsx (doc name/ID/live
StatusBadge, 8-stage ProcessingStepper from aggregate processingSteps()
mapping, current-step/success/failure panels, manual start/retry with guard,
single 3s poller with cap + unmount cleanup, record link via extraction);
shared ProcessingStepper.jsx + styles/processing.css; Upload tracker links
to the processing view. Omitted (no backend source): per-stage timings,
event stream, detection grid, worker/throughput telemetry, simulator panel.
Build caught 1 real bug (isProcessingTerminal imported from types instead
of client) — fixed. vitest 80/80 (11 new), tsc clean, lint 0 errors
(1 pre-existing warning), build green, preview 200.
Backend/database untouched.

[2026-09-05] frontend Stitch EXTRACTION screen (a21c29e7887c424aa7e071f99bcf250d)
[new] route #/document/:id/extract + views/DocumentExtraction.jsx (two-pane:
DocumentViewer metadata pane + grouped extracted fields with ConfidenceBadge,
validation display, conditional View evidence); shared DocumentViewer,
EvidenceHighlight, api/fields.ts (14-field schema), styles/extraction.css;
processing success now links to the extraction route; Export JSON via
exportRecord blob download; actions route to #/record/:id (review+audit).
Omitted (no backend source): scan rendering/zoom/pages (no file-download
endpoint — stated in-UI), per-field evidence when absent, transcript/print
actions. vitest 83/83 (3 new), tsc clean, lint 0 errors (1 pre-existing
warning), build green, preview 200. Backend/database untouched.
```

[2026-09-05] frontend Stitch REVIEW QUEUE screen (99a50253d4734e729113089568af4555)
[rewrote] views/Reviews.jsx (summary StatCards from loaded tasks, filterbar:
issue text + status/priority/reviewer/sort, DataTable with priority/status
badges, empty "Your review queue is clear." + filtered-empty, error+retry,
abort-guarded, explicit refresh, no polling); shared queue.js helpers
(filter/sort/priority-rank/average-age). Review action routes to
#/record/:id (established review workspace). Omitted (no task-API source):
per-task confidence + adjudication columns, confidence/issue-type filters,
confidence sort, assignee names (You/short-ID/Unassigned), bulk/escalate/
export actions. vitest 93/93 (10 new), tsc clean, lint 0 warnings, build
green, preview 200. Backend/database untouched.
```

[2026-09-05] frontend Stitch REVIEW WORKSPACE screen (a002d440c57d4058a5115efa1753baaf)
[rewrote] views/RecordDetail.jsx as two-pane workspace (top id/status/verdict
+ Approve/Reject actions, DocumentViewer left, grouped ReviewField rows with
confidence/validation/evidence/edit right, backend validation panel,
complete-review, audit table); shared Modal (Escape/scrim/backdrop, honest
approve copy, required reject reason) + ReviewField (per-field drafts that
survive reloads, Save/Cancel, keyboard-native) + review.css; PageHeader
actions slot; correctionValue() in fields.ts. Preserved: abort loads,
guards, ensureReview, reload-after-mutation, verdict/approval-blocked panel,
audit actor. No backend versioning exists (blind updates — last-write-wins
documented); approved-record route does not exist yet so approval stays +
reloads (deviation). vitest 94/94 (1 new), tsc clean, lint 0 warnings,
build green, preview 200. Backend/database untouched.
```

[2026-09-05] frontend Stitch APPROVED RECORD screen (4feece87c7ef4c7b84eb19ee04e6be1d)
[new] route #/record/:id/approved + views/ApprovedRecord.jsx (approval strip
from backend facts, shared RecordFields, validation summary, source/audit/
export actions with export states); shared RecordFields.jsx adopted by
DocumentExtraction (single renderer); downloadJson() in format.js;
isTerminalRecord() in fields.ts (adopted by RecordDetail); approval now
navigates to the approved route + terminal link back. Omitted: LRMS push
(mock-only endpoint, would imply real integration), sealed-PDF transcript
(no endpoint), aggregate accuracy + legal-ownership claims. Non-approved
records get an honest state. vitest 95/95 (1 new), tsc clean, lint 0
warnings, build green, preview 200. Backend/database untouched.
```

[2026-09-05] frontend Stitch AUDIT TRAIL screen (b1d6d3e888ab4a5e8dda0803d27900b4)
[new] route #/record/:id/audit + views/RecordAudit.jsx (summary StatCards
from record+document, source filter, newest/oldest sort, Print, read-only);
shared AuditTimeline.jsx + audit.css rail; describeAuditEvent() in
components/audit.js (8 real action titles, officer/pipeline sourcing,
original→updated pairs only when both sides exist); #/audit entry explains
record-scoped design; all View-audit links upgraded to the audit route.
Omitted (no backend source): workspace-wide feed, DSC/IP/ledger fiction,
log export (no endpoint), event stats beyond real counts. vitest 100/100
(5 new), tsc clean, lint 0 warnings, build green, preview 200.
Backend/database untouched.
```

[2026-09-05] frontend Stitch ANALYTICS screen (b1e028ddf5984de28b664b6c220fe59b)
[new] route #/analytics + views/Analytics.jsx (4 live summary metrics +
zero-dependency CSS distribution bars over by-status maps, skeleton/
error+retry/empty states, scope note); metrics in components/analytics.js
(pass rate excl. NOT_CHECKED, latency over completed recent jobs, review
share; nulls render as empty states). Omitted (no API source): accuracy
benchmarks, confidence distribution, per-stage latency, time series,
date/type filters. vitest 105/105 (5 new), tsc clean, lint 0 warnings,
build green, preview 200. Backend/database untouched.
```

[2026-09-05] frontend Stitch SETTINGS screen (455495cdb4b14de1b0e32ed8fde2c2b0)
[new] route #/settings + views/Settings.jsx (read-only Profile from GET /me
with refresh, Security session info + real sign-out, Workspace API-URL with
honest local Saved state); API-URL state moved out of App.jsx (alert()
removed with it). Omitted (no endpoints): profile/password edits,
preferences, notifications, danger zone. vitest 108/108 (3 new), tsc clean,
lint 0 warnings, build green, preview 200. Backend/database untouched.
```

[2026-09-05] frontend Stitch HELP screen (19e6210d57934113b7a374f70791e76b)
[new] route #/help + views/Help.jsx (trust panel + section nav, all 10
required sections with real behavior/terminology, native details/summary
FAQs, support without fictional contacts); registry in components/help.js;
styles/help.css. Omitted fiction: DSC/Rule-48(b)/NIC/dialect claims.
vitest 110/110 (2 new), tsc clean, lint 0 warnings, build green, preview
200. Backend/database untouched (screen is content-only).
```

[2026-09-06] frontend+backend SELF-REGISTRATION (register-then-login flow)
[new] POST /api/v1/auth/register (201 {id,name,id_number,email,role,status,
created_at}, fixed operator/active, bcrypt via existing hash_password, 409
USER_EXISTS with exact message, no token returned); migration
add_users_id_number (nullable TEXT, no invented uniqueness) + file
20260905130000_add_users_id_number.sql; UserOut += id_number (additive);
frontend #/sign-in SignUp view (Stitch login language, exact validation
texts, busy guard, error mapping) + client.registerAccount + AuthLanding
Sign-in enabled + Login one-shot success notice + Settings ID row.
Omitted by design: email verification (none exists), password change,
preferences, role choice. Live E2E: register 201 → DB row verified (bcrypt
hash, operator/active) → duplicate 409 → login 200 → /me → dashboard →
logout → logged-out 401; test user deleted. Backend 153 green, frontend
117/117 + tsc/lint/build green. Docs: 10_API_SPEC §2, 09_SCHEMA users.
```

[2026-09-06] registration failure diagnosis (stale-backend 404 envelope)
[found] Reported generic failure + plain button could not reproduce from
workspace source: SignUp/Login buttons are identical invocations, dist is
fresh, live register→login→dashboard re-verified on current code. Root
cause of the user-seen message: unmapped server responses (404 from a
backend predating /register, 503, or unreachable backend) collapsed into
one generic text. [fixed] mapRegistrationError() in components/auth.js
(404→update/restart hint, unreachable/5xx→service text, exact texts kept)
adopted by SignUp; 4 new tests. vitest 121/121, auth pytest 19/19, tsc/
lint/build green. Action for user: restart backend from current code +
hard-refresh the frontend.
```

[2026-09-06] registration re-diagnosis (user still saw service message)
[found] No code defect: SignUp/Login buttons are identical invocations,
dist fresh, live register→login→dashboard re-verified with Origin headers.
DB cannot selectively break registration: only trigger is
trg_users_updated_at, zero RLS policies on users (service-role path),
single-table atomic insert (no partial-creation state possible).
User-side message fires only on no-HTTP-status or 503/5xx ⇒ their browser
is not reaching a current backend (down / wrong URL / stale bundle).
Two uvicorn PIDs observed = parent+child of one fresh server, same code.
No changes made; test user removed, baseline (operator only) confirmed.
```

[2026-09-05] frontend AUTH LANDING (no Stitch register design exists)
[new] route #/auth + views/AuthLanding.jsx (Stitch login visual language;
Login card navigates to #/login for real; Sign-in card disabled with the
stated reason — no registration endpoint exists); Login gains a
"Create your workspace account" link to #/auth; unauthenticated entry
renders the landing. BLOCKER (per task §6/§17, reported not built): no
POST /auth/register endpoint and no users ID-number column — see report
for the minimal backend change. vitest 110/110, tsc clean, lint 0
warnings, build green, preview 200. Backend/database untouched.
```

[2026-09-06] PHASE 1 STEP 1 record/audit permission decoupling (frontend only)
[root cause] RecordDetail/RecordAudit coupled record+audit in one
Promise.all: the designed audit 403 (operator) rejected the whole load so
setDetail never ran ("Record unavailable"); the reviews-list 403 did the
same. [fix] new components/recordLoad.js orchestration (record primary
with 404-vs-server split; audit/tasks/extraction degrade independently;
audit/tasks 403 → permission states) + 10 tests; both views rewired;
role-aware UX (operators get read-only values + verifier-role notes,
Approve/Reject/Complete hidden, backend still enforces everything).
Backend/RBAC/schema/contracts/auth touched nowhere. vitest 131/131
(10 new), tsc clean, lint 0, build green, backend reviews 10/10 green.
```

[2026-09-06] PHASE 1 STEP 3 user-friendly results + errors (frontend only)
[new] components/errors.js central mapper (exact 401/403/404/409/422/5xx/
network texts; 403≠unavailable, 404≠permission; requestIdOf) + ErrorState
reference line; RecordSummary adopted at both Export JSON actions;
mapper+refs applied across RecordDetail/RecordAudit/Reviews/Documents/
Dashboard/Analytics/Approved/Extraction/Processing/Upload/Settings
(login/signup bespoke texts preserved + covered by their tests).
No backend/contract/RBAC changes. vitest 145/145 (12 new), tsc clean,
lint 0, build green, preview 200, backend reviews+auth 22/22 green.
```

[2026-09-06] PHASE 1 STEP 2 validation navigation + presentation (frontend only)
[root cause] "View validation" scrolled to a zero-height anchor with no
scroll offset under the 56px sticky header (endpoint + render + handler
all verified working); issues rendered as raw SEVERITY [RULE] dumps.
[fix] .validation-anchor scroll-margin-top + arrival flash (motion-safe);
shared ValidationSummary (verdict badge, severity chips, human field
labels, backend messages, generic recommended actions, rule IDs in
collapsed details) adopted in Extraction/Review/Approved/Upload views;
validationVerdict() mapping in types.ts. No backend/validation/contract
changes. vitest 133/133 (2 new), tsc clean, lint 0, build green,
preview 200.
```

[2026-09-06] PHASE 1 STEP 4 coherent result experience (frontend only)
[built] on the extraction view: ResultBanner (green/amber/red display map
over doc+validation states, tested), live review-state row (omitted for
operators who cannot list tasks), role-aware actions (Export demoted to
secondary, operator note instead of dead-end buttons), backend still the
only enforcer. No backend/contract/schema changes. vitest 147/147
(2 new), tsc clean, lint 0, build green, preview 200.
```

[2026-09-06] PHASE 1 STEP 4 polish: non-technical result UX (frontend only)
[change] Missing values render "Not found" (RecordFields, ReviewField,
Upload table); confidence tiers read High/Medium/Low; disabled action
buttons visibly disabled; extraction summary gains mutation + record date.
No backend/contract changes. vitest 147/147, tsc clean, lint 0, build
green, backend reviews+records 19/19 green.
```

[2026-09-06] PHASE 1 STEP 3 finalize: exact error texts (frontend only)
[change] errors.js aligned to mandated wordings (409/422/network) +
tests updated; mapper adoption, RecordSummary at both exports, and
reference-ID lines verified already in place across all API-backed views
(login/signup bespoke texts preserved). Review-status row stays on the
extraction summary only (task-list fetch would 403-noise operators on the
approved view for zero gain — deliberate). vitest 147/147, tsc clean,
lint 0, build green, backend reviews+auth 22/22 green. No backend changes.
```

---

# 12. Tests

```text
Last test run: 2026-09-07 (two-role migration: backend 156 pass + 1 skip,
vitest 147/147, tsc clean, oxlint 0, vite build green, live RBAC 25/25)
Result: PASS — frontend session suite 8/8 (store, requestId, 4 expiry cases,
logout incl. failure path, Bearer wiring); tsc clean; build green; backend
auth/error suites 14/14 untouched-green. One pre-merge bug caught by tests:
auto-logout exclusion covered /me — narrowed to login-only.
Prior: contract audit (tsc/build/pytest 144); STEP 17 pytest 144/145 + live e2e.
No backend test changes needed: audit found zero contract defects.
Known warnings: third-party starlette TestClient deprecation; oxlint
5 pre-existing React-hooks style warnings in views (cosmetic).
Prior: STEP 17 pytest 144/145 + live e2e; STEP 16 gate 140/141 fresh-venv;
STEP 15 139/140 + audit; STEP 14 137/138 + evaluate_all; STEP 13 128/128.
```

---

# 13. Dataset Status

```text
Dataset version: dataset_v1 (manifest.json)
Number of documents: 3 synthetic (+1 PDF rendering of doc01) — target 30–50
Ground truth status: exact by construction — OCR text + structured record
values (registration_number null-by-absence); all fictitious
Evaluation status: OCR done (CER ~0.001); EXTRACTION done live
(mean accuracy 0.9762, 0 failures, 0 hallucinations); VALIDATION done
(rules green; 4-doc check: 1 READY / 2 REVIEW / 1 BLOCKED); CONFIDENCE done
(uncalibrated operational bands; review=True on all 4 docs with reasons);
NO train/test split yet (needed before final reporting)
```

---

# 14. Deployment Status

```text
Environment: Supabase hosted (DB live), app deploy-ready, not yet hosted
Version: DB migrations land_records_foundation + land_records_foundation_fixes
+ storage_documents_bucket + add_users_id_number + two_role_architecture;
backend 0.1.0 + full API; Procfile + runtime.txt
Frontend: QA app builds/serves locally; VITE_API_URL supported; disposable
Backend: boots clean, all health endpoints truthful; Procfile web process
Database: 12 tables live, RLS deny-by-default, seeds present, bucket ready
AI providers: gemini primary + openrouter fallback lane (2 lanes live);
extraction eval green; Demo Mode NOT implemented (flag only)
Known deployment issues: hosted deploy not yet executed (needs: push code,
set production env incl. FRONTEND_ORIGINS/CORS tightening + HTTPS, seed
users/reference data, hosted smoke tests); see runbook §8 checklist
```

---

# 15. Handoff Instructions

The next AI or developer should:

```text
1. Read 00_MASTER.md.
2. Read this MEMORY.md.
3. Identify the current phase.
4. Read only the detailed documents relevant to the task.
5. Inspect the existing implementation before changing it.
6. Preserve working functionality.
7. Test changes.
8. Update this MEMORY.md before finishing.
```

---

# 16. Update Rule

When a meaningful project decision changes:

```text
update relevant detailed document
+
update 00_MASTER.md if architecture/scope changes
+
update MEMORY.md
```

Do not let MEMORY become a replacement for the detailed project documents.

---

[2026-09-07] TWO-ROLE ARCHITECTURE (backend + database + frontend guards)
[changed] ROLE_HIERARCHY -> {user:1, operator:2, admin:3} with lowercase
normalization (normalize_role) applied in get_current_user and require_role;
8 require_role("verifier") gates -> "operator" (7 in reviews/router.py, 1 in
records/router.py mock-LRMS); registration default -> DEFAULT_REGISTRATION_ROLE
= "user"; login now rejects an unsupported stored role (fail closed) instead
of minting a token for it. Migration two_role_architecture: CHECKs on
users.role + roles.name -> ('user','operator','admin'), verifier row deleted,
operator permissions absorbed the verifier action set, `user` row added.
ZERO users rows modified; audit_logs 39 / land_records 2 / documents 4 all
preserved; RLS untouched (12/12 enabled, 0 policies).
[frontend] the two canReview guards INVERTED (role !== "operator" ->
role === "operator" || role === "admin") — leaving them would have locked
operators out of review; role union + user-facing copy updated.
[tests] +3 backend (user denied across the whole privileged surface; operator
retains former verifier capabilities; retired-verifier fails closed); a new
case-normalization test caught a real gap mid-implementation (require_role
compared normalized but returned the raw claim) — fixed.
Backend 156 pass + 1 skip, vitest 147/147, tsc/lint/build green,
live RBAC matrix 25/25 against the real Supabase project.
[known] role/status still read from the JWT and not re-checked per request:
demotion/deactivation takes effect at token expiry (<=480 min). Rotate
AUTH_SECRET to force immediate re-login. No operator/user accounts seeded yet
— both live accounts are operator, so the read-only role is unexercised by a
real login (verified with signed tokens instead).

[2026-09-07] STEP 3 secure registration + controlled provisioning
[verified] public signup already correct after Step 2: role and status are both
server-hardcoded (user/active), never read from the body. Hardened the proof
rather than the code — +6 backend tests: client-supplied status ignored;
unknown/privileged body keys (role, status, id, password_hash, auth_id) ignored;
email uniqueness case-insensitive; bcrypt hash verifies and never round-trips;
signup->login->/me(role=user)->403 across the privileged surface; login is
case-insensitive on email.
[new] scripts/provision_account.py — the ONLY supported path for operator
creation. getpass prompt (no password in argv/history/logs), roles limited to
user|operator (admin and verifier refused by argparse), refuses an existing
email (exit 3, before any prompt), prints no secret. Documented in
13_DEPLOYMENT_RUNBOOK as the preferred path, manual SQL kept as fallback.
[live] disposable signup round-trip against the real Supabase project: 36/36 —
register 201 role=user/status=active, DB row bcrypt + auth_id NULL, duplicate
409 (incl. upper-case email), role=operator in body forced to user, login/me,
4 read endpoints 200, 6 privileged endpoints 403, logout 200. Both disposable
rows deleted; users table back to 2, audit_logs still 39.
[not done, by instruction] NO operator or user MVP account was created: no
credentials were supplied in the task context, so none were invented. The exact
provisioning commands are in the runbook and in the Step 3 report.
[frontend] no change needed — Step 2 already removed every verifier assumption;
signup sends no role field, so the client cannot request one.
Backend 162 pass + 1 skip, vitest 147/147, tsc/lint/build green.

[2026-09-07] STEP 4 typed-value persistence + DB error classification (P0 FIXED)
[root cause] normalize_* deliberately preserve unparseable values verbatim
(04 s6 / 08 s4) and validation flags them (FMT_DATE_001), but _persist handed
them straight to land_records.record_date DATE / area NUMERIC. Postgres
rejected "99/99/2024" with SQLSTATE 22008; every store wrapped ALL exceptions
as AppError(503, DATABASE_UNAVAILABLE) with no logging, so a permanent data
fault was reported as a transient outage and the pipeline discarded the whole
document as PERSIST_FAILED — destroying exactly the records the project exists
to route to human review.
[fix 1] new backend/app/records/typed_values.py: coerce_typed_columns() at the
persistence boundary. A typed column receives only what Postgres can represent;
otherwise NULL, while the raw string stays verbatim in extracted_fields.value
and the validation issue stays attached. Valid values pass through byte-for-
byte (guarded by tests). Nothing is guessed, repaired or invented. Dropped
values are named in the PROCESSING_COMPLETED audit metadata as
unrepresentable_values -> coercion is auditable.
[fix 2] new backend/app/db_errors.py: classify_db_error() across 34 store sites
(reviews/records/processing/documents/auth). 22xxx+23502+23514 -> 422
INVALID_FIELD_VALUE, 23505 -> 409 ALREADY_EXISTS, 23503 -> 409
REFERENCE_CONFLICT, 08/53/57/58 + transport -> 503 DATABASE_UNAVAILABLE,
anything else -> 500 PERSISTENCE_FAILED. SQLSTATE + type + truncated driver
message are logged; client messages never echo the offending value. Pipeline
now propagates the classified code instead of flattening to PERSIST_FAILED.
Two bugs caught by the new tests during implementation: the SQLSTATE regex
matched the word "ERROR" (five uppercase chars) before the real code, and
require_role-style raw claims were returned un-normalized.
[live proof] reprocessed the exact failing document a37f2f60
(step08_intentionally_bad_land_record.pdf, job e1a0dd81 PERSIST_FAILED):
now job SUCCEEDED in 16s, land_record 249b4eaa created REVIEW_REQUIRED,
record_date NULL, raw '99/99/2024' preserved in extracted_fields, FMT_DATE_001
retained, HIGH-priority review task created, audit metadata carries
unrepresentable={'record_date': '99/99/2024'}.
[tests] backend 211 pass + 1 skip (was 162; +49) incl. new
tests/test_typed_persistence.py (47) covering invalid/valid date, invalid/valid
area, raw-value preservation, review creation, correction->complete->approval,
and the full classification matrix; live Supabase opt-in test green.
[known] documents.update_status runs before jobs.update_job(SUCCEEDED) in
_finish, so a client polling document status can briefly see a terminal
document while its job still reads RUNNING (observed during live verification;
cosmetic, not a data fault). Frontend untouched this step, as instructed.

[2026-09-07] STEP 5 two-role golden workflow verification (live, end to end)
[accounts] created 2 labelled test accounts: e2e-operator@example.invalid
(operator, d37144bd) and e2e-user@example.invalid (user, b3518b66). Passwords
were randomly generated for the run and NOT retained anywhere -> provision real
demo accounts with scripts/provision_account.py before any demo.
[operator flow PASS] login -> /me -> 3 dashboards -> upload doc01_clean.pdf
(doc a3d21709, checksum+size verified, object in private bucket) -> process ->
OCR -> extraction (14 fields, confidence in 0..1) -> validation -> record
8e7ce293 REVIEW_REQUIRED -> auto review task -> correction village -> Demo
Village (reason mandatory: empty reason 422) -> revalidation -> approve blocked
while review open (409) -> complete review -> APPROVED (approved_by = operator,
approved_at set) -> audit -> refresh shows persisted APPROVED -> export.
Terminal immutability holds: re-correct 409, double approve 409.
[user flow PASS] login, /me role=user, dashboard, search finds the approved
record, open record, extraction, validation, status, export -> all 200.
All 11 privileged actions denied 403 INSUFFICIENT_ROLE (upload, process, review
list/create/detail, correction, complete, approve, reject, audit, mock-LRMS);
record provably unchanged afterwards. Signup cannot self-elevate; retired
verifier token 401.
[db PASS] 0 orphans across land_records/extracted_fields/validation_results/
review_tasks; 14 unique field names; 1 correction with old->new and
changed_by=operator; audit 50 rows with 0 null actors; chk_approved_pair holds.
[security PASS] built bundle + frontend source contain no service-role key, no
AI provider key, no JWT; only VITE_API_URL is exposed. audit_logs has no
update/delete path in the backend and UPDATE/DELETE are revoked from
anon/authenticated at the DB.
[FINDING P1 - real] duplicate-processing guard is a check-then-act race:
POST /process twice ~0.9s apart created TWO jobs (6b1d1fe7, f509d617), both
ran a full pipeline incl. a second Gemini call. The handler reads
documents.processing_status but PROCESSING is only set later inside the
background task, so the window is open until the worker starts. Data integrity
held (UNIQUE(document_id) on land_records kept it to one record); cost and a
last-write-wins race are the real impact. Frontend submit guards mitigate normal
use. NOT fixed in Step 5 (verification only).
[FINDING P2] documents.processing_status stays REVIEW_REQUIRED after its record
is APPROVED - the document status is never advanced on approval.
[counts] backend 211 pass + 1 skip, frontend 147/147, tsc/lint/build green,
live workflow 57 PASS / 1 real FAIL (the other reported FAIL was my assertion
reading record.status at the wrong nesting level - the API is correct).

[2026-09-07] MASTER MVP REMEDIATION (4 confirmed fixes, all verified live)
[fix 1 - P1 duplicate-processing race] Step 5 proved two concurrent /process
requests produced TWO jobs and TWO AI calls. Root cause: the handler read
documents.processing_status, but PROCESSING is only written later by the
background task, so a read-then-act guard stayed open until the worker started.
Fix: DocumentStore.claim_for_processing() - a single conditional UPDATE
(... WHERE id = ? AND processing_status <> 'PROCESSING') that Postgres
serializes - called before the job is created. No Redis, no new infrastructure.
Live: two threaded requests -> [202, 409], exactly ONE new job.
[fix 2 - P1 login abuse] backend/app/auth/rate_limit.py: in-process fixed
window, counts only FAILED attempts, keyed by (client, email), reset on a real
sign-in. Config login_max_attempts=10 / login_window_seconds=300. Live: 429
after exactly 10 failures, correct password refused while throttled, a
different account unaffected. Known limits stated in the module docstring
(per-process, resets on restart).
[fix 3 - P1 role/status freshness] require_role now re-reads the user from the
database on PRIVILEGED actions only (plain reads still authorize from the
verified token and cost no round trip). A demotion or suspension therefore
takes effect on the next privileged request instead of lingering to token
expiry. Live: demoted operator's existing token -> 403 INSUFFICIENT_ROLE,
suspended -> 401, both restored afterwards.
[fix 4 - P1 role-blind UI] AppShell showed Upload and Review Queue to every
role, and Upload/DocumentProcessing/Reviews had no role gating, so a read-only
user was offered actions the backend would refuse. New
frontend/src/components/roles.js (isOperator/isReadOnly, fails closed on
malformed input); nav filtered, Upload and Reviews render an honest
"Operator access required" panel, Reviews no longer fires a request guaranteed
to 403, Processing start/retry disabled. Presentation only - RBAC stays
server-side.
[security] .gitignore now covers opencode.json (it carries a plaintext Stitch
X-Goog-Api-Key). Value never printed. Built bundle re-scanned: 0 hits for
service_role / GEMINI / OPENROUTER / AIza / X-Goog / AUTH_SECRET / JWT prefix.
[tests] backend 219 pass + 1 skip (was 211; +8: 2 race, 3 role-freshness,
3 rate-limit); frontend 154 pass (was 147; +7 role helper); tsc/oxlint/build
clean; live Supabase opt-in green; live matrix 30/30 after fixes.
[live db] 6 users (4 operator / 2 user), 0 orphans in land_records /
extracted_fields / validation_results / review_tasks, 0 duplicate records per
document, audit 53 rows with 0 null actors, RLS 12/12 enabled with 0 policies.
[accounts] operator.test@example.test and user.test@example.test were
provisioned by the project owner (not by me) at ~11:27 and were left untouched.
e2e-operator@example.invalid / e2e-user@example.invalid remain as the audit
actors for record 8e7ce293 - deleting them would NULL that actor evidence.
[deferred P2] documents.processing_status is not advanced when its record is
APPROVED (document still reads REVIEW_REQUIRED); document terminal status is
set before the job is marked SUCCEEDED; 4 orphan 47-byte storage objects from
2026-09-04; reference_data is DEMO-only so a live READY_FOR_APPROVAL verdict
needs a correction first.

[2026-09-07] FRONTEND DESIGN TRANSFORMATION (foundation + copy + real-browser QA)
[found in browser QA - REAL BUG, fixed] App.jsx called setUser(me) after
GET /me but never imported it. The ReferenceError was swallowed by an empty
.catch(), so the signed-in user was NEVER restored on refresh: the sidebar lost
its identity and, once the nav became role-aware, an operator silently lost
Upload and Review Queue on every reload. Fixed the import, made the catch report
unexpected faults, and added api/appImports.test.ts to guard the bug class
(nothing type-checks a bare identifier inside .jsx).
[tokens] added the missing layers: page-title tier, weight + tracking scales,
one shared focus ring, disabled opacity, row-height and motion scales, and seven
typographic role classes (t-title/t-section/t-eyebrow/t-label/t-value/t-meta/
t-help) so hierarchy is a system decision instead of a per-page choice.
[index.css] was still the old "Minimal QA styles" declaring a SECOND global
baseline (system-ui + #f4f4f2) competing with tokens.css, plus four dead classes.
Reduced to a reset + the utilities still referenced, and added a
prefers-reduced-motion guard.
[primitives] new system layer: .section (grouping by spacing, not another
bordered box), .fieldgrid, table density/numeric alignment/clickable rows,
.checklist, .finding (plain language first, rule IDs folded into details),
.conf (tier leads, percentage secondary), .toolbar, .sr-only.
[microcopy] statusLabel() in api/types.ts maps the backend vocabulary to human
labels at render time only - the wire contract is untouched. REVIEW_REQUIRED ->
"Review required", severities, priorities, verdicts. Removed "backend",
"deterministic", "terminal records", raw sizes in bytes. Help rewritten from
documentation into operator answers.
[screens] entry screen rebuilt (was a headline stranded in emptiness beside two
near-identical cards both meaning "sign in"): three capability statements plus
ONE primary path with account creation as a secondary link. Record workspace now
titled by owner + survey number instead of a UUID fragment, file size in KB,
status in words, and the inline audit table reuses the existing
describeAuditEvent() to show activity/actor/change/relative time instead of raw
action codes, UUIDs and JSON. Documents table leads with holder identity, shows
"Not found" for absent values, and rows are clickable.
[verified in a real browser] operator sees 8 nav items and the full workflow;
read-only user sees 6 and gets honest "Operator access required" panels on
#/upload and #/reviews (Reviews no longer fires a request guaranteed to 403).
Viewports checked at 1440x900, 1280x800, 1024x768 - no overflow, no clipping.
[tests] frontend 163 pass / 20 files (was 154; +9), tsc/oxlint/build clean.
Backend 219 pass + 1 skip - untouched, as required.
[not done] Dashboard, Upload, Processing, Analytics and Settings received the
inherited token/primitive improvements but no bespoke layout redesign.

[2026-09-07] OCR MULTILINGUAL UPGRADE (English + Hindi + Gujarati)
[blocker found] Tesseract 5.4.0 had ONLY eng + osd installed. Hindi and
Gujarati OCR were not inaccurate - they were impossible. Installed hin + guj
(tessdata_best, 20 MB) into a project-local ai/ocr/tessdata/ located via
TESSDATA_PREFIX, so no system install or admin rights are touched. Binaries
are gitignored.
[second gap] pipeline.py built TesseractOcrEngine() with NO language, so every
page was read as eng regardless of what the uploader declared. documents.language
reached the AI extractor but never the OCR engine.
[new] ai/ocr/script_detect.py - per-page routing. OSD is consulted first but
only trusted for a CONFIDENT non-Latin verdict: measured on our fixtures it
called a fully Gujarati page "Latin" at confidence 1.17. The reliable signal is
a probe pass with eng+hin+guj followed by Unicode-block counting, which also
detects pages carrying BOTH English labels and local-script values. Digits and
punctuation are excluded so identifiers cannot drag routing to the wrong model.
Detection: 7/7 fixtures correct, ~1s/page.
[new] ai/ocr/preprocess.py - conservative conditioning only: OSD-measured
orientation, upscale toward 300 DPI, grayscale, contrast stretch ONLY on
genuinely low-contrast pages. Deliberately NOT done (each destroys evidence in
these scripts): binarisation, unsharp masking, morphological despeckling,
cropping - the last three erase matras, nuktas and faint strokes.
[measured, synthetic fixtures] mean CER 0.2550 -> 0.0472 (-81%).
  english   0.0011 -> 0.0011  (ZERO regression)
  hindi     0.7143 -> 0.2143  (-70%)
  gujarati  0.6797 -> 0.0427  (-94%)
  mixed     0.1940 -> 0.0368 / 0.0334  (-81% / -83%)
Hindi remains the weakest (CER 0.21, WER 0.49) - Devanagari conjuncts/matras.
[honest scope] doc04-doc07 are SYNTHETIC development fixtures with ground truth
exact by construction (scripts/make_multilingual_docs.py, Nirmala UI font).
They measure whether the right language model is loaded and can read a clean
render. They do NOT measure real scanned-document accuracy and must not be used
to claim it - dataset/ground_truth/MULTILINGUAL_NOTE.txt states this and names
what a real evaluation set requires. No train/test split exists yet.
[preserved] OCR returns the ORIGINAL script verbatim; no transliteration, no
translation, no semantic correction of identifiers. Test asserts Gujarati output
contains Gujarati codepoints.
[tests] backend 233 pass + 1 skip (was 219; +14 OCR tests). Frontend 163 pass,
tsc/lint/build clean. Zero Gemini/OpenRouter calls spent.

[2026-09-07] DEMO MODE (controlled demonstration path, no external AI/OCR)
[why] A live SIH demonstration should not depend on provider quota, network or
model variability. Demo Mode replays a precomputed OCR/extraction fixture for a
known document; everything after that stage is the same code Live Mode runs.
[architecture] No new pipeline. PipelineDeps already exposed ocr_engine and
ai_service injection seams, so demo stages are injected there and every later
stage (validation, confidence, persistence, review, correction, approval,
audit) is untouched and shared. Live Mode is the default and is unchanged.
[recognition] By SHA-256 of the document bytes, never filename - the upload
path already stores that checksum on the documents row. A renamed copy still
matches; an unrelated file is refused with 422
DEMO_DOCUMENT_NOT_RECOGNISED rather than guessed at. No automatic
live-failure -> demo fallback: the modes stay explicit.
[db] NO SCHEMA CHANGE. Demo runs are tagged via the existing
processing_jobs.pipeline_version = 'v1-demo' (live stays 'v1'), plus
execution_mode / fixture_id / external_ai_calls=0 / external_ocr_calls=0 in the
existing audit_logs.metadata JSONB.
[security] DEMO_MODE is server-side; with it false the backend answers 403
DEMO_MODE_DISABLED whatever the client sends. Demo Mode is not a permission
bypass - read-only users still cannot upload, process or approve (verified live).
[fixture] demo/fixtures/doc10_rtc_hindi_scan/ built ONCE by
scripts/build_demo_fixture.py (one development-time Gemini call). Runtime makes
zero external calls. The capture is honest: the AI misread three identifiers on
the worn scan (survey 445/2 vs 145/2, khasra 76 vs 78, khata 23 vs 123) and
those values are preserved, not corrected.
[live verified] renamed upload 201 -> checksum matched manifest -> demo process
202 -> job SUCCEEDED tagged v1-demo in 11.5s -> 14 fields persisted -> real
validation ran -> audit carried execution_mode=demo, external calls 0 ->
operator approved (APPROVED, approved_by/at set) -> read-only user refused 403
at upload and at approve -> record survived re-login. 22/25 checks passed; the
3 failures were my test EXPECTING a review-required verdict.
[honest finding] the canonical demo document validates CLEAN
(READY_FOR_APPROVAL, 0 findings): its village/tehsil/district match the seeded
DEMO reference data and the misread identifiers are still format-valid, so no
rule fires. The demo therefore shows the straight-through path, not the
review/correction path. Documented rather than forced.
[tests] backend 251 pass + 1 skip (was 233; +18 demo tests incl. renamed-copy
match, wrong-document refusal, zero-external-call assertion with httpx blocked,
determinism, full pipeline with real validation/persistence/audit, RBAC, and
live-not-tagged-demo). Frontend 163 pass, tsc/lint/build clean.
[docs] demo/README.md added; DEMO_MODE currently true in backend/.env for the
demonstration - set false for production.

[2026-09-07] FRONTEND POLISH PASS 2 (the screens left un-redesigned in pass 1)
[stat tiles] StatCard rebuilt: a 3px left tone rule (review/failed/verified)
carries urgency while the card stays white, so a row reads as one calm strip
instead of a traffic light; value up to 2.25rem tabular; optional href turns a
count of outstanding work into the route that acts on it (hover reveals a
chevron). Dashboard reordered so outstanding work leads: Needs review ->
Flagged -> Approved -> Documents, with Needs review and Flagged linking to
their queues. Dropped the meaningless '20% pipeline throughput' metric.
[dashboard] recent-records table now leads with the holder name instead of a
truncated UUID, shows 'Not found' for absent values, and rows are clickable.
'Last sync: 8:49:08 PM' -> 'Updated just now'. Activity panel now explains
where history actually lives rather than reading as a dead panel.
[analytics] distribution rows were printing raw backend codes
(REVIEW_REQUIRED, VALIDATION_FAILED, WARNING) - now humanised via statusLabel.
Jargon removed: '18 check(s), not-checked excluded', 'Across 9 recent job(s)',
'Deterministic rule outcomes', 'Live document pipeline states'.
[upload] the page was a drop zone floating in an empty rectangle. Added a
four-step 'what happens next' strip (read -> extract -> check -> you decide)
shown only before a file is staged. '(backend-enforced)' and
'Backend-created document' removed.
[settings] 'Bearer token in this tab only', 'Stateless token session,
validated against the backend', 'Backend API URL' -> plain language.
[global] removed the env='Live backend data' chip from all 28 sites: it told
an operator nothing and, with Demo Mode now shipping, a demo-processed record
would still have claimed 'Live backend data'.
[bug I introduced and fixed] Analytics rendered blank - statusLabel used but not
imported. tsc, oxlint, vitest and vite build ALL passed with it broken, because
.jsx is not type-checked. Only the browser caught it. Same class as the earlier
App.jsx setUser defect. Added a repo-wide scan for helpers used without import
(now clean across every view/component).
[false alarm, recorded so it is not re-chased] the record page appeared to fail
with 'Unable to connect'; that was my own test error - I was on the preview
build at :4173, which the backend CORS allow-list correctly rejects
(FRONTEND_ORIGINS=http://localhost:5173). On :5173 a clean load renders fine.
[tests] frontend 163 pass / 20 files, tsc + oxlint clean, build green
(CSS 44.3 kB / 8.0 kB gz). Backend 251 pass + 1 skip, untouched.
[still not redesigned] DocumentProcessing stepper, and the record workspace is
still card-heavy (the .section/.fieldgrid primitives exist but are unadopted
there).

## Decision 2026-09-20 — Security and configuration hardening

```text
Completed a scoped security pass without redesigning the application:
removed the local OpenCode Google credential and replaced it with
{env:STITCH_API_KEY}; added a safe opencode.example.json and repository secret
scanner; enforced explicit CORS methods/headers and rejected wildcard origins;
required strong AUTH_SECRET configuration and iat/exp JWT claims; active user
and role state is re-read on every authenticated request; bounded the
in-process login limiter; removed raw database/provider error bodies and
tracebacks from logs; and added focused regression tests.

Logout remains intentionally stateless: the client discards its bearer token;
global invalidation requires AUTH_SECRET rotation or account deactivation.
The external Google credential still requires owner-controlled revocation or
rotation; no revocation is claimed here.
```

## Decision 2026-09-20 — PostgreSQL/Supabase audit

```text
Live read-only verification through the configured Supabase project confirmed
the 12 expected public tables, current user/operator/admin role vocabulary,
the expected live columns and foreign-key relationships, private storage bucket
configuration, and deny-by-default behavior for unauthenticated table/storage
access. Data checks found no relational or timestamp or lifecycle mismatches.

Three duplicate document-checksum groups and four unreferenced storage objects
(188 bytes total) remain as cleanup candidates; no production data or objects
were deleted. The generated supabase/database.types.ts was missing the live
users.id_number column and was corrected. No new database migration was
needed: existing constraints, RLS posture, storage configuration, and indexes
were retained pending catalog-level SQL/EXPLAIN access through the unavailable
Supabase SQL MCP surface.
```

## Decision 2026-09-20 — Atomic processing persistence

```text
The pipeline's final result persistence now uses the new PostgreSQL function
persist_processing_result() from migration
20260920140000_atomic_processing_persistence.sql. OCR rows, land record,
extracted fields, validation results, final document status, review creation,
job success, and completion audit are one database transaction. OCR/AI work and
initial RUNNING/PROCESSING state remain outside the transaction intentionally.

The function is SECURITY INVOKER with pinned search_path, typed scalar inputs,
typed JSONB conversion, no dynamic SQL, and service_role-only execution. It is
retry-safe, reuses open reviews, protects terminal records, and returns an
idempotent result for repeated completion of an already-successful job.
Failure reconciliation only marks a document FAILED while it is still
PROCESSING, so a late duplicate worker cannot overwrite a successful result.
The migration must be applied before deploying the updated backend; hosted RPC
execution was not claimed because the task surface did not expose SQL migration
execution.
```

## Decision 2026-09-21 — Processing lifecycle reliability

```text
The process acceptance boundary now claims a document atomically before job
creation and releases that claim if job creation fails. Demo fixture resolution
also happens before claiming, so rejected demo inputs cannot strand a document
in PROCESSING.

Restart reconciliation moved to the PostgreSQL function
reconcile_stale_processing_jobs() from migration
20260921100000_processing_lifecycle_hardening.sql. It marks stale PENDING/
RUNNING jobs FAILED and releases matching PROCESSING documents in one
transaction. The function is service_role-only, SECURITY INVOKER, and has a
pinned search_path.

GET /documents/{id}/status remains backward-compatible while exposing the
latest job id/status, safe error code, and timestamps when present. The
document processing status remains distinct from land_records approval status:
approval/rejection is authoritative on the record, while the document status
describes ingestion/processing completion. No fabricated per-stage telemetry
was added because the pipeline does not persist those sub-stages.
The new migration must be applied before deploying the updated backend; live
SQL execution was not claimed because the connected Supabase surface was
read-only for migration execution.
```

## Decision 2026-09-21 — Authenticated document source pages

```text
Added GET /api/v1/documents/{document_id}/pages/{page_number}. It uses the
existing private storage backend and server-side read authorization, validates
the generated storage-path shape, downloads source bytes without exposing the
path, and renders only the requested page through the existing PyMuPDF helper.
The response is a private no-store JPEG with safe error envelopes and a render
pixel cap.

The existing extraction schema's nullable source_page/source_text/bounding_box
fields are now represented explicitly in the document extraction response.
They remain null when the provider did not supply real grounding evidence;
coordinates are never invented. No frontend or database migration was added.
Live authenticated storage smoke verification remains a deployment step.
```

## Decision 2026-09-21 — Review and audit API hardening

```text
The review queue audit found server-side status/assignment filtering, but
priority, free-text search, assignee shortcuts, and sorting were still
client-side; pagination was absent. The backend now applies priority filtering
and supports opt-in limit/offset pagination with {items,total,limit,offset}.
Calls without those new parameters retain the existing array response, so the
current frontend remains compatible.

Per-record audit history received the same opt-in pagination contract and a
stable timestamp/id ordering. The endpoint remains operator-only and audit
rows remain append-only through the application and database permissions. A
global audit feed was not added because the current product explicitly uses
record-scoped timelines and has no workspace-wide audit consumer.

Review correctness remains server-enforced: operator-only actions, mandatory
correction reasons with validation reruns, terminal-record immutability,
authoritative approval blockers, and duplicate-action rejection. Successful
mock-LRMS dispatches now append MOCK_LRMS_DISPATCHED without auditing rejected
or unauthorized attempts. Existing review tests cover correction, terminal,
approval, rejection, and authorization behavior; new tests cover queue/audit
pagination and dispatch auditing.
```

## Decision 2026-09-21 — Backend API contract audit

```text
Compared the FastAPI routes, Pydantic schemas, frontend client, and
10_API_SPECIFICATION. The application routes and client already consistently
used /api/v1; the specification had stale unversioned /api examples, omitted
the authenticated source-page route, used the wrong 403 wording, and omitted
the implemented 413 upload response. Documentation and one frontend type
comment were corrected; no backend response shape or AI/provider path changed.

Error handlers preserve request IDs in both the JSON envelope and
X-Request-ID header for tested 401/403/422/429/503 paths, while generic 500
responses remain opaque. No Gemini or other AI API key was used.
```

## Decision 2026-09-21 — Targeted PostgreSQL performance pass

```text
The query audit found the document-status endpoint loading complete job
history and the processing recovery path scanning that same history. Both now
use bounded one-row queries. Review queue and reference-data reads use
explicit projections. Migration
20260921130000_query_path_indexes.sql adds composite indexes matching newest
job lookup and per-record chronological audit history, then removes the
redundant single-column component indexes.

Record search remains escaped ILIKE with pagination; no trigram/full-text or
fuzzy geographic acceptance was introduced without workload evidence. Raw
extracted values remain preserved and duplicate detection remains a review
signal. EXPLAIN was not run because no psql/Supabase CLI or SQL-capable MCP
surface was available; deployment should run read-only plans after applying
the migration. No Gemini/API key was used.
```

## Decision 2026-09-21 — Backend test hardening

```text
The backend risk matrix was compared with the existing tests before adding
coverage. The suite already exercised the major authentication, upload,
processing, validation, review, audit, and transaction rollback paths. The
new regression tests cover the API-boundary TOKEN_EXPIRED contract, malformed
provider-response failure with no partial business persistence, and duplicate
rejection without duplicate audit history. Focused verification passed 210
tests. The full backend suite passed 287 tests and skipped 1, with 5 known
multilingual OCR failures caused by TesseractNotFoundError because the
external Tesseract executable is not installed in the test environment.
pytest-cov was unavailable, so no coverage percentage was claimed. No
Gemini/API key or live external service was used.
```

# END OF MEMORY.md
