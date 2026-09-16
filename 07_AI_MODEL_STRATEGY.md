# 07_AI_MODEL_STRATEGY.md

# Intelligent Land Record Digitization and Validation System

## AI Model and Provider Strategy

**Depends On:** `05_DATASET_AND_ANNOTATION.md`, `06_AI_ARCHITECTURE.md`

---

# 1. Objective

Select AI models/providers based on measured performance on the project's actual land-record dataset.

Do not choose models only because they are popular or large.

---

# 2. AI Components

## OCR

Purpose:

```text
document image
→ text + positions + confidence
```

Candidate approaches:

* open-source OCR
* managed document OCR
* other compatible OCR systems

Initial candidate: evaluate PaddleOCR and alternatives on the actual dataset.

---

## LLM

Purpose:

```text
OCR/context
→ structured land-record fields
```

The LLM must return the schema defined in `04_DATA_DICTIONARY.md`.

---

# 3. Candidate Providers

Initial candidate providers:

```text
Gemini
OpenRouter
NVIDIA
Groq
Mistral
Cohere
```

Only providers that meet the project's actual free/accessible and technical requirements should be enabled.

Availability, rate limits, model availability, and pricing must be rechecked before deployment because provider offerings can change.

---

# 4. Primary Model Selection

Choose the primary model using evaluation criteria:

```text
field extraction accuracy
JSON/schema reliability
Indian-language handling
survey-number accuracy
hallucination/error rate
latency
availability
free-tier practicality
```

The final primary model must be recorded after benchmarking.

---

# 5. Fallback Selection

Choose fallback models based on:

* different failure modes where possible
* adequate structured-output support
* acceptable quality
* acceptable latency
* independent provider availability when useful

Do not add models that have never been tested.

---

# 6. Provider Abstraction

All providers should conform to the same logical interface:

```text
extract_land_record()
```

Input:

```text
OCR result
document context
schema
instructions
```

Output:

```text
structured result
confidence/status metadata
provider/model metadata
error information if failed
```

---

# 7. Key Management

Keys belong on the backend.

Recommended conceptual configuration:

```text
GEMINI_API_KEYS
OPENROUTER_API_KEYS
NVIDIA_API_KEYS
GROQ_API_KEYS
```

Only legitimately authorized credentials may be configured.

The application must not expose keys to the frontend.

---

# 8. Failover Policy

A request should move to another route only for appropriate errors.

Examples:

```text
rate limit
temporary provider failure
timeout
provider unavailable
```

Do not hide:

```text
bad request
invalid schema
application bug
```

by blindly switching providers.

---

# 9. Retries

Use controlled retries.

Recommended principle:

```text
one appropriate retry
→ classify failure
→ fallback if appropriate
```

Avoid retry loops because failed requests may still consume provider quota.

---

# 10. Prompt/Schema Versioning

Track:

```text
prompt_version
schema_version
pipeline_version
model
provider
```

This allows evaluation results to be reproduced.

---

# 11. Model Benchmark Protocol

For each candidate:

```text
same dataset
same target fields
same evaluation procedure
same success definitions
```

Record:

```text
field accuracy
missing fields
incorrect fields
hallucinations
schema failures
average latency
failure rate
```

Select the model with the best practical trade-off.

---

# 12. Final Principle

> **The application owns the workflow; providers supply replaceable AI capabilities.**

# END OF 07_AI_MODEL_STRATEGY.md
