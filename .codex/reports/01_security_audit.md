# Security and Configuration Hardening Audit

Date: 2026-09-20  
Scope: security/configuration hardening only; no application redesign.

## Changed

- Removed the local hardcoded Google/Stitch credential from `opencode.json` and replaced it with the `{env:STITCH_API_KEY}` reference. Added the safe tracked template `opencode.example.json`; the local config remains ignored. The external credential was not revoked or rotated by this audit.
- Added `scripts/scan_secrets.py`, a standard-library repository scan covering tracked and non-ignored files. It reports file/rule names only and never prints matched secret values.
- Strengthened configuration validation: `AUTH_SECRET` must be a non-default value of at least 32 characters; upload/login limits are bounded; wildcard CORS origins are rejected.
- Pinned JWT validation to the expected claims (`sub`, canonical `role`, `iat`, and `exp`) and configured bounded token expiry. Authentication now re-reads the current account for every authenticated request, so deactivated accounts and role changes take effect on ordinary and privileged routes.
- Confirmed server-side authorization: records/documents use authenticated access, while processing, upload, review mutations, approval/rejection, audit, and mock-LRMS operations require the operator role. No frontend-only role restriction is relied upon, and no private-owner filter was added.
- Kept upload validation in place for bounded size, extension/MIME agreement, magic bytes, sanitized filenames, SHA-256 capture, and UUID-based storage paths.
- Tightened CORS to explicit configured origins, required client methods/headers, no credentialed browser requests, and the request-ID response header.
- Kept the dependency-free in-process login limiter, added bounded key storage, and documented the single-process/single-worker assumption.
- Removed database-driver messages, provider response bodies, raw extracted values, passwords, tokens, and exception text from logs/errors. Generic framework error responses no longer echo arbitrary exception details.
- Updated `.env.example`, security design, deployment runbook, agent guidance, and memory with the operational requirements.

## Verified

- Secret scan: `python scripts/scan_secrets.py` — passed.
- Focused backend security/regression suite: `101 passed, 1 warning`.
- Full backend suite: `256 passed, 5 failed, 1 skipped`. The five failures are existing OCR integration failures because `tesseract.exe` is unavailable on PATH; they are not caused by this hardening pass.
- Frontend regression checks: `163 passed`; typecheck, lint, and production build passed.
- `git diff --check` passed.
- Explicit config checks confirmed both `opencode.json` and `opencode.example.json` contain no literal credential and that `opencode.json` is ignored by Git.

## Remaining

- The previously exposed external Google/Stitch credential still needs owner-side revocation/rotation. This audit deliberately makes no claim that it was revoked.
- Logout remains stateless: a stolen bearer token remains usable until expiry unless the account is deactivated or `AUTH_SECRET` is rotated. This is documented and avoids introducing a session store.
- The login limiter is intentionally process-local. Multi-worker or distributed production deployment needs an edge/shared limiter; Redis was not added for the prototype.
- The five OCR tests require the existing Tesseract runtime dependency to be installed/configured before the complete backend suite can be green.
