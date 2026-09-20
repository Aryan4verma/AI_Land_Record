-- Query-path indexes for the current FastAPI access patterns.
--
-- The processing status endpoint reads the newest job for one document.
-- Per-record audit history filters by entity and orders chronologically.
-- Composite indexes match those predicates and ordering. The older
-- single-column indexes are dropped only after their composite replacements
-- exist; the leftmost equality columns preserve their lookup coverage.
BEGIN;

CREATE INDEX IF NOT EXISTS idx_processing_jobs_document_created_at
  ON public.processing_jobs (document_id, created_at DESC, id DESC);
DROP INDEX IF EXISTS public.idx_processing_jobs_document_id;

CREATE INDEX IF NOT EXISTS idx_audit_logs_entity_timestamp
  ON public.audit_logs (entity_type, entity_id, timestamp ASC, id ASC);
DROP INDEX IF EXISTS public.idx_audit_logs_entity;
DROP INDEX IF EXISTS public.idx_audit_logs_timestamp;

COMMIT;
