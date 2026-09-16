# 13_DEPLOYMENT_RUNBOOK.md

# Intelligent Land Record Digitization and Validation System

## Deployment and Operations Runbook

**Depends On:** `09_DATABASE_SCHEMA.md`, `10_API_SPECIFICATION.md`, `11_SECURITY_DESIGN.md`

---

# 1. Purpose

Define how the project is installed, configured, tested, deployed, and recovered.

The deployment process must be repeatable by another team member or AI coding agent.

---

# 2. Project Structure

Actual (differs from the early sketch: docs live at the repo root, the
AI extraction package is named `extract`, and there is no separate
`tests/` top-level dir — backend tests live in `backend/tests/`):

```text
ai-land-records/
├── 00_MASTER.md … 14_UI_UX_SPECIFICATION.md, MEMORY.md, AGENTS.md
├── frontend/            # Vite + React QA app (disposable; Stitch replaces it)
├── backend/
│   ├── app/             # FastAPI app (auth, documents, processing, records, reviews, ai)
│   ├── scripts/         # smoke_gemini.py, verify_failover.py
│   ├── tests/           # pytest suite
│   ├── requirements.txt
│   ├── pytest.ini
│   ├── Procfile         # web: uvicorn app.main:app --host 0.0.0.0 --port $PORT
│   └── runtime.txt      # pinned Python for hosted deployment
├── ai/
│   ├── ocr/
│   ├── extract/
│   ├── validation/
│   └── confidence/
├── dataset/             # raw_documents, ground_truth, ocr_outputs, model_outputs, evaluation
├── scripts/             # make_sample_docs.py, evaluate_all.py
└── supabase/            # migrations/*.sql, database.types.ts
```

---

# 3. Environment Separation

Use:

```text
development
testing
production/demo
```

Do not mix production secrets with development configuration.

---

# 4. Environment Variables

Implemented set (see root `.env.example`; placeholders only, never values):

```text
SUPABASE_URL / SUPABASE_ANON_KEY / SUPABASE_SERVICE_ROLE_KEY / DATABASE_URL
AUTH_SECRET / AUTH_TOKEN_EXPIRE_MINUTES
STORAGE_URL / STORAGE_BUCKET / MAX_UPLOAD_MB
GEMINI_API_KEY / OPENROUTER_API_KEY / NVIDIA_API_KEY / GROQ_API_KEY
AI_PROVIDER / AI_MODEL / AI_TIMEOUT_SECONDS / AI_FALLBACKS
AI_CACHE_ENABLED / AI_CACHE_TTL_SECONDS / AI_CACHE_MAX_ENTRIES
ENVIRONMENT / FRONTEND_ORIGINS / LOG_LEVEL
DEMO_MODE (flag only — Demo Mode behavior is NOT implemented, see §14)
```

Actual values must never be committed.

Local files: root `.env.example` is the template; `backend/.env` is the
live local file (the app also accepts `./.env` from the working directory).

---

# 5. Local Setup

## Frontend

```powershell
cd frontend
npm install
npm run dev        # serves on http://localhost:5173
npm run build      # production bundle into frontend/dist/
```

Deployed builds talk to the backend URL baked in at build time via
`VITE_API_URL` (defaults to `http://127.0.0.1:8000`; still overridable
in-app for QA).

## Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item ..\.env.example .\.env   # then fill AUTH_SECRET + Supabase/AI keys
python -m uvicorn app.main:app --reload --port 8000
python -m pytest -q
```

Hosted start (Procfile): `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
with `runtime.txt` pinning the Python version.

## AI/OCR tooling (separate venv)

```powershell
python -m venv ai\.venv
.\ai\.venv\Scripts\Activate.ps1
pip install -r ai\requirements.txt
# Tesseract 5 binary required: winget install -e --id UB-Mannheim.TesseractOCR
```

## Database

Supabase hosted — no local database to create.

