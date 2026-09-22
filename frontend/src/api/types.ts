/**
 * Canonical API payload types. Backend is authoritative: every interface
 * mirrors a FastAPI response/request schema or a documented JSON shape
 * from 10_API_SPECIFICATION.md. Field names are NEVER renamed here.
 */

/** POST /api/v1/auth/login */
export interface LoginRequest {
  email: string;
  password: string;
}

/** TokenResponse */
export interface TokenResponse {
  access_token: string;
  token_type: string;
}

/** UserOut — GET /api/v1/auth/me */
export interface User {
  id: string;
  name: string;
  email: string;
  role: "user" | "operator" | "admin";
  status: string;
  id_number?: string | null;
}

/** POST /api/v1/auth/register — self-registration (no role; server assigns read-only user) */
export interface RegisterRequest {
  name: string;
  id_number: string;
  email: string;
  password: string;
}

/** RegisterResponse (201) — safe account summary, never secrets */
export interface RegisterResponse {
  id: string;
  name: string;
  id_number: string | null;
  email: string;
  role: string;
  status: string;
  created_at: string;
}

/** DocumentUploadResponse — POST /api/v1/documents (201) */
export interface DocumentUploadResponse {
  document_id: string;
  status: string;
}

/** DocumentOut — GET /api/v1/documents/{id} */
export interface Document {
  id: string;
  file_name: string;
  file_type: string;
  file_size: number;
  checksum: string;
  document_type: string | null;
  language: string | null;
  storage_path: string;
  uploaded_by: string | null;
  uploaded_at: string;
  processing_status: string;
  created_at: string;
  updated_at: string;
}

/** DocumentStatusOut — GET /api/v1/documents/{id}/status */
export interface DocumentStatus {
  document_id: string;
  status: string;
  job_id?: string | null;
  job_status?: string | null;
  error_code?: string | null;
  error_message?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
}

/** One row of extracted_fields — GET .../extraction */
export interface ExtractedField {
  field_name: string;
  value: string | number | null;
  confidence: number | null;
  source_page?: number | null;
  source_text?: string | null;
  bounding_box?: unknown;
  extraction_status?: string;
  validation_status?: string;
}

/** DocumentExtractionOut */
export interface DocumentExtraction {
  document_id: string;
  record_id: string;
  status: string;
  fields: ExtractedField[];
}

/** One validation_results row — GET .../validation */
export interface ValidationIssue {
  rule_id: string;
  field_name: string | null;
  status: string;
  severity: string;
  message: string;
}

/** DocumentValidationOut */
export interface DocumentValidation {
  document_id: string;
  record_id: string;
  status: string;
  issues: ValidationIssue[];
}

/** land_records row (subset relevant to the UI; all 04_DATA_DICTIONARY fields) */
export interface LandRecord {
  id: string;
  document_id: string;
  status: string;
  owner_name: string | null;
  father_or_spouse_name: string | null;
  survey_number: string | null;
  khasra_number: string | null;
  khata_number: string | null;
  area: string | number | null;
  area_unit: string | null;
  village: string | null;
  tehsil: string | null;
  district: string | null;
  land_classification: string | null;
  mutation_number: string | null;
  registration_number: string | null;
  record_date: string | null;
  approved_by?: string | null;
  approved_at?: string | null;
  created_at?: string;
  updated_at?: string;
}

/** RecordSearchOut — GET /api/v1/records */
export interface RecordSearchResult {
  items: LandRecord[];
  page: number;
  limit: number;
  total: number;
}

export interface RecordSearchParams {
  owner?: string;
  survey_number?: string;
  khasra_number?: string;
  village?: string;
  tehsil?: string;
  district?: string;
  status?: string;
  page?: number;
  limit?: number;
}

/** RecordDetailOut — GET /api/v1/records/{id} */
export interface RecordDetail {
  record: LandRecord;
  extracted_fields: ExtractedField[];
  validation: ValidationIssue[];
  document: Document | null;
}

