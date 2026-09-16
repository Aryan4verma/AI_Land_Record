-- ============================================================
-- Reproducible copy of applied migration: land_records_foundation_fixes
-- Addresses Supabase linter findings on the foundation migration:
--   1. function_search_path_mutable (WARN) on set_updated_at
--   2. unindexed_foreign_keys (INFO) x3
-- The remaining rls_enabled_no_policy (INFO) findings are INTENTIONAL:
-- RLS stays enabled with no permissive policies; the FastAPI backend
-- uses service_role (bypasses RLS) and enforces RBAC server-side.
-- ============================================================

-- Fix WARN: pin search_path on trigger function (supabase lint 0011).
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

-- Fix INFO: cover remaining foreign keys with indexes (supabase lint 0001).
CREATE INDEX IF NOT EXISTS idx_field_corrections_changed_by ON public.field_corrections (changed_by);
CREATE INDEX IF NOT EXISTS idx_land_records_approved_by    ON public.land_records (approved_by);
CREATE INDEX IF NOT EXISTS idx_review_tasks_record         ON public.review_tasks (land_record_id);
