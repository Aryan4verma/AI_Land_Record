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

The backend re-reads the active user and canonical role from the database on
every authenticated request. Demotion, suspension, or deletion therefore
takes effect immediately rather than waiting for token expiry. Logout remains
stateless: the client discards its bearer token; rotate `AUTH_SECRET` or
deactivate the account when outstanding tokens must be invalidated globally.

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

Store them in secure backend environment/secret management. OpenCode MCP
credentials use `{env:STITCH_API_KEY}` and are never stored in `opencode.json`
or any tracked file.

---

# 5. File Upload Security

Validate:

* file extension
* MIME type
* size
* filename
* magic bytes/content where practical

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

The backend CORS policy uses explicit configured origins and only the methods
and headers used by the current browser client. Wildcard origins, methods, and
headers are not permitted.

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

Database/provider diagnostics log operation, type, and status facts only;
driver messages, provider response bodies, passwords, tokens, URLs with
credentials, and document-derived values are not logged. Run the repository
secret scan with:

```text
python scripts/scan_secrets.py
```

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
