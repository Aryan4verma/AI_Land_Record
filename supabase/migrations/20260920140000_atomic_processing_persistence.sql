-- Atomic processing-result persistence.
--
-- OCR/AI work intentionally happens outside this function.  The caller first
-- commits the observable RUNNING/PROCESSING state, then calls this function
-- once for the final result unit.  PostgreSQL functions execute in the
-- surrounding statement transaction: any error rolls back every write below.
-- The JSONB payloads are converted immediately into typed PostgreSQL records;
-- scalar identifiers/statuses remain strongly typed function parameters.

BEGIN;

CREATE OR REPLACE FUNCTION public.persist_processing_result(
  p_job_id              UUID,
  p_document_id         UUID,
  p_user_id             UUID,
  p_ocr_results         JSONB,
  p_record               JSONB,
  p_extracted_fields     JSONB,
  p_validation_results   JSONB,
  p_document_status      TEXT,
  p_verdict              TEXT,
  p_review_priority      TEXT,
  p_review_reason        TEXT,
  p_completion_metadata  JSONB
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = ''
AS $function$
DECLARE
  v_job_status       TEXT;
  v_job_document_id  UUID;
  v_document_status  TEXT;
  v_record_id        UUID;
  v_review_id        UUID;
  v_review_created   UUID;
  v_record           RECORD;
  v_existing_review  UUID;
BEGIN
  IF p_job_id IS NULL OR p_document_id IS NULL OR p_user_id IS NULL THEN
    RAISE EXCEPTION 'Processing persistence requires job, document, and user identifiers.'
      USING ERRCODE = '22023';
  END IF;

  IF p_ocr_results IS NULL
     OR p_extracted_fields IS NULL
     OR p_validation_results IS NULL
     OR p_record IS NULL
     OR p_completion_metadata IS NULL
     OR jsonb_typeof(p_ocr_results) <> 'array'
     OR jsonb_typeof(p_extracted_fields) <> 'array'
     OR jsonb_typeof(p_validation_results) <> 'array'
     OR jsonb_typeof(p_record) <> 'object'
     OR jsonb_typeof(p_completion_metadata) <> 'object' THEN
    RAISE EXCEPTION 'Processing persistence payload has an invalid JSON shape.'
      USING ERRCODE = '22023';
  END IF;

  IF jsonb_array_length(p_ocr_results) = 0 THEN
    RAISE EXCEPTION 'Processing persistence requires at least one OCR page.'
      USING ERRCODE = '22023';
  END IF;

  IF p_document_status IS NULL
     OR p_verdict IS NULL
     OR p_document_status NOT IN ('READY_FOR_APPROVAL', 'VALIDATION_FAILED', 'REVIEW_REQUIRED')
     OR p_verdict NOT IN ('READY_FOR_APPROVAL', 'BLOCKED', 'REVIEW_REQUIRED') THEN
    RAISE EXCEPTION 'Processing persistence received an invalid lifecycle state.'
      USING ERRCODE = '22023';
  END IF;

  IF (p_verdict = 'READY_FOR_APPROVAL' AND p_document_status <> 'READY_FOR_APPROVAL')
     OR (p_verdict = 'BLOCKED' AND p_document_status <> 'VALIDATION_FAILED')
     OR (p_verdict = 'REVIEW_REQUIRED' AND p_document_status <> 'REVIEW_REQUIRED') THEN
    RAISE EXCEPTION 'Processing verdict and document status do not agree.'
      USING ERRCODE = '23514';
  END IF;

  IF p_verdict <> 'READY_FOR_APPROVAL'
     AND (p_review_priority IS NULL
          OR p_review_priority NOT IN ('LOW', 'MEDIUM', 'HIGH', 'URGENT')
          OR p_review_reason IS NULL
          OR NULLIF(btrim(p_review_reason), '') IS NULL) THEN
    RAISE EXCEPTION 'Review persistence requires a valid priority and reason.'
      USING ERRCODE = '22023';
  END IF;

  -- Lock the job and document so a retried or duplicated completion cannot
  -- interleave with this result commit.
  SELECT j.status, j.document_id
    INTO v_job_status, v_job_document_id
    FROM public.processing_jobs AS j
   WHERE j.id = p_job_id
   FOR UPDATE;

  IF NOT FOUND THEN
    RAISE EXCEPTION 'Processing job does not exist.' USING ERRCODE = '23503';
  END IF;
  IF v_job_document_id <> p_document_id THEN
    RAISE EXCEPTION 'Processing job belongs to a different document.' USING ERRCODE = '23514';
  END IF;

  -- A repeated call after a successful commit is safe and does not duplicate
  -- review or audit rows.  A failed job is retried with a new job id.
  IF v_job_status = 'SUCCEEDED' THEN
    SELECT r.id INTO v_record_id
      FROM public.land_records AS r
     WHERE r.document_id = p_document_id;
    IF v_record_id IS NULL THEN
      RAISE EXCEPTION 'Succeeded processing job has no land record.' USING ERRCODE = 'XX001';
    END IF;
    RETURN jsonb_build_object('record_id', v_record_id, 'review_id', NULL, 'replayed', TRUE);
  END IF;
  IF v_job_status <> 'RUNNING' THEN
    RAISE EXCEPTION 'Processing job is not running.' USING ERRCODE = '55000';
  END IF;

  SELECT d.processing_status
    INTO v_document_status
    FROM public.documents AS d
   WHERE d.id = p_document_id
   FOR UPDATE;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'Processing document does not exist.' USING ERRCODE = '23503';
  END IF;
  IF v_document_status <> 'PROCESSING' THEN
    RAISE EXCEPTION 'Processing document is not in PROCESSING state.' USING ERRCODE = '55000';
  END IF;

  -- The document status is workflow metadata and can lag a later approval in
  -- older deployments. Never let a retry overwrite a terminal record.
  IF EXISTS (
    SELECT 1
      FROM public.land_records AS r
     WHERE r.document_id = p_document_id
       AND r.status IN ('APPROVED', 'REJECTED')
  ) THEN
    RAISE EXCEPTION 'A terminal land record cannot be reprocessed.' USING ERRCODE = '55000';
  END IF;

  IF NOT EXISTS (SELECT 1 FROM public.users AS u WHERE u.id = p_user_id) THEN
    RAISE EXCEPTION 'Processing actor does not exist.' USING ERRCODE = '23503';
  END IF;

  -- Parse the record payload into typed columns before any write occurs.  In
  -- particular, DATE and NUMERIC conversion errors abort the whole function.
  SELECT x.*
    INTO v_record
    FROM jsonb_to_record(p_record) AS x(
      owner_name TEXT,
      father_or_spouse_name TEXT,
      survey_number TEXT,
      khasra_number TEXT,
      khata_number TEXT,
      area NUMERIC,
      area_unit TEXT,
      village TEXT,
      tehsil TEXT,
      district TEXT,
      land_classification TEXT,
      mutation_number TEXT,
      registration_number TEXT,
      record_date DATE
    );

  -- Replace is intentional for retry/reprocess: the document's result set is
  -- reconstructed as one unit, so stale child rows cannot survive a retry.
  DELETE FROM public.ocr_results WHERE document_id = p_document_id;
  INSERT INTO public.ocr_results (
    document_id, page_number, text, ocr_confidence, structured_output_reference
  )
  SELECT
    p_document_id, x.page_number, x.text, x.ocr_confidence,
    COALESCE(x.structured_output_reference, '{}'::JSONB)
    FROM jsonb_to_recordset(p_ocr_results) AS x(
      page_number INTEGER,
      text TEXT,
      ocr_confidence DOUBLE PRECISION,
      structured_output_reference JSONB
    );

  INSERT INTO public.land_records (
    document_id, status, owner_name, father_or_spouse_name, survey_number,
    khasra_number, khata_number, area, area_unit, village, tehsil, district,
    land_classification, mutation_number, registration_number, record_date
  ) VALUES (
    p_document_id, CASE WHEN p_verdict = 'READY_FOR_APPROVAL'
                        THEN 'READY_FOR_APPROVAL' ELSE 'REVIEW_REQUIRED' END,
    v_record.owner_name, v_record.father_or_spouse_name, v_record.survey_number,
    v_record.khasra_number, v_record.khata_number, v_record.area, v_record.area_unit,
    v_record.village, v_record.tehsil, v_record.district, v_record.land_classification,
    v_record.mutation_number, v_record.registration_number, v_record.record_date
  )
  ON CONFLICT (document_id) DO UPDATE SET
    status = EXCLUDED.status,
    owner_name = EXCLUDED.owner_name,
    father_or_spouse_name = EXCLUDED.father_or_spouse_name,
    survey_number = EXCLUDED.survey_number,
    khasra_number = EXCLUDED.khasra_number,
    khata_number = EXCLUDED.khata_number,
    area = EXCLUDED.area,
    area_unit = EXCLUDED.area_unit,
    village = EXCLUDED.village,
    tehsil = EXCLUDED.tehsil,
    district = EXCLUDED.district,
    land_classification = EXCLUDED.land_classification,
    mutation_number = EXCLUDED.mutation_number,
    registration_number = EXCLUDED.registration_number,
    record_date = EXCLUDED.record_date
  RETURNING id INTO v_record_id;

  DELETE FROM public.extracted_fields WHERE land_record_id = v_record_id;
  INSERT INTO public.extracted_fields (
    land_record_id, field_name, value, confidence, source_page, source_text,
    bounding_box, extraction_status, validation_status
  )
  SELECT
    v_record_id, x.field_name, x.value, x.confidence, x.source_page, x.source_text,
    x.bounding_box, x.extraction_status, x.validation_status
    FROM jsonb_to_recordset(p_extracted_fields) AS x(
      field_name TEXT,
      value TEXT,
      confidence DOUBLE PRECISION,
      source_page INTEGER,
      source_text TEXT,
      bounding_box JSONB,
      extraction_status TEXT,
      validation_status TEXT
    );

  DELETE FROM public.validation_results WHERE land_record_id = v_record_id;
  INSERT INTO public.validation_results (
    land_record_id, rule_id, field_name, status, severity, message
  )
  SELECT
    v_record_id, x.rule_id, x.field_name, x.status, x.severity, x.message
    FROM jsonb_to_recordset(p_validation_results) AS x(
      rule_id TEXT,
      field_name TEXT,
      status TEXT,
      severity TEXT,
      message TEXT
    );

  UPDATE public.documents
     SET processing_status = p_document_status
   WHERE id = p_document_id;

  IF p_verdict <> 'READY_FOR_APPROVAL' THEN
    SELECT t.id INTO v_existing_review
      FROM public.review_tasks AS t
     WHERE t.land_record_id = v_record_id
       AND t.status IN ('PENDING', 'IN_REVIEW')
     ORDER BY t.created_at DESC
     LIMIT 1
     FOR UPDATE;
    IF v_existing_review IS NULL THEN
      INSERT INTO public.review_tasks (
        land_record_id, status, priority, reason
      ) VALUES (
        v_record_id, 'PENDING', p_review_priority, btrim(p_review_reason)
      ) RETURNING id INTO v_review_id;
      v_review_created := v_review_id;
      INSERT INTO public.audit_logs (
        user_id, entity_type, entity_id, action, metadata
      ) VALUES (
        p_user_id, 'land_record', v_record_id, 'REVIEW_CREATED',
        jsonb_build_object('review_id', v_review_id, 'priority', p_review_priority,
                           'reason', btrim(p_review_reason))
      );
    ELSE
      v_review_id := v_existing_review;
    END IF;
  END IF;

  UPDATE public.processing_jobs
     SET status = 'SUCCEEDED', completed_at = now(), error_code = NULL, error_message = NULL
   WHERE id = p_job_id;

  INSERT INTO public.audit_logs (
    user_id, entity_type, entity_id, action, metadata
  ) VALUES (
    p_user_id, 'document', p_document_id, 'PROCESSING_COMPLETED',
    p_completion_metadata || jsonb_build_object(
      'record_id', v_record_id,
      'review_created', v_review_created
    )
  );

  RETURN jsonb_build_object('record_id', v_record_id, 'review_id', v_review_id, 'replayed', FALSE);
END;
$function$;

COMMENT ON FUNCTION public.persist_processing_result(UUID, UUID, UUID, JSONB, JSONB, JSONB, JSONB, TEXT, TEXT, TEXT, TEXT, JSONB)
  IS 'Atomically persists OCR, land-record, extracted-field, validation, review, final processing state, and completion audit data for one running job.';

REVOKE ALL ON FUNCTION public.persist_processing_result(UUID, UUID, UUID, JSONB, JSONB, JSONB, JSONB, TEXT, TEXT, TEXT, TEXT, JSONB) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.persist_processing_result(UUID, UUID, UUID, JSONB, JSONB, JSONB, JSONB, TEXT, TEXT, TEXT, TEXT, JSONB) FROM anon, authenticated;
GRANT EXECUTE ON FUNCTION public.persist_processing_result(UUID, UUID, UUID, JSONB, JSONB, JSONB, JSONB, TEXT, TEXT, TEXT, TEXT, JSONB) TO service_role;

COMMIT;
