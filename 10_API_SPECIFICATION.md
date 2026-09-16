# 10_API_SPECIFICATION.md

# Intelligent Land Record Digitization and Validation System

## API Specification

**Depends On:** `02_PRD.md`, `03_USER_FLOW.md`, `09_DATABASE_SCHEMA.md`

---

# 1. API Principles

The API is the contract between frontend and backend.

All API responses should use consistent JSON structures.

Authentication and authorization are required for protected endpoints.

---

# 2. Authentication

```text
POST /api/auth/login
POST /api/auth/register
POST /api/auth/logout
GET  /api/auth/me
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
user      GET  /records, /records/{id}, /records/{id}/export,
               /dashboard/*, /documents/{id}, /documents/{id}/status,
               /documents/{id}/extraction, /documents/{id}/validation,
               /auth/me
operator  everything above, plus:
               POST /documents, POST /documents/{id}/process,
               all /reviews endpoints, /records/{id}/approve,
               /records/{id}/reject, /records/{id}/audit,
               /integrations/mock-lrms
```

Anything an authenticated `user` is not permitted returns `403 INSUFFICIENT_ROLE`.

---

# 3. Documents

## Upload

```text
POST /api/documents
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
GET /api/documents/{document_id}
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
POST /api/documents/{document_id}/process
```

Starts the AI pipeline.

Returns processing/job status.

---

## Processing Status

```text
GET /api/documents/{document_id}/status
```

---

# 4. Extraction

```text
GET /api/documents/{document_id}/extraction
```

Returns extracted fields with confidence and source metadata.

---

# 5. Validation

```text
GET /api/documents/{document_id}/validation
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

## Get Review Task

```text
GET /api/reviews/{review_id}
```

## Submit Correction

```text
PATCH /api/reviews/{review_id}/fields/{field_name}
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
POST /api/reviews/{review_id}/complete
```

---

# 7. Approval

```text
POST /api/records/{record_id}/approve
POST /api/records/{record_id}/reject
```

Backend must recheck required conditions before approval.

---

# 8. Records

```text
GET /api/records
GET /api/records/{record_id}
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
GET /api/records/{record_id}/audit
```

Only authorized roles may access audit history.

---

# 10. Dashboard

```text
GET /api/dashboard/summary
GET /api/dashboard/processing
GET /api/dashboard/validation
```

---

# 11. Integration / Export

```text
GET /api/records/{record_id}/export
POST /api/integrations/mock-lrms
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
401 → unauthenticated
403 → unauthorized
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
