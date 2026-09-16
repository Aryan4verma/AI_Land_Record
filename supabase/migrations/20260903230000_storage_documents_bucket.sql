-- ============================================================
-- Reproducible copy of applied migration: storage_documents_bucket
-- STEP 04 — private bucket for land-record source documents.
-- Backend uses the service_role key (bypasses storage RLS by design);
-- no public access and no permissive storage policies are created.
-- Server-side guards mirror the API validation: 10 MB + PDF/image only.
-- ============================================================

INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
  'land-record-documents',
  'land-record-documents',
  false,
  10485760,
  ARRAY['application/pdf', 'image/png', 'image/jpeg', 'image/tiff']
)
ON CONFLICT (id) DO UPDATE SET
  public = false,
  file_size_limit = EXCLUDED.file_size_limit,
  allowed_mime_types = EXCLUDED.allowed_mime_types;