/** RecordExportOut — GET /api/v1/records/{id}/export */
export interface RecordExport extends RecordDetail {
  exported_at: string;
  format_version: string;
}

/** review_tasks row */
export interface ReviewTask {
  id: string;
  land_record_id: string;
  assigned_to: string | null;
  status: string;
  priority: string;
  reason: string | null;
  created_at: string;
  completed_at: string | null;
}

/** ReviewCreate — POST /api/v1/reviews */
export interface ReviewCreate {
  land_record_id: string;
  reason: string;
  priority?: "LOW" | "MEDIUM" | "HIGH" | "URGENT";
}

/** CorrectionIn — PATCH /api/v1/reviews/{id}/fields/{field} */
export interface CorrectionIn {
  value: string | null;
  reason: string;
}

/** ReviewDetailOut — GET/PATCH review (includes revalidation) */
export interface ReviewDetail {
  task: ReviewTask;
  record: LandRecord;
  extracted_fields: ExtractedField[];
  validation: ValidationIssue[];
  verdict: string;
  approval_blocked: boolean;
  document: Document | null;
}

/** audit_logs row — GET /api/v1/records/{id}/audit */
export interface AuditEntry {
  id: string;
  user_id: string | null;
  action: string;
  entity_type: string;
  entity_id: string | null;
  old_value: unknown;
  new_value: unknown;
  metadata: Record<string, unknown>;
  timestamp: string;
}

/** DashboardSummaryOut */
export interface DashboardSummary {
  documents_total: number;
  documents_by_status: Record<string, number>;
  records_by_status: Record<string, number>;
  open_reviews: number;
  average_confidence: number | null;
}

/** DashboardProcessingOut */
export interface DashboardProcessing {
  jobs_by_status: Record<string, number>;
  recent_jobs: Record<string, unknown>[];
}

/** DashboardValidationOut */
export interface DashboardValidation {
  issues_by_severity: Record<string, number>;
  issues_by_status: Record<string, number>;
  blocked_documents: number;
}

/** GET /health/ai — public wiring status (provider/model/lanes, never keys) */
export interface HealthAi {
  ai: string;
  provider?: string;
  model?: string;
  lanes?: number;
  cache_enabled?: boolean;
  demo_enabled?: boolean;
  detail?: string;
}

/** Backend record/document status -> StatusBadge tone (single mapping point). */
export type StatusTone = "verified" | "review" | "failed" | "processing" | "neutral";

/** Confidence fraction -> StatusBadge tone (Stitch §Components.2 bands). */export function confidenceTone(value: number | null | undefined): StatusTone {
  if (value === null || value === undefined) return "neutral";
  if (value >= 0.9) return "verified";
  if (value >= 0.7) return "review";
  return "failed";
}

/**
 * Backend validation verdict -> human overall result. Display mapping only;
 * unknown verdicts render verbatim (neutral) rather than guessed.
 */export function validationVerdict(status: string): { label: string; tone: StatusTone } {
  switch ((status || "").toUpperCase()) {
    case "READY_FOR_APPROVAL":
      return { label: "Ready", tone: "verified" };
    case "REVIEW_REQUIRED":
      return { label: "Review required", tone: "review" };
    case "BLOCKED":
    case "VALIDATION_FAILED":
      return { label: "Blocked", tone: "failed" };
    default:
      return { label: status || "Unknown", tone: "neutral" };
  }
}

/**
 * Overall result banner from backend states (document status + validation
 * verdict). Pure display mapping for the result experience: green = ready,
 * amber = review needed, red = blocked/failed. Nothing is decided here.
 */
