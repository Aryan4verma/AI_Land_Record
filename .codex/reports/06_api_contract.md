# Backend API Contract Audit

Date: 2026-09-21

## Findings

The FastAPI implementation and frontend client consistently use the
`/api/v1` prefix for application routes. The API specification still showed
many unversioned `/api/...` examples and omitted the authenticated source-page
route. Its authorization table also omitted the version prefix, described 403
as “unauthorized,” and omitted the implemented 413 upload response.

The health endpoints are intentionally root-level (`/health`,
`/health/database`, `/health/ai`) and are now documented as such. Logout is a
stateless acknowledgement; protected resource and workflow routes retain
their existing authentication and role dependencies.

## Contract verification

- Pydantic request validation produces `422 VALIDATION_ERROR` with field
  locations but does not echo submitted values.
- Missing/invalid/expired authentication produces 401 envelopes;
  authenticated insufficient-role requests produce 403 envelopes.
- Missing resources use 404; duplicate/state/approval conflicts use 409.
- Login throttling produces 429; unavailable dependencies produce 503;
  unexpected exceptions produce a generic 500 envelope.
- Every tested error response contains the same request identifier in the
  JSON envelope and `X-Request-ID` response header.
- Internal exception text, provider/database details, credentials, and
  tracebacks are not returned to clients.
- Existing frontend response shapes were preserved, including legacy review
  and audit arrays; the source-page image is the only documented binary
  response.

## Changes

- Corrected API documentation paths and authorization examples to `/api/v1`.
- Documented source-page access, root health routes, 413 uploads, and the
  authenticated-but-forbidden meaning of 403.
- Corrected the frontend contract comment to state that self-registration
  creates a read-only `user` role.
- Added focused route/version/status/envelope/request-ID regression tests.

No Gemini or other AI provider API key was used for this audit or its tests.

## Verification

- Focused API/auth/error/health tests: **35 passed**.
- Python compilation: passed.
- `git diff --check`: passed.

## Remaining

No backend implementation change was required after the contract comparison;
the identified inconsistencies were documentation/comment drift. Existing
broader-suite environment failures remain limited to the known multilingual
OCR tests when Tesseract is not installed.
