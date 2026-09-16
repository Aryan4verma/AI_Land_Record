# 00_MASTER.md

# Intelligent Land Record Digitization and Validation System

## Master Project Specification

**SIH Problem Statement:** 26018
**Status:** Master Source of Truth

---

# 1. Project Definition

We are building an **AI-assisted legacy land-record digitization and validation platform**.

The system converts supported difficult land documents into structured digital records, validates extracted information, identifies uncertain values, sends uncertain cases to humans, stores approved records with audit history, and provides integration-ready APIs.

We are NOT building a replacement for all government land-record systems.

---

# 2. Core Problem

Legacy records can be:

```text
scanned
handwritten
faded
damaged
inconsistent
multilingual
table-based
stored as PDFs/images
```

Manual digitization is repetitive and can introduce errors.

---

# 3. Core Solution

```text
Document
→ Preprocessing
→ OCR
→ Structured Extraction
→ Normalization
→ Validation
→ Confidence
→ Human Review
→ Approval
→ Database
→ Dashboard/API
```

---

# 4. Core Principle

> **Automate routine work, expose uncertainty, validate independently, and keep humans responsible for final verification.**

---

# 5. MVP

The MVP focuses on:

```text
One primary document type
One controlled language scope
Core land-record fields
PDF/image input
OCR
structured extraction
validation
confidence
human review
approval
database
audit
dashboard
API/export
mock integration
```

---

# 6. Core Documents

```text
01_PROBLEM_RESEARCH.md
02_PRD.md
03_USER_FLOW.md
04_DATA_DICTIONARY.md
05_DATASET_AND_ANNOTATION.md
06_AI_ARCHITECTURE.md
07_AI_MODEL_STRATEGY.md
08_VALIDATION_SPECIFICATION.md
09_DATABASE_SCHEMA.md
10_API_SPECIFICATION.md
11_SECURITY_DESIGN.md
12_EVALUATION_AND_TESTING.md
13_DEPLOYMENT_RUNBOOK.md
14_UI_UX_SPECIFICATION.md
00_MASTER.md
MEMORY.md
```

---

# 7. Technical Architecture

```text
React Frontend
      ↓
FastAPI Backend
      ↓
Document Service
      ↓
OCR
      ↓
AI Extraction
      ↓
Validation
      ↓
Confidence
      ↓
Human Review
      ↓
PostgreSQL
      ↓
Dashboard/API/Integration
```

---

# 8. AI Philosophy

We use pretrained AI.

We do NOT build:

```text
our own GPT
our own foundation model
our own OCR model from scratch
```

We build:

```text
document pipeline
extraction workflow
validation
confidence
human review
audit
database
API
integration
feedback loop
```

---

# 9. AI Providers

Candidate providers:

```text
Gemini
OpenRouter
NVIDIA
Groq
Mistral
Cohere
```

The primary/fallback model selection must be based on testing.

Provider limits and availability are not permanent assumptions.

---

# 10. OCR

OCR is an external/pretrained capability.

Candidate OCR systems are benchmarked against the project's dataset.

OCR output should ideally contain:

```text
text
coordinates
confidence
page
```

---

# 11. Validation

Use:

```text
field rules
format rules
cross-field rules
reference data
duplicate detection
```

AI output alone is not sufficient validation.

---

# 12. Human Review

Low-confidence or conflicting information must be reviewable.

Review screen:

```text
Original document
+
Extracted field
+
Confidence
+
Validation reason
```

---

# 13. Data

Dataset target:

```text
30–50 initial representative documents
```

Every evaluation document needs controlled ground truth.

---

# 14. Security

Critical rules:

```text
API keys server-side
RBAC
authentication
authorization
secure file handling
audit logs
input validation
no secrets in Git
```

---

# 15. Reliability

Use:

```text
provider fallback
model fallback
controlled retry
cache
optional local fallback
clearly labeled demo fallback
```

Do not treat fallback as a mechanism for bypassing provider restrictions.

---

# 16. Project Build Order

```text
Problem Research
→ PRD
→ User Flow
→ Data Dictionary
→ Dataset
→ AI POC
→ OCR benchmark
→ Extraction
→ Validation
→ Database
→ Backend/API
→ Frontend
→ Human Review
→ Integration
→ Evaluation
→ Deployment
→ Final Demo
```

---

# 17. Definition of MVP Done

```text
Document uploaded
→ AI processes it
→ structured fields extracted
→ confidence shown
→ validation runs
→ uncertain fields flagged
→ human can correct
→ approval works
→ record stored
→ audit exists
→ dashboard updates
→ API/export works
```

---

# 18. Out of Scope

Do not prioritize:

```text
all Indian languages
all document types
national deployment
full production LRMS integration
complete government database access
full national GIS
autonomous legal ownership decisions
full legal mutation automation
foundation-model training
OCR-model training from scratch
```

---

# 19. Source of Truth Rules

If documents conflict:

1. Check the latest approved decision in `MEMORY.md`.
2. Check `00_MASTER.md`.
3. Check the relevant detailed document.
4. Do not silently invent a new architecture.
5. Record important changes in `MEMORY.md`.

---

# 20. AI Agent Rule

Any coding AI must:

```text
READ MASTER
→ READ MEMORY
→ READ RELEVANT DETAILED DOCS
→ INSPECT CURRENT CODE
→ PLAN CHANGE
→ IMPLEMENT
→ TEST
→ UPDATE MEMORY
```

It must not rewrite unrelated working components without justification.

# END OF 00_MASTER.md
