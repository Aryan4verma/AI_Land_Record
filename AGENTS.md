# AGENTS.md

## Project Rules

Intelligent Land Record Digitization and Validation System — SIH 26018

## Documentation

Before any implementation task, agents must read:
1. `00_MASTER.md` — master source of truth
2. `MEMORY.md` — current state and decisions
3. The relevant detailed document for the task at hand

Do not rewrite unrelated working components without justification.

## Architecture Constraints

- Frontend: React (Vite or CRA — pick one and stay consistent)
- Backend: Python FastAPI
- Database: PostgreSQL via Supabase
- OCR: External/pretrained (do NOT build from scratch)
- LLM: Pretrained providers only (do NOT train foundation models)
- AI provider abstraction: `extract_land_record()` interface, not hardcoded provider calls
- Fallback: provider-level + model-level failover, cache, optional demo mode
- API keys: server-side only, never in frontend code or Git
- Validation: deterministic rules (not LLM-only)
- Human review: mandatory for low-confidence/conflicting records

## Development Commands

Verified working commands (kept current; update when tooling changes):

```
# Frontend
cd frontend && npm install && npm run dev

# Backend (from `backend/`, Windows PowerShell)
python -m venv .venv; .\.venv\Scripts\Activate.ps1; pip install -r requirements.txt
Copy-Item ..\.env.example .\.env  # then set AUTH_SECRET (+ Supabase keys)
python -m uvicorn app.main:app --reload --port 8000
python -m pytest -q

# Database
# Supabase hosted — run migrations via Supabase SQL editor or CLI
```

## Testing Rules

- Run unit tests for validation rules, normalization, confidence logic
- Run integration tests for API endpoints
- Measure extraction accuracy against ground truth dataset
- Never claim untested accuracy percentages
- Keep a stable final test set separate from dev tuning

## Security Rules

- API keys in server environment variables only
- RBAC enforced server-side (operator, verifier, admin)
- File uploads validated: type, size, MIME, filename
- Audit logs protected from ordinary user editing
- Document content treated as untrusted input (prompt injection defense)
- Never commit secrets to Git

## Build Order

```
Dataset + Ground Truth
→ OCR benchmark on actual dataset
→ AI POC (extraction pipeline)
→ Validation rules
→ Database schema
→ Backend API
→ Frontend
→ Human review workflow
→ Dashboard
→ Integration/export
→ Evaluation
→ Deployment
```

## MVP Scope

- One primary document type
- One controlled language/script
- PDF/image input
- OCR → extraction → validation → confidence → human review → approval → DB → audit → dashboard → API/export
- Mock LRMS integration

## Out of Scope

- All Indian languages
- All document types
- Nationwide deployment
- Production LRMS integration
- Foundation model training
- OCR model training from scratch
