-- ============================================================
-- Reproducible copy of applied migration: land_records_foundation
-- SIH 26018 — Intelligent Land Record Digitization & Validation
-- Implements 09_DATABASE_SCHEMA.md (all 12 tables) +
--   CHECK constraints from 04_DATA_DICTIONARY.md statuses and
--   03_USER_FLOW.md document states.
-- Applied to Supabase project ivmkvwudblcqhtoiqlaf via MCP.
-- NOTE: the live database also has follow-up migration
--   land_records_foundation_fixes (pinned search_path on
--   set_updated_at + 3 covering indexes). See sibling file.
-- Rules honored: immutable UUID ids, audit history preserved,
-- document checksum kept, consistent timestamps, NO secrets stored.
-- RLS is enabled on every table with NO permissive policies:
-- all access goes through the FastAPI backend using the
-- service_role key (RBAC enforced server-side per 11_SECURITY_DESIGN).
-- ============================================================

-- ---------- Helper: auto-maintain updated_at ----------
-- Live version pins SET search_path = '' (see fixes migration).
CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = ''
AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$;

-- ---------- roles ----------
CREATE TABLE public.roles (
  id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  name        TEXT        NOT NULL UNIQUE CHECK (name IN ('operator', 'verifier', 'admin')),
  permissions JSONB       NOT NULL DEFAULT '{}'::jsonb,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE public.roles IS 'RBAC role definitions. users.role maps to roles.name (02_PRD section 7, 11_SECURITY_DESIGN section 3).';

-- ---------- users ----------
CREATE TABLE public.users (
  id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  name          TEXT        NOT NULL CHECK (char_length(btrim(name)) > 0),
  email         TEXT        NOT NULL UNIQUE CHECK (email LIKE '%@%'),
  password_hash TEXT,
  auth_id       UUID        UNIQUE,
  role          TEXT        NOT NULL CHECK (role IN ('operator', 'verifier', 'admin')),
  status        TEXT        NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'suspended')),
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON COLUMN public.users.auth_id IS 'Links app user to Supabase Auth identity. NULL until auth is wired (Milestone 4).';
CREATE TRIGGER trg_users_updated_at
  BEFORE UPDATE ON public.users
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- ---------- reference_data ----------
CREATE TABLE public.reference_data (
  id             UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  reference_type TEXT        NOT NULL CHECK (reference_type IN ('district', 'tehsil', 'village', 'land_classification')),
  code           TEXT        NOT NULL,
  name           TEXT        NOT NULL CHECK (char_length(btrim(name)) > 0),
  parent_id      UUID        REFERENCES public.reference_data (id) ON DELETE RESTRICT,
  version        TEXT        NOT NULL DEFAULT 'v1',
  status         TEXT        NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'inactive')),
  created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT uq_reference_data_type_code_version UNIQUE (reference_type, code, version)
);
COMMENT ON TABLE public.reference_data IS 'Controlled vocabularies for validation (village→tehsil→district chain). Source/version recorded per 08 spec.';

