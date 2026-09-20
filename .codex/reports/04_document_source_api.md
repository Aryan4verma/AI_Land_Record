# Document Source API Audit

Date: 2026-09-21

## Implemented endpoint

Added:

```text
GET /api/v1/documents/{document_id}/pages/{page_number}
```

The endpoint:

- requires the current server-side `user` role minimum, so read-only users,
  operators, and admins can view source evidence according to the existing
  product model;
- resolves the document through the backend store and never accepts a storage
  path from the caller;
- accepts only the generated `documents/<hex>/<hex>.<extension>` storage-path
  shape, rejecting traversal, absolute paths, backslashes, and unexpected
  locations;
- downloads through the existing private Supabase storage service-role path;
- renders only the requested PDF page with PyMuPDF at a browser-suitable DPI;
- treats uploaded raster images as one-page sources;
- returns a private, non-cacheable JPEG with `nosniff` protection;
- validates page numbers and caps the route parameter at 10,000;
- caps decoded render size at 20 million pixels to reduce memory-exhaustion
  risk;
- maps missing source, invalid page, corrupt source, and storage failures to
  safe error envelopes without exposing paths, credentials, provider details,
  or library exception text.

No public bucket or signed browser URL was introduced. No new storage system or
frontend change was made.

## Source provenance review

The existing OCR contract has genuine line coordinates in
`OcrLine.box`, plus page number, dimensions, text, and confidence. The current
database persistence stores OCR page text and structural dimensions, while
`extracted_fields` already supports nullable `source_page`, `source_text`, and
`bounding_box` columns.

The extraction provider currently does not return grounded coordinates or
source spans, and the pipeline therefore persists those fields as `NULL`. The
document extraction response now has an explicit typed model for these
optional fields and returns them when stored evidence exists. It does not
invent page numbers or coordinates. The page endpoint supplies the document
and page context independently; field-to-source links remain absent unless
the pipeline has real evidence to store.

## Failure and authorization behavior

- Missing document row: `404 DOCUMENT_NOT_FOUND`.
- Missing private object: `404 DOCUMENT_SOURCE_NOT_FOUND`.
- Out-of-range page: `404 DOCUMENT_PAGE_NOT_FOUND`.
- Corrupt/unsupported source: `422 DOCUMENT_SOURCE_INVALID`.
- Storage transport failure: `503 STORAGE_UNAVAILABLE`.
- Missing or invalid bearer token: `401`.
- Read-only users are intentionally authorized for source viewing, matching
  the existing “user = read-only record/view access” model.

## Verification

- Document source/page and related backend regression tests: **69 passed**.
- Full backend suite: **276 passed, 5 known multilingual OCR failures, 1 skipped**.
- Secret scan passed.
- Python compilation passed.
- `git diff --check` passed.
- Existing frontend code was not modified.

## Remaining

- A live authenticated smoke test against the hosted private Supabase bucket
  remains deployment verification; the available task surface did not provide
  a live write/migration execution path.
- The frontend can consume the endpoint in a later task; it was intentionally
  left unchanged here.
