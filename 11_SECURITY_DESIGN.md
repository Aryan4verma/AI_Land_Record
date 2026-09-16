# 11_SECURITY_DESIGN.md

# Intelligent Land Record Digitization and Validation System

## Security Design

**Depends On:** `02_PRD.md`, `09_DATABASE_SCHEMA.md`, `10_API_SPECIFICATION.md`

---

# 1. Security Objective

Protect:

* land-record information
* uploaded documents
* user identities
* API credentials
* audit information
* database access

The MVP should follow a secure-by-default design.

---

# 2. Authentication

All protected features require authentication.

The system must not trust user identity supplied only by the frontend.

The backend must verify the authenticated session/token.

---

# 3. Authorization

Use role-based access control. Two user-facing roles (revised 2026-09-07):

```text
User        read-only
Operator    full document + review/approval workflow
[Admin]     internal only, never user-facing
```

Permissions are enforced on the backend.

```text
User     → search/view records, extraction, validation, permitted export
Operator → upload/process + review/correct/complete + approve/reject + audit
Admin    → reserved internal escalation rank (no endpoint requires it)
```

Rules:

* Role values are normalized to lowercase before any comparison.
* Self-registration can only ever create `user` (least privilege); a `role`
  key supplied by the client is ignored, never honoured.
* Operator accounts are provisioned out-of-band only.
* The retired `verifier` value is not in the hierarchy: a token or stored row
  carrying it fails closed (401) rather than being reinterpreted.

KNOWN LIMITATION: authorization reads the role from the verified JWT and does
not re-check the database on every request (only `/auth/me` refetches). A
demotion or deactivation therefore takes effect at token expiry
(`AUTH_TOKEN_EXPIRE_MINUTES`, default 480) rather than immediately. Rotate
`AUTH_SECRET` to invalidate all outstanding tokens at once.

---

# 4. API-Key Security

Never place AI provider credentials in:

```text
React source
browser storage
public configuration
Git repository
logs
```

Store them in secure backend environment/secret management.

---

# 5. File Upload Security

Validate:

* file extension
* MIME type
* size
* filename
* content where practical

Use generated internal storage names rather than trusting user filenames.

Do not directly execute uploaded files.

---

# 6. Database Security

Use:

* least-privilege database accounts
* parameterized queries/ORM
* access controls
* encrypted transport
* backups
* proper indexes and constraints

Do not expose database credentials to frontend code.

---

# 7. Audit Security

Audit logs should be:

* timestamped
* associated with a user
* associated with a record/entity
* protected from ordinary users editing history

---

# 8. Sensitive Data Handling

Use only data that the team is authorized to process.

For external AI providers:

```text
send only necessary information
avoid unnecessary sensitive data
```

For development:

```text
prefer synthetic/redacted/anonymized examples when possible
```

---

# 9. Prompt Injection / Document Content

Uploaded documents may contain arbitrary text.

Treat document text as **untrusted input**.

The extraction system must distinguish:

```text
system instructions
vs
document content
```

Do not allow document text to override system instructions.

---

# 10. Validation Security

Do not trust AI-generated fields merely because the model returned valid JSON.

Backend validation must run independently.

---

# 11. Secrets Management

Required secrets may include:

```text
database credentials
authentication secrets
Gemini keys
OpenRouter keys
NVIDIA keys
Groq keys
storage credentials
```

Never commit actual values.

Provide `.env.example` with placeholders.

---

# 12. Logging

Log:

```text
request ID
user/action
processing status
errors
provider failures
security events
```

Do not log raw secrets.

Avoid unnecessary sensitive document content in logs.

---

# 13. Dependency Security

Keep dependencies updated.

Before final deployment:

```text
install dependencies
→ run vulnerability checks where available
→ remove unused packages
→ lock versions
```

---

# 14. Security Principle

> **Never trust the browser, never trust raw document content, never trust AI output without validation, and never expose secrets.**

# END OF 11_SECURITY_DESIGN.md