-- ---------- documents ----------
CREATE TABLE public.documents (
  id                UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  file_name         TEXT        NOT NULL,
  file_type         TEXT        NOT NULL,
  file_size         BIGINT      NOT NULL CHECK (file_size > 0),
  checksum          TEXT        NOT NULL,
  document_type     TEXT,
  language          TEXT,
  storage_path      TEXT        NOT NULL,
  uploaded_by       UUID        REFERENCES public.users (id) ON DELETE SET NULL,
  uploaded_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  processing_status TEXT        NOT NULL DEFAULT 'UPLOADED'
    CHECK (processing_status IN (
      'UPLOADED', 'PREPROCESSING', 'OCR_PROCESSING', 'EXTRACTION',
      'VALIDATION', 'PROCESSING', 'EXTRACTED', 'VALIDATION_FAILED',
      'REVIEW_REQUIRED', 'READY_FOR_APPROVAL', 'APPROVED', 'REJECTED', 'FAILED')),
  created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TRIGGER trg_documents_updated_at
  BEFORE UPDATE ON public.documents
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- ---------- processing_jobs ----------
CREATE TABLE public.processing_jobs (
  id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id      UUID        NOT NULL REFERENCES public.documents (id) ON DELETE CASCADE,
  status           TEXT        NOT NULL DEFAULT 'PENDING'
    CHECK (status IN ('PENDING', 'RUNNING', 'SUCCEEDED', 'FAILED', 'CANCELLED')),
  pipeline_version TEXT        NOT NULL DEFAULT 'v1',
  started_at       TIMESTAMPTZ,
  completed_at     TIMESTAMPTZ,
  error_code       TEXT,
  error_message    TEXT,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT chk_job_time_order CHECK (completed_at IS NULL OR started_at IS NULL OR completed_at >= started_at)
);

-- ---------- ocr_results ----------
CREATE TABLE public.ocr_results (
  id                          UUID             PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id                 UUID             NOT NULL REFERENCES public.documents (id) ON DELETE CASCADE,
  page_number                 INTEGER          NOT NULL CHECK (page_number >= 1),
  text                        TEXT             NOT NULL DEFAULT '',
  ocr_confidence              DOUBLE PRECISION CHECK (ocr_confidence IS NULL OR (ocr_confidence >= 0 AND ocr_confidence <= 1)),
  structured_output_reference JSONB            NOT NULL DEFAULT '{}'::jsonb,
  created_at                  TIMESTAMPTZ      NOT NULL DEFAULT now(),
  CONSTRAINT uq_ocr_results_document_page UNIQUE (document_id, page_number)
);

-- ---------- land_records ----------
CREATE TABLE public.land_records (
  id                    UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id           UUID        NOT NULL UNIQUE REFERENCES public.documents (id) ON DELETE RESTRICT,
  status                TEXT        NOT NULL DEFAULT 'DRAFT'
    CHECK (status IN ('DRAFT', 'PROCESSING', 'REVIEW_REQUIRED', 'READY_FOR_APPROVAL', 'APPROVED', 'REJECTED')),
  owner_name            TEXT,
  father_or_spouse_name TEXT,
  survey_number         TEXT,
  khasra_number         TEXT,
  khata_number          TEXT,
  area                  NUMERIC,
  area_unit             TEXT,
  village               TEXT,
  tehsil                TEXT,
  district              TEXT,
  land_classification   TEXT,
  mutation_number       TEXT,
  registration_number   TEXT,
  record_date           DATE,
  approved_by           UUID        REFERENCES public.users (id) ON DELETE SET NULL,
  approved_at           TIMESTAMPTZ,
  created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT chk_approved_pair CHECK ((approved_by IS NULL) = (approved_at IS NULL))
);
COMMENT ON COLUMN public.land_records.document_id IS 'One record per document (UNIQUE). ON DELETE RESTRICT protects approved history.';
CREATE TRIGGER trg_land_records_updated_at
  BEFORE UPDATE ON public.land_records
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- ---------- extracted_fields ----------
CREATE TABLE public.extracted_fields (
  id                UUID             PRIMARY KEY DEFAULT gen_random_uuid(),
  land_record_id    UUID             NOT NULL REFERENCES public.land_records (id) ON DELETE CASCADE,
  field_name        TEXT             NOT NULL,
  value             TEXT,
  confidence        DOUBLE PRECISION CHECK (confidence IS NULL OR (confidence >= 0 AND confidence <= 1)),
  source_page       INTEGER          CHECK (source_page IS NULL OR source_page >= 1),
  source_text       TEXT,
  bounding_box      JSONB,
  extraction_status TEXT             NOT NULL DEFAULT 'EXTRACTED'
    CHECK (extraction_status IN ('EXTRACTED', 'MISSING', 'UNCERTAIN', 'CONFLICT', 'ERROR')),
  validation_status TEXT             NOT NULL DEFAULT 'NOT_CHECKED'
    CHECK (validation_status IN ('NOT_CHECKED', 'PASS', 'WARNING', 'FAIL', 'REVIEW_REQUIRED')),
  created_at        TIMESTAMPTZ      NOT NULL DEFAULT now(),
  CONSTRAINT uq_extracted_fields_record_field UNIQUE (land_record_id, field_name)
);

-- ---------- validation_results ----------
CREATE TABLE public.validation_results (
  id             UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  land_record_id UUID        NOT NULL REFERENCES public.land_records (id) ON DELETE CASCADE,
  rule_id        TEXT        NOT NULL,
  field_name     TEXT,
  status         TEXT        NOT NULL
    CHECK (status IN ('NOT_CHECKED', 'PASS', 'WARNING', 'FAIL', 'REVIEW_REQUIRED')),
  severity       TEXT        NOT NULL
    CHECK (severity IN ('INFO', 'WARNING', 'ERROR', 'CRITICAL')),
  message        TEXT        NOT NULL,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------- review_tasks ----------
CREATE TABLE public.review_tasks (
  id             UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  land_record_id UUID        NOT NULL REFERENCES public.land_records (id) ON DELETE CASCADE,
  assigned_to    UUID        REFERENCES public.users (id) ON DELETE SET NULL,
  status         TEXT        NOT NULL DEFAULT 'PENDING'
    CHECK (status IN ('PENDING', 'IN_REVIEW', 'COMPLETED', 'CANCELLED')),
  priority       TEXT        NOT NULL DEFAULT 'MEDIUM'
    CHECK (priority IN ('LOW', 'MEDIUM', 'HIGH', 'URGENT')),
  reason         TEXT,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  completed_at   TIMESTAMPTZ
);

-- ---------- field_corrections ----------
CREATE TABLE public.field_corrections (
  id             UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  land_record_id UUID        NOT NULL REFERENCES public.land_records (id) ON DELETE CASCADE,
  field_name     TEXT        NOT NULL,
  old_value      TEXT,
  new_value      TEXT,
  reason         TEXT,
  changed_by     UUID        REFERENCES public.users (id) ON DELETE SET NULL,
  changed_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE public.field_corrections IS 'Append-only human-correction history feeding the feedback dataset (01 section 15).';

-- ---------- audit_logs (append-only) ----------
CREATE TABLE public.audit_logs (
  id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     UUID        REFERENCES public.users (id) ON DELETE SET NULL,
  entity_type TEXT        NOT NULL,
  entity_id   UUID,
  action      TEXT        NOT NULL,
  old_value   JSONB,
  new_value   JSONB,
  metadata    JSONB       NOT NULL DEFAULT '{}'::jsonb,
  timestamp   TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE public.audit_logs IS 'Append-only. entity_id is polymorphic (no FK). Protected from ordinary edits (Rule 2, 11_SECURITY_DESIGN section 7).';

-- ============================================================
-- Indexes
-- ============================================================
CREATE INDEX idx_documents_checksum          ON public.documents (checksum);
CREATE INDEX idx_documents_processing_status ON public.documents (processing_status);
CREATE INDEX idx_documents_uploaded_by       ON public.documents (uploaded_by);

CREATE INDEX idx_processing_jobs_document_id ON public.processing_jobs (document_id);
CREATE INDEX idx_processing_jobs_status      ON public.processing_jobs (status);

CREATE INDEX idx_land_records_status         ON public.land_records (status);
CREATE INDEX idx_land_records_survey_village ON public.land_records (survey_number, village);
CREATE INDEX idx_land_records_owner          ON public.land_records (owner_name);
CREATE INDEX idx_land_records_district       ON public.land_records (district);

CREATE INDEX idx_extracted_fields_needs_review
  ON public.extracted_fields (land_record_id)
  WHERE validation_status IN ('FAIL', 'REVIEW_REQUIRED');

CREATE INDEX idx_validation_results_record   ON public.validation_results (land_record_id);
CREATE INDEX idx_validation_results_blocking
  ON public.validation_results (land_record_id)
  WHERE severity IN ('ERROR', 'CRITICAL');

CREATE INDEX idx_review_tasks_open
  ON public.review_tasks (status, created_at)
  WHERE status IN ('PENDING', 'IN_REVIEW');
CREATE INDEX idx_review_tasks_assigned_to    ON public.review_tasks (assigned_to);

CREATE INDEX idx_field_corrections_record    ON public.field_corrections (land_record_id);

CREATE INDEX idx_audit_logs_entity           ON public.audit_logs (entity_type, entity_id);
CREATE INDEX idx_audit_logs_user             ON public.audit_logs (user_id);
CREATE INDEX idx_audit_logs_timestamp        ON public.audit_logs (timestamp DESC);

CREATE INDEX idx_reference_data_parent       ON public.reference_data (parent_id);
CREATE INDEX idx_reference_data_type         ON public.reference_data (reference_type);

-- NOTE: fixes migration additionally creates:
--   idx_field_corrections_changed_by, idx_land_records_approved_by,
--   idx_review_tasks_record (see sibling file).

-- ============================================================
-- Row Level Security: enabled everywhere, no permissive policies.
-- Backend uses service_role (bypasses RLS); RBAC lives in the API.
-- ============================================================
ALTER TABLE public.roles              ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.users              ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.documents          ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.processing_jobs    ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ocr_results        ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.land_records       ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.extracted_fields   ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.validation_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.review_tasks       ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.field_corrections  ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.audit_logs         ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.reference_data     ENABLE ROW LEVEL SECURITY;

-- Defense in depth: history tables immutable for API roles even if
-- a permissive policy is added later by mistake.
REVOKE UPDATE, DELETE ON public.audit_logs FROM anon, authenticated;
REVOKE UPDATE, DELETE ON public.field_corrections FROM anon, authenticated;

-- ============================================================
-- Seed: RBAC roles (02_PRD section 7)
-- ============================================================
INSERT INTO public.roles (name, permissions) VALUES
  ('operator', '{"actions": ["documents:upload", "documents:process", "documents:view", "reviews:create"]}'::jsonb),
  ('verifier', '{"actions": ["documents:upload", "documents:process", "documents:view", "reviews:create", "reviews:review", "reviews:edit", "records:approve", "records:reject"]}'::jsonb),
  ('admin',    '{"actions": ["documents:upload", "documents:process", "documents:view", "reviews:create", "reviews:review", "reviews:edit", "records:approve", "records:reject", "users:manage", "audit:view", "system:configure"]}'::jsonb)
ON CONFLICT (name) DO NOTHING;

-- ============================================================
-- Seed: clearly-labeled DEMO reference chain (one district).
-- NOT real government data. Replaced by controlled reference
-- dataset before any real validation (08 section 6).
-- ============================================================
INSERT INTO public.reference_data (reference_type, code, name, parent_id, version, status)
VALUES ('district', 'DEMO-D01', 'Demo District', NULL, 'v1', 'active')
ON CONFLICT (reference_type, code, version) DO NOTHING;

INSERT INTO public.reference_data (reference_type, code, name, parent_id, version, status)
VALUES ('tehsil', 'DEMO-T01', 'Demo Tehsil',
  (SELECT id FROM public.reference_data WHERE reference_type = 'district' AND code = 'DEMO-D01' AND version = 'v1'),
  'v1', 'active')
ON CONFLICT (reference_type, code, version) DO NOTHING;

INSERT INTO public.reference_data (reference_type, code, name, parent_id, version, status)
VALUES ('village', 'DEMO-V01', 'Demo Village',
  (SELECT id FROM public.reference_data WHERE reference_type = 'tehsil' AND code = 'DEMO-T01' AND version = 'v1'),
  'v1', 'active')
ON CONFLICT (reference_type, code, version) DO NOTHING;

INSERT INTO public.reference_data (reference_type, code, name, parent_id, version, status)
VALUES
  ('land_classification', 'DEMO-AGRI', 'Agricultural', NULL, 'v1', 'active'),
  ('land_classification', 'DEMO-RES', 'Residential', NULL, 'v1', 'active')
ON CONFLICT (reference_type, code, version) DO NOTHING;
