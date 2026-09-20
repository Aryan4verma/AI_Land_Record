# 10_API_SPECIFICATION.md

# Intelligent Land Record Digitization and Validation System

## API Specification

**Depends On:** `02_PRD.md`, `03_USER_FLOW.md`, `09_DATABASE_SCHEMA.md`

---

# 1. API Principles

The API is the contract between frontend and backend.

All API responses should use consistent JSON structures, except explicitly
documented binary source-page responses.

Authentication and authorization are required for protected endpoints.

---

# 2. Authentication

```text
POST /api/v1/auth/login
POST /api/v1/auth/register
POST /api/v1/auth/logout
GET  /api/v1/auth/me
```

Login returns an authenticated session/token according to the selected authentication implementation.

Register (self-registration, 201) accepts `{name, id_number, email, password}` and creates a
read-only `user` account with `active` status; the role is never accepted from the client (any
`role` key in the body is ignored) and no token is returned — the client proceeds to login.
Duplicate email returns `409 USER_EXISTS`.

Operator accounts cannot be self-registered. They are provisioned out-of-band
(see 13_DEPLOYMENT_RUNBOOK "Seeding Users").

## Authorization

Role ladder: `user` < `operator` (< `admin`, internal only).

```text
user      GET  /api/v1/records, /api/v1/records/{id},
               /api/v1/records/{id}/export, /api/v1/dashboard/*,
               /api/v1/documents/{id}, /api/v1/documents/{id}/status,
               /api/v1/documents/{id}/pages/{page},
               /api/v1/documents/{id}/extraction,
               /api/v1/documents/{id}/validation, /api/v1/auth/me
operator  everything above, plus:
               POST /api/v1/documents,
               POST /api/v1/documents/{id}/process,
               all /api/v1/reviews endpoints,
               /api/v1/records/{id}/approve,
               /api/v1/records/{id}/reject,
               /api/v1/records/{id}/audit,
               /api/v1/integrations/mock-lrms
```

Anything an authenticated `user` is not permitted returns `403 INSUFFICIENT_ROLE`.

---

# 3. Documents

## Upload

```text
POST /api/v1/documents
```

Purpose:

Upload a supported PDF/image.

Returns:

```json
{
  "document_id": "...",
  "status": "UPLOADED"
}
```

---

## Get Document

```text
GET /api/v1/documents/{document_id}
```

Returns:

```text
metadata
processing status
document status
```

---

## Start Processing

```text
POST /api/v1/documents/{document_id}/process
```

Starts the AI pipeline.

Returns processing/job status.

---

## Processing Status

```text
GET /api/v1/documents/{document_id}/status
```

## Source Page

```text
GET /api/v1/documents/{document_id}/pages/{page_number}
```

Requires an authenticated account with the normal read-access role and
returns a private JPEG image for the requested source page. The source is
never made public and storage paths/credentials are not part of this contract.

---

# 4. Extraction

```text
GET /api/v1/documents/{document_id}/extraction
```

Returns extracted fields with confidence and source metadata.

---

# 5. Validation

```text
GET /api/v1/documents/{document_id}/validation
```

Returns:

```json
{
  "status": "REVIEW_REQUIRED",
  "issues": []
}
```

---

# 6. Review

## List Review Queue

```text
GET /api/v1/reviews?status=PENDING&assigned_to={user_id}
```

Status and assignment filters are server-side. `priority` is also supported
server-side. Existing calls without pagination parameters return the legacy
array shape. Supplying `priority`, `limit`, or `offset` opts into:

```json
{
  "items": [],
  "limit": 20,
  "offset": 0,
  "total": 0
}
```

`limit` is bounded to 100. This opt-in shape preserves existing frontend
callers while allowing a paginated client to be added later.

## Get Review Task

```text
GET /api/v1/reviews/{review_id}
```

## Submit Correction

```text
PATCH /api/v1/reviews/{review_id}/fields/{field_name}
```

Request:

```json
{
  "value": "78",
  "reason": "Corrected from original document"
}
```

## Complete Review

```text
POST /api/v1/reviews/{review_id}/complete
```

---

# 7. Approval

```text
POST /api/v1/records/{record_id}/approve
POST /api/v1/records/{record_id}/reject
```

Backend must recheck required conditions before approval.

---

# 8. Records

```text
GET /api/v1/records
GET /api/v1/records/{record_id}
```

Supported query parameters may include:

```text
owner
survey_number
khasra_number
village
tehsil
district
status
page
limit
```

---

# 9. Audit

```text
GET /api/v1/records/{record_id}/audit
```

Only authorized roles may access audit history.

Per-record audit history supports the same optional `limit` and `offset`
parameters and returns the paginated shape above when either is supplied;
legacy calls continue to return an ordered array. There is intentionally no
workspace-wide audit feed in the current product: audit history is consumed
as a record-scoped timeline.

---

# 10. Dashboard

```text
GET /api/v1/dashboard/summary
GET /api/v1/dashboard/processing
GET /api/v1/dashboard/validation
```

The liveness and dependency health endpoints are intentionally unversioned:

```text
GET /health
GET /health/database
GET /health/ai
```

---

# 11. Integration / Export

```text
GET /api/v1/records/{record_id}/export
POST /api/v1/integrations/mock-lrms
```

The mock LRMS endpoint exists for hackathon demonstration.

Do not present it as a live government integration.

---

# 12. Standard Error Response

Use a consistent format:

```json
{
  "error": {
    "code": "DOCUMENT_NOT_FOUND",
    "message": "The requested document was not found.",
    "request_id": "..."
  }
}
```

---

# 13. HTTP Status Principles

```text
200 → success
201 → created
202 → accepted for asynchronous processing
400 → bad request
413 → request entity/file too large
401 → unauthenticated
403 → authenticated but forbidden
404 → not found
409 → conflict
422 → validation failure
429 → rate limited where relevant
500 → server error
503 → temporary service unavailable
```

---

# 14. API Security Rules

* authenticate protected endpoints
* authorize by role
* validate request data
* limit file uploads
* do not expose provider credentials
* log security-relevant failures
* use HTTPS in deployment

---

# 15. API Versioning

Use a versioned prefix:

```text
/api/v1/...
```

Future breaking changes should use a new version.

# END OF 10_API_SPECIFICATION.md
