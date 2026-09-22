# Backend — Land Record Digitization API (STEP 03 foundation)

FastAPI + Supabase (service_role, server-side only). Versioned API under `/api/v1`.

## Setup (Windows PowerShell)

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item ..\.env.example .\.env
# Edit .env: set AUTH_SECRET to a strong random value, add SUPABASE_URL +
# SUPABASE_SERVICE_ROLE_KEY. Never commit .env.
```

## Start

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload --port 8000
```

Without Supabase keys the app still starts; `/health/database` reports 503
until keys are configured.

## Test

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m pytest -q
```

Tests force `ENVIRONMENT=testing`, a fixed `AUTH_SECRET`, and empty Supabase
settings — they never touch the live database. AI tests use a mocked HTTP
transport; no provider calls leave the machine.

## AI provider layer (STEP 06)

Application code calls `extract_land_record()` in `app.ai` — never a
provider adapter directly. First provider: Gemini (REST via httpx, no SDK).
The free-demo default is `gemini-2.5-flash-lite`, which supports the existing
structured-output extraction contract. Model/key/timeout are env-driven:
`AI_PROVIDER`, `AI_MODEL`,
`AI_TIMEOUT_SECONDS`, `GEMINI_API_KEY` (server-side only).

STEP 13 reliability: `AI_FALLBACKS` adds ordered `provider:model` lanes
(OpenRouter supported, with its native `models` fallback list); each lane
gets one attempt plus one retry on transient failures only (rate limit,
timeout, unavailable) — auth/bad-request/bad-response raise immediately.
Repeat extractions hit a bounded TTL cache keyed by source + pipeline +
route chain + prompt/schema versions. Every result records
`attempted_routes` (provider/model/outcome/attempts).

One controlled live request (needs `GEMINI_API_KEY` in `.env`):

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python scripts\smoke_gemini.py
```

## Endpoints (foundation)

| Method | Path | Auth | Purpose |
| ------ | ---- | ---- | ------- |
| GET | `/health` | no | Liveness + version |
| GET | `/health/database` | no | Supabase reachability |
| GET | `/health/ai` | no | AI wiring status (`not_configured`) |
| POST | `/api/v1/auth/login` | no | Email + password → Bearer token |
| POST | `/api/v1/auth/logout` | no | Stateless logout acknowledgement |
| GET | `/api/v1/auth/me` | yes | Current user (refetched, active only) |
| POST | `/api/v1/documents` | yes (operator+) | Upload PDF/PNG/JPEG/TIFF (≤10 MB) → `{document_id, status}` |
| GET | `/api/v1/documents/{id}` | yes | Document metadata + processing status |
| GET | `/api/v1/documents/{id}/status` | yes | Processing status only |
| POST | `/api/v1/documents/{id}/process` | yes (operator+) | Start pipeline job → 202 (background) |
| GET | `/api/v1/documents/{id}/extraction` | yes | Extracted fields + confidence + source |
| GET | `/api/v1/documents/{id}/validation` | yes | Validation verdict + issues |
| POST | `/api/v1/reviews` | yes (operator+) | Create review task for a record |
| GET | `/api/v1/reviews` | yes (verifier+) | List review tasks (status/assignee filters) |
| GET | `/api/v1/reviews/{id}` | yes (verifier+) | Task + record + extracted fields + validation |
| PATCH | `/api/v1/reviews/{id}/fields/{field}` | yes (verifier+) | Correct a field (reason required, revalidates) |
| POST | `/api/v1/reviews/{id}/complete` | yes (verifier+) | Complete a review |
| POST | `/api/v1/records/{id}/approve` | yes (verifier+) | Approve (blocked while issues remain) |
| POST | `/api/v1/records/{id}/reject` | yes (verifier+) | Reject (reason required) |
| GET | `/api/v1/records/{id}/audit` | yes (verifier+) | Audit history for a record |
| GET | `/api/v1/records` | yes | Search records (owner/survey/village/… + page/limit) |
| GET | `/api/v1/records/{id}` | yes | Record + extracted fields + validation + document |
| GET | `/api/v1/records/{id}/export` | yes | Full record export (JSON, labeled v1) |
| GET | `/api/v1/dashboard/summary` | yes | Counts, open reviews, avg confidence |
| GET | `/api/v1/dashboard/processing` | yes | Jobs by status + recent jobs |
| GET | `/api/v1/dashboard/validation` | yes | Issues by severity/status, blocked docs |
| POST | `/api/v1/integrations/mock-lrms` | yes (verifier+) | Demo receiver, APPROVED records only |

Interactive docs: `http://127.0.0.1:8000/docs`