export function resultBanner(
  docStatus: string,
  validationStatus: string | null | undefined,
): { tone: "success" | "error" | "info"; title: string; body: string } {
  const doc = (docStatus || "").toUpperCase();
  const val = (validationStatus || "").toUpperCase();
  if (doc === "FAILED" || doc === "VALIDATION_FAILED" || val === "BLOCKED") {
    return {
      tone: "error",
      title: "Processing failed",
      body: "The backend pipeline did not produce a usable record. Retry processing from the document view or inspect the validation findings below.",
    };
  }
  if ((doc === "READY_FOR_APPROVAL" || doc === "APPROVED") && (!val || val === "READY_FOR_APPROVAL")) {
    return {
      tone: "success",
      title: "Ready",
      body: "Extraction finished and backend checks are clean. An operator can approve from the review workspace.",
    };
  }
  if (val === "REVIEW_REQUIRED" || doc === "REVIEW_REQUIRED") {
    return {
      tone: "info",
      title: "Needs review",
      body: "Extraction finished with findings a human must resolve before approval.",
    };
  }
  return {
    tone: "info",
    title: "Processing",
    body: "The backend pipeline has not reached a terminal state yet.",
  };
}

/**
 * Stitch pipeline stages mapped to the aggregate backend document status.
 * The backend exposes one live status per document (no per-stage events,
 * timings, or worker telemetry), so mid-pipeline stages share a single
 * "active" group and per-stage durations are never shown. Terminal and
 * failure flags drive the success/failure panels and polling stop.
 */
export type StepState = "done" | "active" | "queued" | "failed" | "unknown";

export interface PipelineStep {
  key: string;
  label: string;
  state: StepState;
}

export interface PipelineView {
  steps: PipelineStep[];
  terminal: boolean;
  failed: boolean;
}

const PIPELINE_LABELS: [string, string][] = [
  ["uploaded", "Document uploaded"],
  ["preprocessing", "Image preprocessing"],
  ["ocr", "OCR"],
  ["normalization", "Text normalization"],
  ["extraction", "Field extraction"],
  ["validation", "Validation"],
  ["confidence", "Confidence analysis"],
  ["review", "Review preparation"],
];

const TERMINAL_GOOD = new Set(["REVIEW_REQUIRED", "READY_FOR_APPROVAL", "APPROVED", "REJECTED"]);
const TERMINAL_FAILED = new Set(["VALIDATION_FAILED", "FAILED"]);

/** Return the known zero-based stage for a failure, or null when the backend
 * only supplied an aggregate FAILED state. Unknown stages must never be
 * presented as failed by inference.
 */
function failureStageIndex(status: string, errorCode: string): number | null {
  if (status === "VALIDATION_FAILED") return 5;
  if (["OCR_FAILED", "OCR_ENGINE_UNAVAILABLE"].includes(errorCode)) return 2;
  if (["RENDER_FAILED", "UNSUPPORTED_FILE_TYPE"].includes(errorCode)) return 1;
  if (errorCode.startsWith("PROVIDER_")) return 4;
  return null;
}

export function processingSteps(status: string, errorCode = ""): PipelineView {
  const normalized = (status || "").toUpperCase();
  const normalizedError = (errorCode || "").toUpperCase();
  const failed = TERMINAL_FAILED.has(normalized);
  const good = TERMINAL_GOOD.has(normalized);
  const running = normalized === "PROCESSING" || normalized === "EXTRACTED";
  const knownFailure = failureStageIndex(normalized, normalizedError);
  const steps = PIPELINE_LABELS.map(([key, label], i) => {
    let state: StepState = "queued";
    if (good) state = "done";
    else if (failed) {
      if (knownFailure === null) state = i === 0 ? "done" : "unknown";
      else if (i < knownFailure) state = "done";
      else if (i === knownFailure) state = "failed";
      else state = "unknown";
    }
    else if (i === 0) state = "done";
    else if (running && i <= 4) state = "active";
    return { key, label, state };
  });
  return { steps, terminal: good || failed, failed };
}

/**
 * Instant client-side upload pre-check mirroring the backend contract
 * (backend/app/documents: pdf/png/jpg/jpeg/tif/tiff, 10 MiB cap, MIME
 * cross-check). Returns an error code or null when acceptable. The backend
 * re-validates everything (magic bytes included) and stays authoritative.
 */
