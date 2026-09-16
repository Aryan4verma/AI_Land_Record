# 04_DATA_DICTIONARY.md

# Intelligent Land Record Digitization and Validation System

## Core Data Dictionary

**Depends On:** `01_PROBLEM_RESEARCH.md`, `02_PRD.md`

---

# 1. Purpose

This file defines the structured fields produced by the AI extraction pipeline.

The schema must remain stable across:

```text
OCR
→ LLM extraction
→ validation
→ database
→ API
→ frontend
```

Do not add fields casually. Any schema change must be reflected in the database, API, validation rules, UI, and evaluation documents.

---

# 2. Core Land Record Fields

| Field                 | Type        | Required | Description                            |
| --------------------- | ----------- | -------: | -------------------------------------- |
| record_id             | UUID        |      Yes | Internal unique identifier             |
| owner_name            | String      |     Yes* | Landowner name                         |
| father_or_spouse_name | String      |       No | Parent/spouse name when present        |
| survey_number         | String      |     Yes* | Survey number                          |
| khasra_number         | String      |       No | Khasra number when present             |
| khata_number          | String      |       No | Khata/account number                   |
| area                  | Decimal     |     Yes* | Land area                              |
| area_unit             | Enum/String |     Yes* | Unit such as hectare/acre as supported |
| village               | String      |     Yes* | Village                                |
| tehsil                | String      |     Yes* | Tehsil                                 |
| district              | String      |     Yes* | District                               |
| land_classification   | String      |       No | Classification/category                |
| mutation_number       | String      |       No | Mutation identifier                    |
| registration_number   | String      |       No | Registration identifier                |
| record_date           | Date/String |       No | Relevant record date                   |

`*` Required only when the selected document type is expected to contain the field.

---

# 3. Field-Level AI Metadata

Every extracted field should be able to retain:

```text
field_name
value
confidence
source_page
source_text
bounding_box (when available)
extraction_status
validation_status
```

Example:

```json
{
  "field_name": "survey_number",
  "value": "145/2",
  "confidence": 0.95,
  "source_page": 1,
  "extraction_status": "EXTRACTED",
  "validation_status": "PASS"
}
```

---

# 4. Allowed Field Statuses

### Extraction status

```text
EXTRACTED
MISSING
UNCERTAIN
CONFLICT
ERROR
```

### Validation status

```text
NOT_CHECKED
PASS
WARNING
FAIL
REVIEW_REQUIRED
```

---

# 5. Null and Unknown Rules

If the document does not contain a value:

```text
value = null
status = MISSING
```

If text exists but cannot be reliably interpreted:

```text
value = null or uncertain value according to implementation
status = UNCERTAIN
```

The AI must never invent a value solely to satisfy a required schema.

---

# 6. Normalization Rules

Normalization may include:

* trimming unnecessary whitespace
* consistent date representation
* consistent area/unit representation
* standardized field names
* preserving original values where transformation could affect meaning

Never silently alter the source meaning.

Original/raw extraction should remain recoverable when needed for auditability.

---

# 7. Document Metadata

Each uploaded document should retain:

```text
document_id
file_name
file_type
file_size
language/script if detected
document_type
upload_user
upload_timestamp
processing_status
processing_started_at
processing_completed_at
storage_reference
checksum/hash
```

---

# 8. Confidence Representation

Use a consistent numeric representation internally, preferably:

```text
0.00 → 1.00
```

Frontend may display:

```text
0.95 → 95%
```

The confidence calculation itself is defined in:

`06_AI_ARCHITECTURE.md`

and

`08_VALIDATION_SPECIFICATION.md`

---

# 9. Record Status

A land record may have:

```text
DRAFT
PROCESSING
REVIEW_REQUIRED
READY_FOR_APPROVAL
APPROVED
REJECTED
```

A record must not be treated as approved merely because extraction succeeded.

---

# 10. Ground Truth Compatibility

The schema must also be usable for evaluation.

Ground-truth files should use the same logical field names.

Example:

```json
{
  "owner_name": "Ravi Patel",
  "survey_number": "145/2",
  "area": 2.45,
  "area_unit": "hectare",
  "village": "ABC"
}
```

This allows automated comparison between:

```text
Ground Truth
vs
AI Output
```

---

# 11. Future Extension Rules

New fields may be added only when:

1. The field is supported by an actual document need.
2. It is added to the data dictionary.
3. Database schema is updated.
4. API schema is updated.
5. Validation rules are updated if necessary.
6. UI is updated.
7. Evaluation dataset contains examples.

# END OF 04_DATA_DICTIONARY.md
