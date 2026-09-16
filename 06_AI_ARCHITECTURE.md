# 06_AI_ARCHITECTURE.md

# Intelligent Land Record Digitization and Validation System

## AI and Document Processing Architecture

**Depends On:** `02_PRD.md`, `04_DATA_DICTIONARY.md`, `05_DATASET_AND_ANNOTATION.md`

---

# 1. Architecture Goal

Convert an uploaded supported document into a validated structured land record while preserving source traceability and human review capability.

---

# 2. Core Pipeline

```text
Document
   ↓
File Validation
   ↓
Preprocessing
   ↓
OCR
   ↓
OCR Text + Coordinates + Confidence
   ↓
Structured Information Extraction
   ↓
Normalization
   ↓
Rule-Based Validation
   ↓
Reference/Duplicate Checks
   ↓
Confidence Calculation
   ↓
Human Review if Required
   ↓
Approved Record
```

---

# 3. Layer Responsibilities

## Layer 1 — Document Intake

Responsibilities:

* validate file
* identify document metadata
* store source
* create processing job

---

## Layer 2 — Preprocessing

Possible operations:

```text
orientation correction
deskew
denoise
contrast improvement
cropping
resolution adjustment
PDF-to-image conversion
```

Preprocessing must be measured rather than applied blindly.

---

## Layer 3 — OCR

OCR converts image content into:

```text
text
bounding boxes
confidence
page information
```

OCR is an external/pretrained capability.

Do not build a new OCR foundation model for MVP.

---

## Layer 4 — Extraction

Input:

```text
OCR text + document context
```

Output:

```text
structured land-record schema
```

The extraction model must follow `04_DATA_DICTIONARY.md`.

Use structured output where supported.

---

## Layer 5 — Normalization

Normalize without changing source meaning.

Examples:

```text
whitespace
date representation
area/unit representation
field formatting
```

---

## Layer 6 — Validation

Validation combines:

```text
field rules
format rules
cross-field checks
reference-data checks
duplicate detection
```

The LLM should not be the sole validation authority.

---

## Layer 7 — Confidence

Confidence should represent extraction reliability and workflow risk.

Potential inputs:

```text
OCR confidence
extraction consistency
validation results
reference-data consistency
```

Final formula is defined during implementation and documented in `08_VALIDATION_SPECIFICATION.md`.

---

## Layer 8 — Human Review

Low-confidence/conflicting records are routed to authorized reviewers.

Review UI must show:

```text
original source
+
extracted value
+
confidence
+
validation reason
```

---

# 4. AI Provider Abstraction

Application code should call a stable internal interface such as:

```text
extract_land_record(input)
```

rather than directly depending on one provider throughout the application.

Conceptual structure:

```text
AIService
├── GeminiAdapter
├── OpenRouterAdapter
├── NVIDIAAdapter
├── GroqAdapter
└── FutureAdapter
```

Providers can be enabled/disabled through configuration.

---

# 5. Fallback Strategy

The fallback system has two levels.

## Provider-level

```text
Provider A
→ Provider B
→ Provider C
```

## Model-level

Within a provider:

```text
Model A
→ Model B
→ Model C
```

OpenRouter's own model/provider routing can be used where appropriate.

Do not design the system around bypassing provider limits. Fallback exists for reliability and availability.

---

# 6. Cache

Cache results when safe.

Recommended cache keys may include:

```text
document checksum
pipeline version
model/version identifier
prompt/schema version
```

If the same source and processing configuration are reused, a previous result may be reused instead of making an unnecessary AI call.

---

# 7. Feedback Loop

```text
AI output
→ human correction
→ correction stored
→ feedback dataset
→ evaluation
→ prompt/rule/model improvement
```

Do not silently treat every human correction as training data.

---

# 8. Failure Isolation

A failure in one component should not corrupt other stages.

Examples:

```text
OCR failure
→ processing state = FAILED

LLM failure
→ retry/fallback

Validation failure
→ REVIEW_REQUIRED

Database failure
→ controlled error + logging
```

---

# 9. Core AI Design Principle

> **Use pretrained AI for perception and language understanding; use deterministic software for rules, state, validation, persistence, and workflow control.**

# END OF 06_AI_ARCHITECTURE.md
