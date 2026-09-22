/**
 * Canonical frontend API contract layer — the ONLY place that talks HTTP.
 * Backend is authoritative: paths, methods, field names and shapes mirror
 * 10_API_SPECIFICATION.md and the FastAPI response models exactly.
 * No business logic lives here: no validation, confidence, approval or
 * authorization rules are duplicated from the backend.
 */
import type {
  ApiErrorBody,
  AuditEntry,
  CorrectionIn,
  DashboardProcessing,
  DashboardSummary,
  DashboardValidation,
  Document,
  DocumentExtraction,
  DocumentStatus,
  DocumentUploadResponse,
  DocumentValidation,
  HealthAi,
  LoginRequest,
  MockLrmsResult,
  RecordDetail,
  RecordExport,
  RecordSearchParams,
  RecordSearchResult,
  RegisterRequest,
  RegisterResponse,
  ReviewCreate,
  ReviewDetail,
  ReviewTask,
  TokenResponse,
  User,
} from "./types";

// Production is served by the same FastAPI process as the Vite bundle. Local
// Vite development keeps its existing separate-backend default, while an
// explicit VITE_API_URL remains available for QA and non-standard hosting.
const configuredApiUrl = import.meta.env.VITE_API_URL || "";
const DEFAULT_API_URL = (configuredApiUrl || (import.meta.env.PROD ? "" : "http://127.0.0.1:8000")).replace(/\/$/, "");

/** Backend error with the request_id preserved for traceability. */
export class ApiError extends Error {
  code: string;
  requestId: string;
  status: number;

  constructor(status: number, body: Partial<ApiErrorBody>) {
    const code = body.code || String(status);
    const message = body.message || "Request failed";
    const requestId = body.request_id || "";
    super(requestId ? `${code}: ${message} [request ${requestId}]` : `${code}: ${message}`);
    this.name = "ApiError";
    this.code = code;
    this.requestId = requestId;
    this.status = status;
  }
}

export function getApiUrl(): string {
  return localStorage.getItem("qa_api_url") || DEFAULT_API_URL;
}

export function setApiUrl(url: string): void {
  localStorage.setItem("qa_api_url", url.replace(/\/$/, ""));
}

export function getToken(): string {
  return sessionStorage.getItem("qa_token") || "";
}

export function setToken(token: string): void {
  if (token) sessionStorage.setItem("qa_token", token);
  else sessionStorage.removeItem("qa_token");
}

export function getUser(): User | null {
  try {
    return JSON.parse(sessionStorage.getItem("qa_user") || "null") as User | null;
  } catch {
    return null;
  }
}

export function setUser(user: User | null): void {
  if (user) sessionStorage.setItem("qa_user", JSON.stringify(user));
  else sessionStorage.removeItem("qa_user");
}

/** Last document touched by the upload workflow (restores state across refresh/navigation). */
export function getLastDocumentId(): string | null {
  return sessionStorage.getItem("qa_last_doc_id");
}

export function setLastDocumentId(id: string): void {
  if (id) sessionStorage.setItem("qa_last_doc_id", id);
}

export function clearLastDocumentId(): void {
  sessionStorage.removeItem("qa_last_doc_id");
}

/**
 * Terminal document statuses: polling must stop and results may be loaded.
 * Unknown statuses intentionally return false (keep polling until the poll cap).
 */
const PROCESSING_TERMINAL = new Set([
  "REVIEW_REQUIRED",
  "READY_FOR_APPROVAL",
  "VALIDATION_FAILED",
  "APPROVED",
  "REJECTED",
  "FAILED",
]);

export function isProcessingTerminal(status: string): boolean {
  return PROCESSING_TERMINAL.has(status);
}

/**
 * Synchronous double-submit guard. React state updates are async, so two
 * clicks in the same tick both pass a `busy`-flag check; this ref-held guard
 * closes that race (backend 409 remains the authoritative duplicate-process
 * defense). Call release() in a finally block.
 */
export function createSubmitGuard(): { tryAcquire(): boolean; release(): void } {
  let held = false;
  return {
    tryAcquire(): boolean {
      if (held) return false;
      held = true;
      return true;
    },
    release(): void {
      held = false;
    },
  };
}

export function fmtConfidence(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return Math.round(value * 100) + "%";
}

/** Codes meaning "this session is dead" (vs 403 = alive but unauthorized). */
const SESSION_DEAD_CODES = new Set(["UNAUTHENTICATED", "INVALID_TOKEN", "TOKEN_EXPIRED"]);

type SessionExpiredHandler = () => void;
let sessionExpiredHandler: SessionExpiredHandler | null = null;