export const UPLOAD_MAX_BYTES = 10 * 1024 * 1024;

const UPLOAD_EXT_TO_MIME: Record<string, string> = {
  pdf: "application/pdf",
  png: "image/png",
  jpg: "image/jpeg",
  jpeg: "image/jpeg",
  tif: "image/tiff",
  tiff: "image/tiff",
};

export function uploadFileCheck(
  fileName: string,
  fileSize: number,
  mimeType: string,
): "UNSUPPORTED_FILE_TYPE" | "FILE_TYPE_MISMATCH" | "FILE_TOO_LARGE" | null {
  const ext = (fileName.split(".").pop() || "").toLowerCase();
  const expected = UPLOAD_EXT_TO_MIME[ext];
  if (!expected) return "UNSUPPORTED_FILE_TYPE";
  // Browsers sometimes report an empty MIME (notably .tif) — only enforce
  // the cross-check when the browser actually supplied a type.
  if (mimeType && mimeType !== expected) return "FILE_TYPE_MISMATCH";
  if (fileSize > UPLOAD_MAX_BYTES) return "FILE_TOO_LARGE";
  return null;
}

export function statusTone(status: string): StatusTone {
  switch ((status || "").toUpperCase()) {
    case "APPROVED":
      return "verified";
    case "REVIEW_REQUIRED":
    case "VALIDATION_FAILED":
    case "READY_FOR_APPROVAL":
      return "review";
    case "FAILED":
    case "REJECTED":
      return "failed";
    case "UPLOADED":
    case "PROCESSING":
    case "EXTRACTED":
    case "PENDING":
    case "IN_REVIEW":
      return "processing";
    default:
      return "neutral";
  }
}

/** MockLrmsOut — POST /api/v1/integrations/mock-lrms */
export interface MockLrmsResult {
  integration: string;
  status: string;
  record_id: string;
  received_at: string;
  disclaimer: string;
}

/** Standard error envelope — 10_API_SPECIFICATION §12 */
export interface ApiErrorBody {
  code: string;
  message: string;
  request_id: string;
}

/** Human label for a backend status/verdict code.
 *
 * The backend vocabulary (REVIEW_REQUIRED, READY_FOR_APPROVAL, ...) is the
 * contract and stays untouched on the wire; this is presentation only. An
 * unknown code degrades to sentence case rather than being hidden, so a new
 * backend status can never render as a blank chip.
 */
export function statusLabel(status: string): string {
  const code = (status || "").trim().toUpperCase();
  const LABELS: Record<string, string> = {
    UPLOADED: "Uploaded",
    PREPROCESSING: "Preparing",
    OCR_PROCESSING: "Reading document",
    EXTRACTION: "Extracting",
    VALIDATION: "Checking",
    PROCESSING: "Processing",
    EXTRACTED: "Extracted",
    VALIDATION_FAILED: "Needs attention",
    REVIEW_REQUIRED: "Review required",
    READY_FOR_APPROVAL: "Ready for approval",
    APPROVED: "Approved",
    REJECTED: "Rejected",
    FAILED: "Failed",
    DRAFT: "Draft",
    PENDING: "Pending",
    IN_REVIEW: "In review",
    COMPLETED: "Completed",
    CANCELLED: "Cancelled",
    BLOCKED: "Blocked",
    NOT_CHECKED: "Not checked",
    PASS: "Passed",
    WARNING: "Needs checking",
    FAIL: "Failed check",
    LOW: "Low",
    MEDIUM: "Medium",
    HIGH: "High",
    URGENT: "Urgent",
  };
  if (LABELS[code]) return LABELS[code];
  if (!code) return "";
  const words = code.replace(/_/g, " ").toLowerCase();
  return words.charAt(0).toUpperCase() + words.slice(1);
}
