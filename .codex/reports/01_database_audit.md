# PostgreSQL / Supabase Audit

Date: 2026-09-20  
Project: `ivmkvwudblcqhtoiqlaf`

## 1. Schema drift

Repository migrations contain five ordered migrations covering the expected 12
public tables, the two-role vocabulary (`user`, `operator`, `admin`),
`users.id_number`, the documented foreign keys, lifecycle checks, unique
constraints, timestamp trigger, RLS enablement, and private document storage.

Live PostgREST schema inspection confirmed the same 12 tables and the expected
live columns, primary-key markers, and foreign-key relationships. Live data
also confirmed the current two-role user population and three role definitions.

One repository artifact was stale: `supabase/database.types.ts` omitted the
live `users.id_number` column. Its Row/Insert/Update types were corrected.

The configured task MCP surface exposed read-only PostgREST/OpenAPI and
storage access, but did not expose `execute_sql` or PostgreSQL catalog views.
Therefore exact live enumeration of every CHECK constraint, index definition,
trigger/function attribute, RLS policy row, and grant cannot be independently
claimed from this session. The migration definitions were compared against the
live exposed schema and behavioral access checks; no table/column/FK drift was
found.

## 2. Integrity risks

Live read-only checks returned:

- 0 orphan rows across processing jobs, OCR results, land records, extracted
  fields, validation results, review tasks, field corrections, and user-linked
  columns.
- 0 duplicate `(document_id, page_number)` OCR rows and 0 duplicate
  `land_records.document_id` rows.
- 0 invalid job timestamp order, record timestamp order, review completion
  mismatches, or approved-by/approved-at pair mismatches.
- Only declared lifecycle/status values were present.
- 3 duplicate document-checksum groups. This is a source-duplication/cost
  concern, not a safe candidate for a global UNIQUE constraint because the
  product intentionally retains checksum information for duplicate/source
  tracking and may receive renamed copies.
- 4 storage objects not referenced by `documents.storage_path` (188 bytes).
  Every document row had a corresponding storage object. These are cleanup
  candidates from prior runs; no production object was deleted.

Nullable fields are consistent with the workflow: extracted values and review
assignment may be absent, historical actor references use `ON DELETE SET NULL`,
and `users.id_number` remains nullable only for pre-existing accounts. Audit
history uses the intentional polymorphic `entity_id` and was not redesigned.

## 3. Index review

The repository query review found coverage for the demonstrated access paths:

- review queue: partial open-task `(status, created_at)`, assignment, and task
  record indexes;
- record search/status: status, survey/village, owner, and district indexes;
- document lookup: checksum, processing status, and uploader indexes;
- processing jobs: document and status indexes;
- audit history: entity, actor, and descending timestamp indexes;
- reference data: parent and type indexes;
- all remaining foreign keys added by the fixes migration.

No index was added. The main record filters use leading-wildcard `ILIKE`, so
the existing B-tree indexes would not prove a benefit for those searches; a
trigram design would require measured `EXPLAIN` evidence and an extension
decision. The small live dataset does not justify speculative indexes.

## 4. RLS review

The repository migrations intentionally enable RLS on all 12 public business
tables and create no permissive frontend policies. The FastAPI service-role
connection remains the application boundary; no direct-to-Supabase frontend
architecture was introduced.

Behavioral live checks using the anon key returned zero rows for users,
documents, audit logs, and reference data. Anonymous storage listing also
returned zero objects, while the bucket is reported as private with a 10 MiB
limit and the expected four MIME types. This is consistent with deny-by-
default RLS/storage behavior. Exact policy/grant catalog rows require the
unavailable SQL MCP surface and remain a follow-up verification item.

## 5. Audit integrity

`audit_logs.entity_id` remains polymorphic by design. Existing migrations
protect ordinary API roles from updating/deleting audit rows, and application
review flows append audit entries for corrections and terminal decisions.
No delete/rewrite cleanup was performed. User deletion semantics retain audit
rows by nulling the actor reference rather than deleting history.

## 6. Migration quality

The migration sequence is timestamp ordered and forward-oriented. The
foundation migration is followed by its search-path/index fixes, storage
configuration, `id_number`, and the two-role transition. Seed inserts use
conflict-safe behavior where appropriate; the storage bucket migration is
idempotent; the two-role migration documents a rollback path and preserves
historical data. Historical migrations were not edited.

No new database migration was necessary. The only high-confidence drift fix
was the generated TypeScript type update.

## 7. Data cleanup

No existing production data or storage objects were deleted or rewritten.
The four unreferenced storage objects and duplicate checksum groups should be
reviewed by an operator. If cleanup is approved, create a new reviewed
migration/maintenance procedure with an explicit allow-list, audit record,
retention window, and dry-run count before deletion.

## Verification

- Live schema/data/storage checks completed through the configured Supabase
  connection without printing credentials or document contents.
- Anonymous table/storage access checks returned no rows/objects.
- Migration filenames are ordered and all historical files remain unchanged.
- Relevant backend tests and TypeScript validation were run after the type
  drift correction.

## Remaining

- Run a catalog-level SQL audit (`pg_catalog` / `information_schema`, storage
  policies, grants, and `EXPLAIN`) once the Supabase MCP `execute_sql` tool is
  exposed to this task. No claim is made that this unavailable portion was
  fully enumerated here.
- Review the four orphan storage objects and three duplicate checksum groups;
  do not delete automatically.
