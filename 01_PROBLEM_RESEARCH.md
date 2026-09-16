# 01_PROBLEM_RESEARCH.md

# Intelligent Land Record Digitization and Validation System

## 1. Project Identity

* **SIH Problem Statement ID:** 26018
* **Title:** Intelligent Land Record Digitization and Validation System
* **Organization:** Ministry of Rural Development
* **Department:** Department of Land Resources (DoLR)
* **Category:** Software
* **Theme:** Smart Automation

---

# 2. Problem in Simple Terms

Historical land records can exist as scanned PDFs, images, handwritten registers, old documents, maps, cadastral records, and other difficult formats.

These documents may contain:

* poor-quality scans
* faded text
* damaged pages
* handwriting
* inconsistent layouts
* tables and annotations
* multiple Indian languages/scripts

Converting these records into accurate digital data can require significant manual effort and can introduce errors.

The actual problem is therefore:

> **How can we automatically convert difficult legacy land documents into structured digital land records while detecting uncertainty and errors and allowing humans to verify important information?**

---

# 3. What We Are Actually Building

We are NOT simply building an OCR application.

We are building:

> **An AI-assisted pipeline that converts difficult legacy land documents into structured, validated, confidence-scored, human-approved digital records.**

Core flow:

```text
Document
→ Preprocessing
→ OCR
→ Information Extraction
→ Normalization
→ Validation
→ Confidence Scoring
→ Human Verification
→ Approval
→ Database
→ Dashboard / API / Integration
```

---

# 4. Current Manual Problem

Simplified existing workflow:

```text
Legacy Document
→ Human reads document
→ Human identifies fields
→ Human types data
→ Human checks document
→ Human corrects errors
→ Data stored digitally
```

Problems:

* slow processing
* repetitive manual work
* transcription errors
* inconsistent data entry
* missing information
* difficult validation
* difficulty handling poor scans and handwriting
* difficulty handling multiple languages

Our system should automate the repetitive parts while keeping human verification for uncertain information.

---

# 5. Core User

### Primary user

Land-record/revenue-office operator or verification officer.

The user should be able to:

```text
Login
→ Upload document
→ Start processing
→ View extracted fields
→ View confidence
→ View validation warnings
→ Compare with original document
→ Correct uncertain fields
→ Approve record
→ View stored record
→ View audit history
```

---

# 6. Expected Inputs

The official problem statement refers to:

* scanned PDFs
* images
* handwritten documents
* historical documents
* legacy PDFs
* land records
* cadastral/maps-related information

### MVP rule

Do NOT support every document type initially.

Start with:

```text
ONE primary document type
+
ONE controlled language/script scope
+
PDF/image input
+
selected printed/handwritten cases
```

Expand later only after the core pipeline works reliably.

---

# 7. Core Land-Record Fields

Possible fields include:

```text
owner_name
father_or_spouse_name
survey_number
khasra_number
khata_number
area
area_unit
village
tehsil
district
land_classification
mutation_number
registration_number
record_date
```

The final MVP field list will be finalized in:

`04_DATA_DICTIONARY.md`

Do not add unnecessary fields before the MVP schema is finalized.

---

# 8. Core AI/System Pipeline

```text
                    DOCUMENT
                        ↓
                 Upload & Storage
                        ↓
                 Image Preprocessing
                        ↓
                       OCR
                        ↓
       Text + Bounding Boxes + OCR Confidence
                        ↓
              Structured Extraction
                        ↓
                  Normalization
                        ↓
               Validation Engine
                        ↓
               Confidence Engine
                        ↓
            ┌───────────┴───────────┐
            ↓                       ↓
      High Confidence          Low Confidence
            ↓                       ↓
      Auto Processing          Human Review
            │                       │
            └───────────┬───────────┘
                        ↓
                   Final Record
                        ↓
                     Database
                        ↓
               Dashboard / API
```

---

# 9. OCR Role

OCR converts document images into machine-readable text.

OCR may provide:

* recognized text
* text positions/bounding boxes
* recognition confidence

