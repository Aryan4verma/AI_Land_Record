# 02_PRD.md

# Intelligent Land Record Digitization and Validation System

## Product Requirements Document

**SIH Problem Statement:** 26018
**Status:** MVP Planning Baseline
**Depends On:** `01_PROBLEM_RESEARCH.md`

---

# 1. Product Objective

Build an AI-assisted platform that converts supported legacy land-record documents into structured digital records, validates extracted information, identifies uncertain data, enables human verification, stores approved records, and provides an integration-ready interface.

The MVP must demonstrate the complete workflow rather than attempting nationwide or production-level coverage.

---

# 2. Primary User

**Land-record/revenue-office operator or verification officer**

The user must be able to:

```text
Login
→ Upload document
→ Process document
→ Review extracted data
→ See confidence and validation warnings
→ Correct uncertain fields
→ Approve record
→ Search stored record
→ View audit history
```

---

# 3. Product Goals

## G1 — Reduce manual data entry

Automatically extract predefined fields from supported documents.

## G2 — Improve data reliability

Use validation rules, reference checks, confidence signals, and human review.

## G3 — Preserve traceability

Record corrections, approvals, users, and timestamps.

## G4 — Provide interoperability

Expose approved records through APIs/export and maintain an integration-ready schema.

## G5 — Demonstrate practical AI use

Use existing OCR and pretrained LLMs instead of training foundation models from scratch.

---

# 4. MVP Inputs

The MVP accepts:

* PDF documents
* image documents
* one selected primary land-record document type
* one controlled language/script scope initially
* selected printed and challenging/handwritten examples

The exact document type and language are finalized after dataset and OCR benchmarking.

---

# 5. MVP Outputs

For each processed document:

```text
Document status
Extracted fields
Field confidence
Validation results
Review status
Final approved record
Audit history
```

---

# 6. Core Functional Requirements

## FR-01 Authentication

Users must authenticate before accessing protected functionality.

## FR-02 Document Upload

Authorized users can upload supported PDF/image files.

The system must validate:

* file type
* file size
* processing status

## FR-03 Document Processing

The system must process an uploaded document through:

```text
Preprocessing
→ OCR
→ Structured extraction
→ Normalization
→ Validation
→ Confidence calculation
```

## FR-04 Structured Extraction

The system must extract the fields defined in `04_DATA_DICTIONARY.md`.

Missing or unclear information must not be invented.

## FR-05 Confidence

Each relevant extracted field should receive a confidence/status signal.

## FR-06 Validation

The system must execute rules defined in `08_VALIDATION_SPECIFICATION.md`.

## FR-07 Human Verification

Low-confidence or conflicting fields must be reviewable by an authorized user.

## FR-08 Approval

An authorized verifier can approve or reject the final record.

## FR-09 Audit Trail

Important actions and field changes must be recorded.

## FR-10 Repository

Approved and reviewable records must be searchable.

## FR-11 Dashboard

The dashboard should show:

* total documents
* processed documents
* pending reviews
* approved records
* rejected records
* validation issues
* average confidence
* processing statistics

## FR-12 API

The backend must expose documented endpoints for document processing and record management.

## FR-13 Integration

The system must provide API/export capability suitable for a mock LRMS/integration demonstration.

## FR-14 Role-Based Access

Different roles must have appropriate permissions.

---

# 7. MVP Roles

Two user-facing roles (revised 2026-09-07). The former `verifier` role is
retired and its capabilities belong to `operator`.

### Operator

Can:

* upload
* process
* view results
* create review tasks
* review, correct, complete review
* approve/reject
* view record audit history
* search/view/export records

### User

Read-only. Can:

* search/view records
* view extraction and validation/status
* export where policy allows

Must NOT: upload, process, correct, review, complete review, approve,
reject, or read privileged audit history. Every one of these returns
`403 INSUFFICIENT_ROLE` from the backend.

### Admin (internal only)

Retained as an internal escalation rank above operator. It is never offered
as a user-facing role, never creatable through self-registration, and no
endpoint currently requires it.

---

# 8. Non-Functional Requirements

## Reliability

A provider/model failure must not crash the complete application.

## Security

Secrets must remain server-side.

## Traceability

Important AI and human actions must be auditable.

## Maintainability

AI providers and models should be replaceable through an abstraction layer.

## Performance

Processing time must be measured and reported rather than assumed.

## Usability

An operator must understand:

* what the AI extracted
* what is uncertain
* why verification is required
* what action to take

---

# 9. Explicit Non-MVP

The MVP will not attempt:

* every Indian language
* every land-record type
* nationwide deployment
* autonomous legal ownership decisions
* autonomous legal mutation approval
* direct access to confidential government databases
* complete production LRMS integration
* full national GIS platform
* new foundation-model training
* OCR model training from scratch

---

# 10. MVP Acceptance Criteria

The MVP is considered functional when:

```text
A supported document can be uploaded
→ processed
→ converted into structured fields
→ validated
→ assigned confidence/status
→ flagged for human review where necessary
→ corrected/approved by a human
→ stored in the database
→ retrieved later
→ shown with audit information
```

---

# 11. Success Metrics

The final targets will be established after benchmarking.

Measure:

* OCR accuracy
* field extraction accuracy
* validation accuracy
* review rate
* average confidence
* processing time
* failure rate
* duplicate detection performance

Do not claim untested accuracy.

---

# 12. Product Principle

> **Automate routine extraction, explicitly expose uncertainty, and keep humans responsible for final verification.**

# END OF 02_PRD.md
