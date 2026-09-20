-- Processing lifecycle hardening.
--
-- A process restart must reconcile the job and its document status together.
-- This function is intentionally small and set-based so the two visible
-- states cannot be committed independently. It does not delete jobs or
-- business results and is safe to call repeatedly.
BEGIN;

CREATE OR REPLACE FUNCTION public.reconcile_stale_processing_jobs()
RETURNS integer
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = ''
AS $$
DECLARE
  v_count integer;
BEGIN
  WITH stale_jobs AS (
    SELECT id, document_id
    FROM public.processing_jobs
    WHERE status IN ('PENDING', 'RUNNING')
    FOR UPDATE
  ), updated_jobs AS (
    UPDATE public.processing_jobs AS jobs
       SET status = 'FAILED',
           completed_at = now(),
           error_code = 'SERVER_RESTARTED',
           error_message = 'Server restarted while this job was running.'
      FROM stale_jobs
     WHERE jobs.id = stale_jobs.id
    RETURNING jobs.document_id
  ), updated_documents AS (
    UPDATE public.documents AS documents
       SET processing_status = 'FAILED'
      FROM updated_jobs
     WHERE documents.id = updated_jobs.document_id
       AND documents.processing_status = 'PROCESSING'
    RETURNING documents.id
  )
  SELECT count(*) INTO v_count FROM updated_jobs;

  RETURN COALESCE(v_count, 0);
END;
$$;

COMMENT ON FUNCTION public.reconcile_stale_processing_jobs() IS
  'Atomically marks pre-restart PENDING/RUNNING jobs failed and releases matching PROCESSING documents for retry.';

REVOKE ALL ON FUNCTION public.reconcile_stale_processing_jobs() FROM PUBLIC;
REVOKE ALL ON FUNCTION public.reconcile_stale_processing_jobs() FROM anon;
REVOKE ALL ON FUNCTION public.reconcile_stale_processing_jobs() FROM authenticated;
GRANT EXECUTE ON FUNCTION public.reconcile_stale_processing_jobs() TO service_role;

COMMIT;
