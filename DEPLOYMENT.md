# Free SIH 2026 demo deployment

This runbook deploys the existing application without changing its workflow:

```text
Cloudflare Pages → Render Docker Web Service → Supabase Free
                                  ↘ Tesseract 5
                                  ↘ Gemini 2.5 Flash-Lite → OpenRouter free router
```

Never place backend secrets in the frontend, GitHub, or the Docker image.

## Supabase

Use the existing project configured by `SUPABASE_URL`. Apply the migrations in
`supabase/migrations/` in filename order. The processing migrations are
required before deploying the backend:

```text
20260920140000_atomic_processing_persistence.sql
20260921100000_processing_lifecycle_hardening.sql
```

Verify the private `land-record-documents` bucket, its 10 MB limit, allowed
PDF/PNG/JPEG/TIFF types, RLS, and the service-role-only processing functions.
Do not make the bucket public.

Set these Render backend variables only:

```text
SUPABASE_URL
SUPABASE_SERVICE_ROLE_KEY
AUTH_SECRET
FRONTEND_ORIGINS=https://<your-pages-project>.pages.dev
GEMINI_API_KEY
OPENROUTER_API_KEY
AI_PROVIDER=gemini
AI_MODEL=gemini-2.5-flash-lite
AI_FALLBACKS=openrouter:openrouter/free
DEMO_MODE=true
```

`DEMO_MODE=true` is appropriate for a fixture-backed SIH demonstration. It
does not call Gemini/OpenRouter and remains labelled in the application. Set
it to `false` when demonstrating live provider processing.

Provision an operator out-of-band; self-registration creates read-only users
only:

```powershell
backend\.venv\Scripts\python scripts\provision_account.py `
  --email operator@example.com --name "Demo Operator" `
  --id-number OP-001 --role operator
```

The script prompts for the password and does not print it or store it in the
repository.

## Render

Create a Free Web Service from the repository with:

```text
Environment: Docker
Dockerfile: Dockerfile
Health check path: /health
```

The Dockerfile installs Python 3.12 dependencies, Tesseract 5, and the
`eng`, `hin`, and `guj` language packs. It starts:

```text
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

The service must listen on Render's `$PORT`; do not hardcode port 8000 in the
deployment settings. The free instance is intentionally single-worker and
in-process rate limiting/cache are deployment-local.

After deployment, check:

```text
GET https://<render-service>.onrender.com/health
GET https://<render-service>.onrender.com/health/ai
GET https://<render-service>.onrender.com/health/database
```

## Cloudflare Pages

Create a Pages project from the repository with:

```text
Root directory: frontend
Build command: npm run build
Output directory: dist
Environment variable: VITE_API_URL=https://<render-service>.onrender.com
```

The app uses hash routes, and `frontend/public/_redirects` also provides an
SPA fallback for direct page requests. `VITE_API_URL` is the only frontend
deployment variable; do not add Supabase, JWT, or provider keys to Pages.

## Smoke verification

From the repository root:

```powershell
python scripts\deployment_smoke.py
python scripts\deployment_smoke.py --supabase
python scripts\deployment_smoke.py --url https://<render-service>.onrender.com
cd frontend
npm install
npm run build
```

Then manually verify the authenticated workflow with a non-sensitive specimen:

```text
login → upload → process → OCR → extraction → validation
→ review/approval → record retrieval → JSON export → source page viewer
```

For the fixture-backed demo, confirm the audit metadata identifies demo mode
and reports zero external AI/OCR calls. For live mode, confirm the selected
Gemini model and OpenRouter fallback in server configuration, never in the
browser.

## Rollback

Keep the previous Render image and Pages deployment available. Roll back the
application and compatible configuration together. Do not reset Supabase or
delete audit history.
