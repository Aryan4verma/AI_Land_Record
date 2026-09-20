# PostgreSQL/Supabase Performance Pass

Date: 2026-09-21

## Access-pattern audit

| Area | Actual access pattern | Finding |
|---|---|---|
| Records search | One PostgREST query with selected filters, exact count, ordered page/range | Bounded page reads; count is returned by the same request. Text filters use escaped `ILIKE '%term%'`. |
| Review queue | Status/assignment/priority filters, newest-first ordering, optional range/count | Paginated path is bounded. Legacy array calls remain unbounded for compatibility with the current frontend. Queue projection now selects only response columns. |
| Document lookup | Primary-key lookup by document id | Uses the primary key; no additional lookup index is needed. |
| Processing jobs | Status endpoint previously loaded all jobs for one document; recovery checked the same history | Added one-row latest-job and active-job queries. Added a matching document/created-at index. |
| Audit history | Entity equality filters followed by chronological ordering | Added `(entity_type, entity_id, timestamp, id)` index and removed redundant separate entity/timestamp indexes. |
| Reference data | Active reference rows loaded for validation/review | Controlled lookup set; reduced projection to the columns used by `build_reference`. No speculative status index added. |
| Dashboard | Status/confidence columns are read in bulk and aggregated in Python; recent jobs are limited to 10 | No N+1 pattern. Bulk dashboard aggregation remains appropriate for the prototype; an RPC would add complexity without a demonstrated plan need. |

## Implemented improvements

- `GET /api/v1/documents/{id}/status` now fetches only the newest job row.
- Processing job-creation recovery checks for one active job row instead of
  loading complete job history.
- Review queue and reference-data reads use explicit column projections.
- New migration `20260921130000_query_path_indexes.sql` adds the two
  evidence-based composite indexes and removes the now-redundant component
  indexes after replacement.

## Search and normalization decisions

Record search remains escaped `ILIKE` with bounded pagination. Leading-wildcard
search will not use ordinary B-tree text indexes efficiently, but the current
prototype has no demonstrated scale or latency requirement that justifies
`pg_trgm`, full-text search, or fuzzy matching. Those would require measured
workload evidence and a separate product decision.

Duplicate detection remains an explicit review signal, never an automatic
acceptance. Raw extracted values remain preserved; typed columns are normalized
only at the existing persistence boundary.

## EXPLAIN availability

No `EXPLAIN`/`EXPLAIN ANALYZE` plan was executed. The workspace has no `psql`
or Supabase CLI, and the connected tool surface available in this task does not
expose a SQL execution/RPC plan endpoint. No write or API-key workaround was
used, and no plan was guessed. The new migration should be followed by
read-only `EXPLAIN (ANALYZE, BUFFERS)` checks in the deployment database for:

- latest job by document;
- active job existence by document;
- paginated audit history by entity and timestamp;
- representative record searches with and without text filters.

## Verification

- Focused processing/document/records/review/performance tests: **62 passed**.
- Broader backend suite: **284 passed, 5 known Tesseract-dependent failures,
  1 skipped**.
- Python compilation: passed.
- `git diff --check`: passed.

## Remaining

Legacy review and audit array responses still allow unbounded reads because the
current frontend has not adopted the optional pagination contracts. Dashboard
aggregates still scan their narrow status/confidence columns in bulk. Both are
documented prototype-scale tradeoffs rather than silently changed contracts.
