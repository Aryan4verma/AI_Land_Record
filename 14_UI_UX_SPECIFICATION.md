# 14_UI_UX_SPECIFICATION.md

# Intelligent Land Record Digitization and Validation System

## UI/UX Specification

**Depends On:** `02_PRD.md`, `03_USER_FLOW.md`, `04_DATA_DICTIONARY.md`

---

# 1. UI Objective

The interface must make the AI workflow understandable to a non-technical land-record operator.

The user should always understand:

```text
What is happening?
What did the AI find?
How confident is it?
What is wrong?
What do I need to review?
```

---

# 2. Main Screens

```text
Login
Dashboard
Upload
Processing
Extraction/Review
Records
Record Details
Audit History
Administration
```

---

# 3. Login Screen

Elements:

```text
Email/username
Password
Login
Error message
```

Keep the screen simple.

---

# 4. Dashboard

Show:

```text
Documents Processed
Pending Review
Approved
Rejected
Validation Issues
Average Confidence
```

Primary actions:

```text
Upload Document
Review Pending
Search Records
```

---

# 5. Upload Screen

Elements:

```text
Drag/drop area
Browse button
Supported file information
Document type
Language if required
Upload button
```

Show:

```text
upload progress
processing status
errors
```

---

# 6. Processing Screen

Show stages:

```text
Document received      ✓
Preprocessing          ✓
OCR                    ✓
Extraction              ✓
Validation              ✓
Confidence calculation  ✓
```

For active stage:

```text
Processing...
```

For failure:

```text
Processing failed
Reason
Retry
```

---

# 7. Main Review Screen

Recommended two-panel design:

```text
┌────────────────────┬─────────────────────┐
│ Original Document  │ Extracted Record    │
│                    │                     │
│ page/image         │ Field values        │
│                    │ confidence          │
│                    │ validation status   │
└────────────────────┴─────────────────────┘
```

---

# 8. Field Display

Example:

```text
Owner Name
Ravi Patel
Confidence: 98%
Status: Verified

Survey Number
145/2
Confidence: 62%
Status: Review Required
```

Uncertain fields should be visually obvious without relying only on color.

Use:

```text
icon
label
text
```

in addition to color.

---

# 9. Validation Panel

Show:

```text
Validation issue
Field
Severity
Reason
Recommended review action
```

Example:

```text
WARNING
Khasra Number

The extracted value has low confidence.
Check the original document before approval.
```

---

# 10. Correction Interaction

When editing:

```text
Original value
New value
Reason
Save correction
```

The system must record the correction in the audit system.

---

# 11. Approval

The approval button should not be enabled when mandatory blocking issues remain.

Before approval, show:

```text
Required fields complete
Validation issues resolved
Review complete
```

---

# 12. Records Screen

Use:

```text
search
filters
table
status
pagination
```

Possible columns:

```text
Record ID
Owner
Survey No.
Village
District
Status
Updated
```

---

# 13. Record Details

Show:

```text
original source
structured fields
confidence
validation
review history
audit
```

---

# 14. Design Principles

## Principle 1

Do not hide uncertainty.

## Principle 2

Always connect extracted data back to the source where possible.

## Principle 3

Use plain labels such as:

```text
Needs Review
Validated
Approved
Rejected
```

## Principle 4

Avoid presenting AI output as legally authoritative.

## Principle 5

Keep the primary task visible.

---

# 15. Responsive Behavior

The main operator workflow should work on:

```text
desktop
laptop
large tablet
```

Desktop is the primary target for the MVP.

# END OF 14_UI_UX_SPECIFICATION.md
