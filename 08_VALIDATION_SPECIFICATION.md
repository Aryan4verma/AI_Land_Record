# 08_VALIDATION_SPECIFICATION.md

# Intelligent Land Record Digitization and Validation System

## Validation Specification

**Depends On:** `04_DATA_DICTIONARY.md`, `06_AI_ARCHITECTURE.md`

---

# 1. Purpose

Validation determines whether extracted information is sufficiently complete, consistent, and reliable for the next workflow step.

Validation is not equivalent to legal ownership determination.

---

# 2. Validation Layers

```text
Field Validation
→ Format Validation
→ Cross-Field Validation
→ Reference Validation
→ Duplicate Detection
→ Confidence Decision
```

---

# 3. Field Validation

Examples:

```text
required owner field missing
→ REVIEW_REQUIRED

required survey field missing
→ REVIEW_REQUIRED

area missing
→ REVIEW_REQUIRED
```

---

# 4. Format Validation

Examples:

```text
area must be numeric
area must be positive
date must be valid
identifier must match supported format
```

Formatting rules must be defined for the selected document/state/domain scope.

Do not invent universal formats where regional variation exists.

---

# 5. Cross-Field Validation

Examples:

```text
village + tehsil + district consistency
area + unit consistency
document type + expected field availability
```

These checks should produce understandable reasons.

---

# 6. Reference-Data Validation

Where trusted reference data exists:

```text
Extracted village
vs
reference village list
```

or:

```text
Village → expected Tehsil → expected District
```

Reference data source and version must be recorded.

If trustworthy reference data is unavailable:

```text
do not pretend validation occurred
```

Use:

```text
NOT_CHECKED
```

or equivalent.

---

# 7. Duplicate Detection

The system may identify possible duplicates using configured combinations such as:

```text
survey number
+
village
+
owner
```

Duplicate detection produces:

```text
NO_MATCH
POSSIBLE_DUPLICATE
CONFIRMED_DUPLICATE
```

A possible duplicate must not automatically be treated as fraud.

---

# 8. Confidence Decision

Example conceptual outcome:

```text
HIGH
→ eligible for normal workflow

MEDIUM
→ review depending on field/rule

LOW
→ human verification required
```

Thresholds must be derived from testing, not arbitrarily described as scientifically valid.

---

# 9. Validation Result Structure

Recommended:

```json
{
  "rule_id": "SURVEY_FORMAT_001",
  "field": "survey_number",
  "status": "WARNING",
  "message": "Value does not match the configured format.",
  "severity": "MEDIUM"
}
```

---

# 10. Severity

Use:

```text
INFO
WARNING
ERROR
CRITICAL
```

Interpretation:

### INFO

No action required.

### WARNING

Review may be appropriate.

### ERROR

Record cannot proceed automatically.

### CRITICAL

Record must be blocked until authorized review resolves the issue.

---

# 11. Approval Rule

A record cannot be approved automatically when:

```text
required field unresolved
critical validation failure exists
mandatory human review incomplete
```

Approval rules belong to backend workflow logic.

---

# 12. Explainability

Every validation failure must answer:

```text
What failed?
Which field?
Why did it fail?
What should the reviewer inspect?
```

Example:

> Khasra Number requires review because extraction confidence is below the configured threshold.

---

# 13. Validation Principle

> **AI may propose values; deterministic rules and authorized humans determine whether the record can proceed.**

# END OF 08_VALIDATION_SPECIFICATION.md