```text
Apply migrations in order via Supabase SQL editor/MCP (files in supabase/migrations/):
  land_records_foundation → land_records_foundation_fixes → storage_documents_bucket
  → add_users_id_number → two_role_architecture
Seeded automatically: roles (user/operator/admin) + DEMO reference chain.
Private bucket land-record-documents is created by the storage migration
(10 MB limit, PDF/PNG/JPEG/TIFF).

## Seeding Users

Self-registration (`POST /api/v1/auth/register`) creates read-only `user`
accounts ONLY. There is no privileged account-creation API and none should be
added. OPERATOR accounts are provisioned out-of-band by an operator of the
deployment.

### Preferred: the provisioning script

`scripts/provision_account.py` is the supported path. It prompts for the
password with `getpass`, so the password never appears in shell history, the
process list, or any log; it refuses `admin` and the retired `verifier`; and it
refuses any email that already exists (no silent role changes).

```powershell
# one operator (full document + review/approval workflow)
backend\.venv\Scripts\python scripts\provision_account.py `
  --email operator@example.com --name "Operator One" `
  --id-number OP-001 --role operator

# one read-only user (equivalent to a normal public signup)
backend\.venv\Scripts\python scripts\provision_account.py `
  --email user@example.com --name "Reader One" `
  --id-number USER-001 --role user
```

The script prints the created id/role/status and never a password or hash.

### Fallback: manual SQL

If the script cannot be run, generate the bcrypt hash locally so the password
never travels in cleartext, then insert with the hash only:

```powershell
cd backend
.\.venv\Scripts\python -c "from app.auth.security import hash_password; print(hash_password('CHOOSE-A-STRONG-PASSWORD'))"
```

```sql
-- Operator: full document + review/approval workflow.
INSERT INTO public.users (name, email, password_hash, role, status)
VALUES ('Operator One', 'operator@example.com', '<PASTED-HASH>', 'operator', 'active');

-- Read-only user (also creatable through POST /api/v1/auth/register).
INSERT INTO public.users (name, email, password_hash, role, status)
VALUES ('Reader One', 'user@example.com', '<PASTED-HASH>', 'user', 'active');
```

Log in via `POST /api/v1/auth/login` to obtain a Bearer token.
```

## Evaluation

```powershell
python scripts\evaluate_all.py --dry-run   # plan + live-call count, no-op
python scripts\evaluate_all.py             # pytest + stages + dataset/evaluation/REPORT.md
```

---

# 6. Development Startup Order

Recommended:

```text
Database
↓
Backend
↓
AI/OCR services
↓
Frontend
```

---

# 7. Deployment Order

```text
Database
→ backend
→ storage
→ AI configuration
→ frontend
→ smoke tests
```

---

# 8. Pre-Deployment Checklist

```text
All tests pass
Environment variables configured
Secrets not committed
Database migration complete
OCR tested
LLM tested
Validation tested
Fallback tested
Upload tested
Authentication tested
Audit tested
Demo documents tested
```

---

# 9. Demo Readiness Checklist

Before SIH demonstration:

```text
Internet works
Primary provider works
Fallback provider works
OCR works
Database works
Sample documents work
Cached results available
Demo Mode available
Logs accessible
API keys valid
Application deployed
```

---

# 10. Failure Recovery

## AI provider unavailable

```text
use configured fallback
```

## Database unavailable

```text
do not lose active state
restore/reconnect
```

## Backend unavailable

```text
restart service
inspect logs
run health check
```

---

# 11. Health Endpoints

Recommended:

```text
GET /health
GET /health/ai
GET /health/database
```

These should report service availability without exposing secrets.

---

# 12. Versioning

Record:

```text
application version
database version
AI pipeline version
prompt version
model/provider
```

---

# 13. Rollback

Keep the previous working deployment version available.

Rollback should restore:

```text
application
database-compatible version
configuration
```

without destroying audit history.

---

# 14. Demo Mode

> Status (2026-09-05): NOT IMPLEMENTED. Only the `DEMO_MODE`/`AI_CACHE_*`
> configuration flags exist; no demo-serving behavior reads them. Do not
> claim Demo Mode readiness until this section is implemented and labeled
> per the rules below.

Demo mode is an emergency reliability mechanism.

It may use preprocessed/cached demonstration results.

It must be clearly labeled.

It must never falsely claim that a live AI request succeeded when it did not.

# END OF 13_DEPLOYMENT_RUNBOOK.md