/** App shell registers this once to navigate to login on session death. */
export function onSessionExpired(handler: SessionExpiredHandler | null): void {
  sessionExpiredHandler = handler;
}

/** True when a stored token existed before this request. */
function hadSession(): boolean {
  return getToken() !== "";
}

function clearSession(): void {
  setToken("");
  setUser(null);
}

/** Best-effort server logout, then always clear local session. */
export async function logout(): Promise<void> {
  try {
    await request("/api/v1/auth/logout", { method: "POST" });
  } catch {
    // Logout is a stateless acknowledgement; local cleanup must happen anyway.
  }
  clearSession();
}

interface RequestOptions {
  method?: string;
  body?: unknown;
  form?: FormData;
  auth?: boolean;
  /** AbortSignal for cancellation on unmount/navigation. Abort rejections
      propagate raw (DOMException, not ApiError) so callers can ignore them. */
  signal?: AbortSignal;
}

export interface CallOptions {
  signal?: AbortSignal;
}

async function request<T>(path: string, { method = "GET", body, form, auth = true, signal }: RequestOptions = {}): Promise<T> {
  const headers: Record<string, string> = {};
  if (auth) headers["Authorization"] = "Bearer " + getToken();
  let payload: BodyInit | undefined;
  if (form) {
    payload = form;
  } else if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }
  const res = await fetch(getApiUrl() + path, { method, headers, body: payload, signal });
  const data: unknown = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = (data as { error?: Partial<ApiErrorBody> }).error || {};
    const apiError = new ApiError(res.status, err);
    // Dead session with a previously stored token: clear it and let the
    // app shell redirect to login. Only the login endpoint itself is
    // excluded (a 401 there means bad credentials and must stay a form
    // error, not a redirect). Never fires for 403s (valid session,
    // insufficient role), and never when no token was stored.
    if (
      res.status === 401 &&
      hadSession() &&
      SESSION_DEAD_CODES.has(apiError.code) &&
      path !== "/api/v1/auth/login" &&
      sessionExpiredHandler
    ) {
      clearSession();
      sessionExpiredHandler();
    }
    throw apiError;
  }
  return data as T;
}

/** Fetch a privately rendered document page without treating the image body as JSON. */
async function requestBlob(path: string, { auth = true, signal }: RequestOptions = {}): Promise<Blob> {
  const headers: Record<string, string> = {};
  if (auth) headers["Authorization"] = "Bearer " + getToken();
  const res = await fetch(getApiUrl() + path, { method: "GET", headers, signal });
  if (!res.ok) {
    const data: unknown = await res.json().catch(() => ({}));
    const err = (data as { error?: Partial<ApiErrorBody> }).error || {};
    const apiError = new ApiError(res.status, err);
    if (
      res.status === 401 &&
      hadSession() &&
      SESSION_DEAD_CODES.has(apiError.code) &&
      sessionExpiredHandler
    ) {
      clearSession();
      sessionExpiredHandler();
    }
    throw apiError;
  }
  return res.blob();
}

/* ---- auth ---- */

export function login(credentials: LoginRequest): Promise<TokenResponse> {
  return request<TokenResponse>("/api/v1/auth/login", { method: "POST", body: credentials, auth: false });
}

export function registerAccount(input: RegisterRequest): Promise<RegisterResponse> {
  return request<RegisterResponse>("/api/v1/auth/register", { method: "POST", body: input, auth: false });
}

export function getMe(): Promise<User> {
  return request<User>("/api/v1/auth/me");
}

/* ---- documents ---- */

export interface UploadMeta {
  documentType?: string;
  language?: string;
}

export function uploadDocument(file: File, meta?: UploadMeta, opts?: CallOptions): Promise<DocumentUploadResponse> {
  const form = new FormData();
  form.append("file", file);
  if (meta?.documentType) form.append("document_type", meta.documentType);
  if (meta?.language) form.append("language", meta.language);
  return request<DocumentUploadResponse>("/api/v1/documents", { method: "POST", form, ...(opts || {}) });
}

export function getDocument(documentId: string, opts?: CallOptions): Promise<Document> {
  return request<Document>(`/api/v1/documents/${documentId}`, opts);
}

export function getDocumentStatus(documentId: string, opts?: CallOptions): Promise<DocumentStatus> {
  return request<DocumentStatus>(`/api/v1/documents/${documentId}/status`, opts);
}

export function getDocumentPage(documentId: string, pageNumber: number, opts?: CallOptions): Promise<Blob> {
  return requestBlob(`/api/v1/documents/${documentId}/pages/${pageNumber}`, opts);
}

