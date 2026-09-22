# Free SIH 2026 demo deployment on Vercel

This repository is deployed as one Vercel project from the root:

```text
Vercel Dockerfile.vercel → FastAPI + built React/Vite bundle
                         ↘ Tesseract 5 (eng/hin/guj)
                         ↘ Supabase private storage/database/RLS
                         ↘ Gemini 2.5 Flash-Lite → OpenRouter free fallback
```

The container is stateless. Persistent documents, processing jobs, records and
audit history remain in Supabase. Never place backend secrets in the frontend,
Git, or the Docker image.

## Vercel project

Import this repository as one Vercel project with the repository root as the
project root. Vercel detects `Dockerfile.vercel`; its final image listens on
the platform-provided `$PORT`. Do not configure a separate frontend project or
Render service.

The image builds the frontend with `npm ci` and `npm run build`, copies
`frontend/dist` into the final Python image, and FastAPI serves both the
`/api/*` routes and the React fallback. In production the frontend API client
uses same-origin requests. Local Vite development still defaults to
`http://127.0.0.1:8000`; `VITE_API_URL` remains available for QA.

## Supabase

Use the existing project configured by `SUPABASE_URL`. Apply the migrations in
`supabase/migrations/` in filename order. The processing migrations are
required before deployment:

```text
20260920140000_atomic_processing_persistence.sql
20260921100000_processing_lifecycle_hardening.sql
```

Verify the private `land-record-documents` bucket, its 10 MB limit, allowed
PDF/PNG/JPEG/TIFF types, RLS, and service-role-only processing functions. Do
not make the bucket public.

## Vercel environment variables

Configure these as Vercel server-side environment variables. `GEMINI_API_KEY`
and `OPENROUTER_API_KEY` must not be prefixed with `VITE_`.

```text
SUPABASE_URL
SUPABASE_SERVICE_ROLE_KEY
AUTH_SECRET
AUTH_TOKEN_EXPIRE_MINUTES=480
STORAGE_BUCKET=land-record-documents
MAX_UPLOAD_MB=10
GEMINI_API_KEY
OPENROUTER_API_KEY
AI_PROVIDER=gemini
AI_MODEL=gemini-2.5-flash-lite
AI_TIMEOUT_SECONDS=60
AI_FALLBACKS=openrouter:openrouter/free
AI_CACHE_ENABLED=true
AI_CACHE_TTL_SECONDS=3600
AI_CACHE_MAX_ENTRIES=256
FRONTEND_ORIGINS=https://<your-vercel-domain>
ENVIRONMENT=production
LOG_LEVEL=INFO
DEMO_MODE=true
PROCESSING_REQUEST_BOUND=true
```

`DEMO_MODE=true` enables the labelled fixture-backed demonstration. It skips
external OCR/AI calls only for the known fixture path; validation, persistence,
review, approval/rejection, audit and export remain real. Set it to `false` for
live provider processing.

`PROCESSING_REQUEST_BOUND=true` is required for this single-container
deployment. The process endpoint waits for the complete OCR/extraction/
validation/persistence unit and returns the persisted terminal job state. This
prevents a platform response from detaching work that could be terminated
after the request finishes. Keep specimens within the Vercel plan's request
duration limit; the recorded fixture-backed demo run is about 11.5 seconds and
recent live jobs were roughly 1–2 minutes.

Provision an operator out-of-band; self-registration creates read-only users
only:

```powershell
backend\.venv\Scripts\python scripts\provision_account.py `
  --email operator@example.com --name "Demo Operator" `
  --id-number OP-001 --role operator
```

The script prompts for the password and does not print it or store it in the
repository.

## Smoke verification

From the repository root:

```powershell
python scripts\deployment_smoke.py
python scripts\deployment_smoke.py --supabase
python scripts\deployment_smoke.py --url https://<your-vercel-domain>
cd frontend
npm install
npm run build
```

Then verify the workflow with a non-sensitive specimen:

```text
login → upload → process → OCR → extraction → validation
→ review/approval → record retrieval → JSON export → source page viewer
```

For the fixture-backed demo, confirm the audit metadata identifies demo mode
and reports zero external AI/OCR calls. For live mode, confirm the selected
Gemini model and OpenRouter fallback in server configuration, never in the
browser.

## Rollback and recovery

Use Vercel's previous deployment rollback. Keep the database-compatible image
and configuration together; do not reset Supabase or delete audit history.
On a process failure, inspect the persisted job/document status, then retry
the failed document through the existing API. Startup reconciliation remains
the recovery path for jobs interrupted by a container restart.
