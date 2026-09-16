# 03_USER_FLOW.md

# Intelligent Land Record Digitization and Validation System

## User Flow Specification

**Depends On:** `01_PROBLEM_RESEARCH.md`, `02_PRD.md`

---

# 1. Primary End-to-End Flow

```text
LOGIN
  ↓
DASHBOARD
  ↓
UPLOAD DOCUMENT
  ↓
DOCUMENT VALIDATION
  ↓
PROCESSING
  ↓
OCR
  ↓
STRUCTURED EXTRACTION
  ↓
NORMALIZATION
  ↓
VALIDATION
  ↓
CONFIDENCE
  ↓
REVIEW REQUIRED?
  ├── NO → APPROVAL/FINALIZATION
  └── YES → HUMAN REVIEW
                    ↓
                 CORRECTION
                    ↓
                 REVALIDATION
                    ↓
                 APPROVAL
  ↓
STORE FINAL RECORD
  ↓
AUDIT TRAIL
  ↓
SEARCH / DASHBOARD / API
```

---

# 2. Login Flow

```text
User opens application
→ enters credentials
→ authentication succeeds
→ role is identified
→ dashboard opens
```

Failure:

```text
invalid credentials
→ show error
→ do not authenticate
```

---

# 3. Dashboard Flow

Dashboard shows:

* total documents
* processing status
* pending verification
* approved records
* rejected records
* validation statistics
* confidence statistics

Primary actions:

```text
Upload Document
Review Pending
Search Records
View Audit
```

---

# 4. Upload Flow

```text
User selects Upload
→ selects PDF/image
→ frontend validates basic file properties
→ backend receives file
→ file is stored
→ document record is created
→ processing begins
```

Reject when:

* unsupported file
* invalid request
* file too large
* security validation fails

---

# 5. Processing Flow

Document status moves through states:

```text
UPLOADED
→ PREPROCESSING
→ OCR_PROCESSING
→ EXTRACTION
→ VALIDATION
→ REVIEW_REQUIRED / READY_FOR_APPROVAL
→ APPROVED / REJECTED
```

Every state change should be traceable.

---

# 6. Extraction Review Flow

The review page should show:

```text
Original document
        +
Extracted fields
        +
Confidence
        +
Validation warnings
```

Example:

```text
Owner Name       Ravi Patel      98%    OK
Survey Number    145/2           95%    OK
Khasra Number    78              61%    REVIEW
Area             2.45            97%    OK
Village          ABC             99%    OK
```

---

# 7. Human Review Flow

```text
Reviewer opens pending record
→ examines original document
→ examines extracted field
→ corrects value if needed
→ submits correction
→ validation runs again
→ reviewer approves/rejects
```

Correction must create an audit entry.

---

# 8. Approval Flow

Before approval:

```text
Required fields complete?
Validation issues resolved?
Required review completed?
```

If yes:

```text
APPROVE
→ final record created
→ record becomes searchable
→ audit event stored
```

If unresolved:

```text
Approval blocked
→ user sees unresolved issue
```

---

# 9. Rejection Flow

A verifier may reject a record when:

* document is unusable
* extracted information cannot be verified
* serious conflict remains
* incorrect document type
* required information is absent

Rejected records must retain their history.

---

# 10. Search Flow

User can search by supported fields such as:

```text
Owner
Survey Number
Khasra Number
Khata Number
Village
Tehsil
District
Status
```

Search result:

```text
Record ID
Owner
Survey/Khasra
Village
Status
Confidence
Last Updated
```

---

# 11. Audit Flow

Authorized users can inspect:

```text
Created
Uploaded
Processed
Extracted
Edited
Validated
Reviewed
Approved
Rejected
```

Each relevant event should contain:

```text
user
action
timestamp
record/document
old value
new value
```

---

# 12. API/Integration Flow

After approval:

```text
Approved Record
      ↓
API / Export
      ↓
Mock LRMS / External Consumer
```

Only approved/authorized data should be exposed according to permissions.

---

# 13. Error Flow

## OCR Failure

```text
OCR failed
→ mark processing error
→ show understandable message
→ allow retry
```

## LLM Failure

```text
AI provider failure
→ fallback according to AI strategy
→ if all live providers fail:
   use configured cache/local/demo strategy
```

## Validation Failure

```text
Validation issue
→ do not silently approve
→ flag issue
→ route to review
```

## Database Failure

```text
database error
→ preserve processing state where possible
→ log error
→ show retryable failure
```

---

# 14. State Model

Recommended document states:

```text
UPLOADED
PROCESSING
EXTRACTED
VALIDATION_FAILED
REVIEW_REQUIRED
READY_FOR_APPROVAL
APPROVED
REJECTED
FAILED
```

State transitions must be controlled by backend rules.

# END OF 03_USER_FLOW.md