OCR is only one stage.

```text
OCR
≠
Complete land-record understanding
```

We will use an existing OCR engine/model rather than build an OCR model from scratch.

Candidate OCR technologies should be benchmarked against our actual dataset.

---

# 10. LLM/AI Role

A pretrained LLM can transform OCR output into structured land-record information.

Example:

### OCR text

```text
Owner: Ravi Patel
Survey No.: 145/2
Area: 2.45 hectare
Village: ABC
```

### Structured result

```json
{
  "owner_name": "Ravi Patel",
  "survey_number": "145/2",
  "area": 2.45,
  "area_unit": "hectare",
  "village": "ABC"
}
```

The LLM should:

* extract information
* classify information into predefined fields
* normalize information when appropriate
* return structured output
* avoid inventing missing information
* return null/uncertain values when information cannot be reliably determined

We will use pretrained AI models/API services instead of training a foundation model from scratch.

---

# 11. Validation

Validation must NOT depend only on the LLM.

Use multiple layers:

```text
Field Validation
+
Format Validation
+
Cross-Field Validation
+
Reference-Data Validation
+
Duplicate Detection
```

Examples:

```text
Required field missing
→ REVIEW

Area <= 0
→ INVALID

Invalid survey-number format
→ WARNING/INVALID

Village does not match reference data
→ WARNING

Possible duplicate record
→ REVIEW
```

The exact rules will be defined in:

`08_VALIDATION_SPECIFICATION.md`

---

# 12. Confidence Scoring

Each important extracted field should have a confidence signal.

Example:

```text
Owner Name
Ravi Patel
98%

Survey Number
145/2
95%

Khasra Number
78
61%
REVIEW REQUIRED
```

Confidence is a **workflow signal**, not proof of legal correctness.

Purpose:

```text
High confidence
→ less manual intervention

Low confidence
→ human verification
```

The confidence calculation will be finalized in the AI and validation design documents.

---

# 13. Human-in-the-Loop

The system must not assume that AI is always correct.

Workflow:

```text
AI extracts information
→ system calculates confidence
→ reliable fields can continue automatically
→ uncertain fields are flagged
→ human reviews/corrects them
→ human approves final record
```

Review UI should show:

```text
Original Document
        +
Extracted Structured Data
        +
Confidence
        +
Validation Warnings
```

Possible actions:

```text
Accept
Edit
Reject
Approve
```

---

# 14. Audit Trail

Every important change should be traceable.

Example:

```text
User: Officer 104
Field: Khasra Number
Old Value: 78
New Value: 73
Reason: OCR correction
Time: 14:35
Action: Approved
```

The system should preserve:

* who performed the action
* what changed
* previous value
* new value
* timestamp
* approval status

---

# 15. Learning/Feedback Mechanism

The official problem asks for an AI-driven mechanism that improves over time.

For the MVP, implement the foundation of this mechanism:

```text
AI Prediction
→ Human Correction
→ Store Correction
→ Add to Feedback Dataset
→ Use for future evaluation/improvement
```

Possible future uses:

* prompt improvement
* retrieval examples
* rule improvement
* model evaluation
* fine-tuning
* model training

Do NOT attempt to train a large foundation model during the MVP.

---

# 16. Existing Ecosystem Positioning

This project should NOT claim that India has no digital land-record systems.

The government already has land-record modernization initiatives and digital systems.

The project opportunity is:

> **Provide an intelligent ingestion, extraction, validation, and human-verification layer for difficult legacy source documents that can work alongside existing digital land-record ecosystems.**

Therefore, we should design for interoperability with:

* LRMS
* DILRMP ecosystem
* GIS platforms
* cadastral information systems
* other authorized government databases

For the hackathon, use mock/integration-ready systems when real government production access is unavailable.

---

# 17. GIS/Map Position

GIS and cadastral maps are relevant to the broader land-record ecosystem.

However:

> **GIS is not the primary MVP innovation.**

The first priority is:

```text
Legacy Document
→ Structured Land Record
→ Validation
→ Human Verification
→ Approved Record
```

GIS/map linkage can be added as a secondary feature.

---

# 18. MVP Scope

## Include

```text
1. Login
2. Document upload
3. PDF/image processing
4. Image preprocessing
5. OCR
6. Structured field extraction
7. Core land-record fields
8. Confidence scoring
9. Rule-based validation
10. Reference/duplicate checks using controlled data
11. Human verification
12. Approval
13. Database storage
14. Audit trail
15. Dashboard
16. API/export
17. Mock LRMS integration
```

---

# 19. Explicitly Outside MVP

Do NOT make these first-priority features:

```text
All Indian languages
All document types
Nationwide deployment
Complete production LRMS integration
Direct production government database access
Full national GIS platform
Autonomous legal ownership decisions
Automatic legal mutation approval
Advanced fraud investigation
Training a new foundation LLM
Training OCR from scratch
```

These can be future scope.

---

# 20. AI Technology Philosophy

### We are NOT building:

```text
Our own GPT
Our own foundation model
Our own OCR neural network
```

### We ARE building:

```text
Document-processing pipeline
OCR integration
Land-record schema
Structured extraction
Validation engine
Confidence engine
Human-review workflow
Audit system
Database
APIs
Dashboard
Integration layer
Feedback mechanism
```

The project's value is in the **complete domain-specific system**, not in recreating a foundation model.

---

# 21. Candidate AI Provider Strategy

Candidate LLM providers may include:

```text
Gemini
OpenRouter
NVIDIA NIM
Groq
Mistral
Cohere
```

Do not assume that one model is automatically the best.

Benchmark candidate models against our dataset using:

```text
Field accuracy
JSON reliability
Indian-language handling
Survey-number accuracy
Hallucination rate
Processing speed
```

Then select:

```text
Primary Model
+
Fallback Model 1
+
Fallback Model 2
+
Emergency Fallback
```

The final choices belong in:

`07_AI_MODEL_STRATEGY.md`

---

# 22. Provider Independence

The application should not depend directly on one AI provider.

The backend should conceptually expose:

```text
extract_land_record()
```

rather than hard-coding one model throughout the application.

Architecture:

```text
AI Service
    ├── Gemini
    ├── OpenRouter
    ├── NVIDIA
    ├── Groq
    └── Future Provider
```

This allows models/providers to be replaced without redesigning the whole system.

---

# 23. API-Key Security

AI credentials must remain on the backend.

Never put provider API keys directly in frontend code.

Use:

```text
Environment Variables
+
Server-side configuration
+
Secure secret handling
```

Example:

```text
GEMINI_API_KEY
OPENROUTER_API_KEY
NVIDIA_API_KEY
GROQ_API_KEY
```

Never commit real secrets to GitHub.

---

# 24. Reliability Strategy

Free AI APIs may have:

* rate limits
* request limits
* temporary outages
* model availability changes
* provider failures

Therefore the AI service should eventually support:

```text
Primary Provider
→ Model Fallback
→ Provider Fallback
→ Cache
→ Optional Local Fallback
→ Clearly Labeled Demo Mode
```

Do not rely on unlimited free API usage.

---

# 25. Dataset Requirement

Before serious AI development, create a controlled dataset.

Initial target:

```text
30–50 representative documents
```

Include different difficulty levels:

```text
Clean
Medium quality
Poor quality
Handwritten/challenging
```

Each document needs ground truth.

Ground truth means:

> The correct structured values against which AI output can be measured.

Example:

```json
{
  "owner_name": "Correct Name",
  "survey_number": "145/2",
  "khasra_number": "78",
  "area": 2.45,
  "village": "ABC"
}
```

Dataset details will be finalized in:

`05_DATASET_AND_ANNOTATION.md`

---

# 26. Evaluation Requirement

The system must eventually be measured rather than judged only visually.

Measure:

```text
OCR accuracy
Field extraction accuracy
Precision
Recall
F1 where appropriate
Validation accuracy
False positives
False negatives
Processing time
Human-review rate
Failure rate
```

