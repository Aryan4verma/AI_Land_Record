# 05_DATASET_AND_ANNOTATION.md

# Intelligent Land Record Digitization and Validation System

## Dataset and Ground-Truth Specification

**Depends On:** `01_PROBLEM_RESEARCH.md`, `04_DATA_DICTIONARY.md`

---

# 1. Purpose

The dataset is used to:

* test OCR
* test structured extraction
* test validation
* compare AI models
* measure improvements
* demonstrate the system objectively

A model cannot be evaluated reliably without ground truth.

---

# 2. Initial Dataset Target

Start with approximately:

```text
30–50 representative documents
```

The exact number may increase if needed.

Include different difficulty levels:

```text
Clean
Medium quality
Poor quality
Handwritten/challenging
```

---

# 3. Dataset Scope

Initially control:

```text
One document type
One language/script scope
Core fields from 04_DATA_DICTIONARY.md
```

Do not mix many unrelated document types until the primary pipeline works.

---

# 4. Dataset Structure

Recommended:

```text
dataset/
├── raw_documents/
├── preprocessed/
├── ocr_outputs/
├── ground_truth/
├── model_outputs/
├── evaluation/
└── README.md
```

---

# 5. Ground Truth

Ground truth is the manually verified correct structured result.

Example:

```json
{
  "owner_name": "Ravi Patel",
  "survey_number": "145/2",
  "khasra_number": "78",
  "area": 2.45,
  "area_unit": "hectare",
  "village": "ABC",
  "tehsil": "XYZ",
  "district": "DEF"
}
```

Ground truth must be created from the original document by a human and checked before evaluation.

---

# 6. Annotation Rules

Annotators must:

1. Read the original document.
2. Record only information actually present.
3. Preserve uncertain/ambiguous source information appropriately.
4. Use the data dictionary field names.
5. Never infer unsupported values.
6. Record missing values as null/absent according to schema.
7. Preserve units and meaningful distinctions.

---

# 7. Document Difficulty Labels

Each document should have a difficulty label:

```text
EASY
MEDIUM
HARD
CHALLENGING
```

Optional attributes:

```text
printed
handwritten
faded
skewed
noisy
damaged
multi-column
table-heavy
mixed-language
```

These labels help identify where the system fails.

---

# 8. Train/Test Separation

Do not use the same document for both development and final evaluation.

Recommended conceptual split:

```text
Development set
→ prompt/model/rule development

Validation set
→ intermediate testing

Final test set
→ final reported performance
```

For a small hackathon dataset, the exact split may be adjusted, but test documents should remain unseen during final tuning.

---

# 9. OCR Ground Truth

Where practical, store reference text for selected documents.

This allows comparison:

```text
Ground-truth text
vs
OCR text
```

This supports OCR error measurement.

---

# 10. Extraction Evaluation

Compare field-by-field:

```text
Ground truth
vs
AI output
```

Classify each field:

```text
CORRECT
INCORRECT
MISSING
HALLUCINATED
PARTIALLY_CORRECT
```

This is more informative than a single overall score.

---

# 11. Privacy and Data Handling

Only use documents that the team is permitted to use for development/testing.

Do not upload sensitive/unapproved documents to external AI services.

When necessary:

```text
redact
anonymize
syntheticize
```

according to the data-usage requirements.

---

# 12. Versioning

Dataset versions must be identifiable.

Example:

```text
dataset_v1
dataset_v2
dataset_v3
```

When ground truth changes, document why.

Do not silently replace old evaluation results.

---

# 13. Dataset Success Criteria

The dataset is ready when:

```text
Representative documents exist
+
Ground truth is available
+
Core fields are defined
+
Difficulty is recorded
+
Evaluation split is controlled
+
Documents can legally/ethically be used
```

# END OF 05_DATASET_AND_ANNOTATION.md