/** Start processing. `mode` selects the OCR/extraction source only — every
 *  stage after that is identical. Omitted means live, so existing callers
 *  keep their exact previous behaviour. */
export function startProcessing(
  documentId: string,
  mode: "live" | "demo" = "live",
): Promise<{ job_id: string; status: string }> {
  const query = mode === "demo" ? "?mode=demo" : "";
  return request(`/api/v1/documents/${documentId}/process${query}`, { method: "POST" });
}

export function getExtraction(documentId: string, opts?: CallOptions): Promise<DocumentExtraction> {
  return request<DocumentExtraction>(`/api/v1/documents/${documentId}/extraction`, opts);
}

export function getDocumentValidation(documentId: string, opts?: CallOptions): Promise<DocumentValidation> {
  return request<DocumentValidation>(`/api/v1/documents/${documentId}/validation`, opts);
}

/* ---- records ---- */

export function searchRecords(params: RecordSearchParams, opts?: CallOptions): Promise<RecordSearchResult> {
  const query = new URLSearchParams();
  if (params.page !== undefined) query.set("page", String(params.page));
  if (params.limit !== undefined) query.set("limit", String(params.limit));
  for (const key of ["owner", "survey_number", "khasra_number", "village", "tehsil", "district", "status"] as const) {
    const value = params[key];
    if (value) query.set(key, value);
  }
  return request<RecordSearchResult>(`/api/v1/records?${query}`, opts);
}

export function getRecord(recordId: string, opts?: CallOptions): Promise<RecordDetail> {
  return request<RecordDetail>(`/api/v1/records/${recordId}`, opts);
}

export function exportRecord(recordId: string): Promise<RecordExport> {
  return request<RecordExport>(`/api/v1/records/${recordId}/export`);
}

export function getRecordAudit(recordId: string, opts?: CallOptions): Promise<AuditEntry[]> {
  return request<AuditEntry[]>(`/api/v1/records/${recordId}/audit`, opts);
}

/* ---- reviews ---- */

export function listReviews(status: "PENDING" | "IN_REVIEW" | "COMPLETED" | "CANCELLED", opts?: CallOptions): Promise<ReviewTask[]> {
  return request<ReviewTask[]>(`/api/v1/reviews?status=${status}`, opts);
}

export function createReview(input: ReviewCreate): Promise<ReviewTask> {
  return request<ReviewTask>("/api/v1/reviews", { method: "POST", body: input });
}

export function getReview(reviewId: string, opts?: CallOptions): Promise<ReviewDetail> {
  return request<ReviewDetail>(`/api/v1/reviews/${reviewId}`, opts);
}

export function correctField(reviewId: string, field: string, correction: CorrectionIn): Promise<ReviewDetail> {
  return request<ReviewDetail>(`/api/v1/reviews/${reviewId}/fields/${field}`, {
    method: "PATCH",
    body: correction,
  });
}

export function completeReview(reviewId: string): Promise<ReviewTask> {
  return request<ReviewTask>(`/api/v1/reviews/${reviewId}/complete`, { method: "POST" });
}

export function approveRecord(recordId: string, reason?: string): Promise<{ record_id: string; status: string }> {
  return request(`/api/v1/records/${recordId}/approve`, { method: "POST", body: { reason } });
}

export function rejectRecord(recordId: string, reason: string): Promise<{ record_id: string; status: string }> {
  return request(`/api/v1/records/${recordId}/reject`, { method: "POST", body: { reason } });
}

/* ---- dashboard ---- */

export function getDashboardSummary(opts?: CallOptions): Promise<DashboardSummary> {
  return request<DashboardSummary>("/api/v1/dashboard/summary", opts);
}

export function getDashboardProcessing(opts?: CallOptions): Promise<DashboardProcessing> {
  return request<DashboardProcessing>("/api/v1/dashboard/processing", opts);
}

export function getDashboardValidation(opts?: CallOptions): Promise<DashboardValidation> {
  return request<DashboardValidation>("/api/v1/dashboard/validation", opts);
}

/* ---- health (public; no secrets — used for the shell status pill) ---- */

export function getHealthAi(opts?: CallOptions): Promise<HealthAi> {
  return request<HealthAi>("/health/ai", opts);
}

/* ---- integration ---- */

export function submitMockLrms(recordId: string): Promise<MockLrmsResult> {
  return request<MockLrmsResult>("/api/v1/integrations/mock-lrms", {
    method: "POST",
    body: { record_id: recordId },
  });
}