Do not claim an accuracy percentage without testing it on a defined dataset.

Evaluation details belong in:

`12_EVALUATION_AND_TESTING.md`

---

# 27. Key Technical Challenges

### Challenge 1 — Poor scans

Response:

```text
Preprocessing
+
OCR benchmarking
```

### Challenge 2 — Handwriting

Response:

```text
Supported sample scope
+
Confidence
+
Human verification
```

### Challenge 3 — Multiple languages

Response:

```text
Controlled MVP language scope
→ expand later
```

### Challenge 4 — Incorrect AI output

Response:

```text
Validation
+
Confidence
+
Human review
```

### Challenge 5 — Missing reference data

Response:

```text
Controlled reference dataset
+
Mock integration
```

### Challenge 6 — Sensitive information

Response:

```text
Authentication
+
Authorization
+
Secure storage
+
Audit logging
```

---

# 28. Main Product Thesis

The central product thesis is:

> **If difficult legacy land documents can be converted into structured information through AI-assisted extraction and then checked through validation, confidence scoring, and human verification, repetitive digitization work can be reduced while maintaining reviewability and traceability.**

This is a hypothesis to be demonstrated through the prototype.

---

# 29. Main Product Positioning

Use this as the project's central description:

> **We are building an AI-assisted legacy land-record digitization and validation platform that extracts structured information from difficult documents, identifies uncertainty and inconsistencies, routes low-confidence information to human reviewers, stores approved records with audit history, and provides integration-ready APIs for existing digital land-record ecosystems.**

Do NOT position the project as:

> "An AI that automatically determines legal ownership."

---

# 30. North-Star Workflow

The entire project should ultimately demonstrate:

```text
UPLOAD
  ↓
READ
  ↓
UNDERSTAND
  ↓
STRUCTURE
  ↓
VALIDATE
  ↓
CONFIDENCE
  ↓
REVIEW
  ↓
APPROVE
  ↓
STORE
  ↓
INTEGRATE
```

---

# 31. Research Decisions to Confirm Before Implementation

Before finalizing the PRD and architecture, confirm:

```text
1. Exact MVP document type
2. Exact MVP language/script
3. Final core fields
4. Dataset source
5. Ground-truth method
6. OCR candidates
7. LLM candidates
8. Validation reference data
9. MVP boundaries
10. Primary user workflow
```

Do not make these decisions based only on assumptions.

---

# 32. Development Principle

The project must be built in this order:

```text
Problem Understanding
→ MVP Definition
→ Dataset
→ AI/OCR POC
→ Structured Extraction
→ Validation
→ Human Review
→ Database
→ Backend/API
→ Frontend
→ Integration
→ Evaluation
→ Deployment
→ Final Demo
```

Do not start by building a large UI before proving the core document-to-structured-data pipeline.

---

# 33. Final Understanding

The project is fundamentally:

```text
MESSY LEGACY DOCUMENT
          ↓
       AI READS
          ↓
 AI UNDERSTANDS FIELDS
          ↓
 STRUCTURED RECORD
          ↓
    VALIDATION
          ↓
   CONFIDENCE
          ↓
 HUMAN VERIFICATION
          ↓
    APPROVED DATA
          ↓
 DATABASE / API / GIS
```

The core innovation is not OCR alone.

The core value is:

> **Turning difficult legacy land documents into trustworthy, structured, validated, human-approved digital records.**

---

# 34. Source

Primary source:

**SIH Problem Statement 26018 — Intelligent Land Record Digitization and Validation System**

Official problem statement requirements must remain the primary reference for project scope.

Where this document makes project-specific decisions, those decisions are treated as implementation strategy rather than claims that they are explicitly required by the official statement.

---

# 35. Handoff to Next Documents

This document is the foundation for:

```text
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

Later documents must remain consistent with this document unless a new decision is explicitly recorded and justified in `MEMORY.md`.

# END OF 01_PROBLEM_RESEARCH.md
