# Review and Audit API Audit

Date: 2026-09-21

## Review queue findings

Before this pass, the review endpoint applied `status` and `assigned_to`
server-side. The frontend applied status presentation filtering, priority,
free-text search, “mine/unassigned,” and sorting after loading the two open
status lists. There was no backend pagination. Record search already had
server-side filters and page/limit pagination.

The backend now supports server-side `priority` plus bounded optional
`limit`/`offset` pagination. Existing calls without the new parameters still
return the existing array shape. Paginated calls return `items`, `total`,
`limit`, and `offset`; ordering is newest first with a stable id tie-breaker.

## Review correctness

The existing implementation was verified and retained for the required rules:

- operator authorization is enforced on queue, correction, completion,
  approval, rejection, and audit routes;
- corrections require a non-blank justification, preserve the correction row,
  and rerun deterministic validation;
- approved/rejected records cannot be corrected or acted on again;
- approval recomputes validation, required fields, and open reviews on the
  backend before changing status;
- duplicate open reviews and duplicate terminal/completion actions are
  rejected without a second workflow audit event.

## Audit findings and changes

Processing, review creation, field correction, review completion, approval,
and rejection already produced meaningful audit entries. Successful mock-LRMS
dispatches now append `MOCK_LRMS_DISPATCHED`; refused or unauthorized attempts
do not create noise. Audit rows have no application update/delete path, and
the database migration protects them from ordinary update/delete access.

Per-record audit history is now optionally paginated, chronologically ordered,
and still operator-only. A global audit endpoint was not added: the current
frontend explicitly presents record-scoped timelines and has no workspace-wide
audit use case.

## Index review

The existing indexes match the observed queries: the open review partial index
covers status plus creation ordering, `assigned_to` supports assignment
lookups, `idx_review_tasks_record` supports record workflow checks, and
`audit_logs(entity_type, entity_id)` plus timestamp indexing supports the
record audit timeline. No speculative priority or global-audit index was added;
the existing status/creation ordering path remains the known queue access path.
Priority selectivity should be EXPLAIN-checked against live workload before
adding another index.

## Verification

- Focused review/records tests: **22 passed**.
- Existing review regression coverage verifies authorization, correction
  justification and revalidation, terminal immutability, approval blocking,
  duplicate actions, and audit creation.
- New coverage verifies server-side priority filtering, opt-in pagination,
  legacy list compatibility, paginated audit authorization, and mock-LRMS
  dispatch auditing.

## Remaining

The frontend still performs its existing presentation-only search, assignee
shortcut, and sorting locally, and was intentionally not redesigned. A future
frontend can opt into the new paginated contracts. Live EXPLAIN plans remain a
deployment/database-operations check rather than a speculative migration.
