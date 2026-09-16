# 09_DATABASE_SCHEMA.md

# Intelligent Land Record Digitization and Validation System

## Database Schema

**Depends On:** `02_PRD.md`, `04_DATA_DICTIONARY.md`, `08_VALIDATION_SPECIFICATION.md`

---

# 1. Database Goal

Store:

* users
* documents
* processing jobs
* OCR output
* extracted records
* field-level results
* validation results
* reviews
* audit history
* reference data

The database should preserve enough information to reconstruct important processing and review history.

---

# 2. Main Tables

## users

```text
id
name
email
password/auth reference
id_number (nullable; required at registration, NULL only for pre-existing rows)
role
status
created_at
updated_at
```

---

## roles

```text
id
name
permissions
```

Possible roles (revised 2026-09-07 — `verifier` retired, capabilities
mapped onto `operator`):

```text
user       read-only
operator   full document + review/approval workflow
admin      internal only, not user-facing
```

Enforced by CHECK constraints on `users.role` and `roles.name`
(migration `20260907102842_two_role_architecture`). `users.role` is a
CHECK-constrained TEXT column, not a foreign key to `roles.name`.

---

## documents

```text
id
file_name
file_type
file_size
checksum
document_type
language
storage_path
uploaded_by
uploaded_at
processing_status
created_at
updated_at
```

---

## processing_jobs

```text
id
document_id
status
pipeline_version
started_at
completed_at
error_code
error_message
```

---

## ocr_results

```text
id
document_id
page_number
text
ocr_confidence
structured_output_reference
created_at
```

If needed, bounding boxes can be stored separately or as structured data.

---

## land_records

```text
id
document_id
status
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
created_at
updated_at
approved_by
approved_at
```

---

## extracted_fields

Use this to preserve field-level metadata.

```text
id
land_record_id
field_name
value
confidence
source_page
source_text
bounding_box
extraction_status
validation_status
```

---

## validation_results

```text
id
land_record_id
rule_id
field_name
status
severity
message
created_at
```

---

## review_tasks

```text
id
land_record_id
assigned_to
status
priority
reason
created_at
completed_at
```

Statuses:

```text
PENDING
IN_REVIEW
COMPLETED
CANCELLED
```

---

## field_corrections

```text
id
land_record_id
field_name
old_value
new_value
reason
changed_by
changed_at
```

---

## audit_logs

```text
id
user_id
entity_type
entity_id
action
old_value
new_value
metadata
timestamp
```

---

## reference_data

```text
id
reference_type
code
name
parent_id
version
status
```

Possible reference types:

```text
district
tehsil
village
land_classification
```

---

# 3. Relationships

```text
users
  ↓
documents
  ↓
processing_jobs
  ↓
ocr_results

documents
  ↓
land_records
  ↓
extracted_fields
  ↓
validation_results
  ↓
review_tasks
  ↓
field_corrections
  ↓
audit_logs
```

Reference data can be connected to relevant land-record fields logically or through foreign keys where appropriate.

---

# 4. Database Rules

## Rule 1

Use immutable IDs.

## Rule 2

Do not delete audit history as part of ordinary editing.

## Rule 3

Keep document checksum/hash to support duplicate/source tracking.

## Rule 4

Use timestamps consistently.

## Rule 5

Do not store secrets such as provider API keys in normal business tables.

---

# 5. Data Integrity

Use:

* primary keys
* foreign keys
* unique constraints where appropriate
* not-null constraints where justified
* check constraints where appropriate
* transactions for multi-table operations

---

# 6. MVP Simplification

The exact production schema may be more complex.

For MVP, prioritize:

```text
users
documents
land_records
extracted_fields
validation_results
review_tasks
audit_logs
reference_data
```

# END OF 09_DATABASE_SCHEMA.md
