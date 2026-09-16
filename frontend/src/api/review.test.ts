/**
 * Review/approval request-shape tests (Phase 1D). Node environment with
 * stubbed browser globals + mocked fetch — asserts the exact URLs, methods,
 * and bodies the workflow views send, so a drift from the backend contract
 * (wrong field target, wrong body, approval gating bypass) fails here.
 */
import { beforeEach, describe, expect, it, vi } from "vitest";

function memoryStorage() {
  const store = new Map();
  return {
    getItem: (key: string) => (store.has(key) ? store.get(key)! : null),
    setItem: (key: string, value: string) => void store.set(key, String(value)),
    removeItem: (key: string) => void store.delete(key),
    clear: () => store.clear(),
  };
}

const localStorageStub = memoryStorage();
const sessionStorageStub = memoryStorage();

vi.stubGlobal("localStorage", localStorageStub);
vi.stubGlobal("sessionStorage", sessionStorageStub);

const {
  approveRecord,
  completeReview,
  correctField,
  createReview,
  getRecordAudit,
  getReview,
  rejectRecord,
} = await import("./client.js");
const { correctionValue } = await import("./fields.js");
const { isTerminalRecord } = await import("./fields.js");
const { validationVerdict } = await import("./types.js");
const { resultBanner } = await import("./types.js");

function jsonResponse(status: number, body: unknown) {
  return { ok: status >= 200 && status < 300, status, json: async () => body };
}

type SeenRequest = { url: string; method: string; body: unknown };

function mockFetchOnce(response: unknown) {
  const seen: SeenRequest[] = [];
  vi.stubGlobal("fetch", async (url: string, init: RequestInit = {}) => {
    seen.push({
      url: String(url),
      method: (init.method || "GET").toUpperCase(),
      body: init.body ? JSON.parse(String(init.body)) : undefined,
    });
    return jsonResponse(200, response);
  });
  return seen;
}

beforeEach(() => {
  localStorageStub.clear();
  sessionStorageStub.clear();
  vi.unstubAllGlobals();
  vi.stubGlobal("localStorage", localStorageStub);
  vi.stubGlobal("sessionStorage", sessionStorageStub);
});

describe("review workflow request shapes", () => {
  it("correctField PATCHes the selected field with {value, reason}", async () => {
    const seen = mockFetchOnce({ task: {}, verdict: "NEEDS_REVIEW", approval_blocked: true });
    await correctField("task-1", "area", { value: "2.50", reason: "typo in OCR" });
    expect(seen).toHaveLength(1);
    expect(seen[0].url).toContain("/api/v1/reviews/task-1/fields/area");
    expect(seen[0].method).toBe("PATCH");
    expect(seen[0].body).toEqual({ value: "2.50", reason: "typo in OCR" });
  });

  it("completeReview POSTs to the review's complete endpoint with no field body", async () => {
    const seen = mockFetchOnce({ id: "task-1", status: "COMPLETED" });
    await completeReview("task-1");
    expect(seen).toHaveLength(1);
    expect(seen[0].url).toContain("/api/v1/reviews/task-1/complete");
    expect(seen[0].method).toBe("POST");
    expect(seen[0].body).toBeUndefined();
  });

  it("approveRecord POSTs to the record's approve endpoint", async () => {
    const seen = mockFetchOnce({ record_id: "rec-1", status: "APPROVED" });
    await approveRecord("rec-1");
    expect(seen).toHaveLength(1);
    expect(seen[0].url).toContain("/api/v1/records/rec-1/approve");
    expect(seen[0].method).toBe("POST");
  });

  it("rejectRecord POSTs to the record's reject endpoint with the reason", async () => {
    const seen = mockFetchOnce({ record_id: "rec-1", status: "REJECTED" });
    await rejectRecord("rec-1", "wrong village");
    expect(seen[0].url).toContain("/api/v1/records/rec-1/reject");
    expect(seen[0].method).toBe("POST");
    expect(seen[0].body).toEqual({ reason: "wrong village" });
  });

  it("createReview POSTs land_record_id + reason + priority", async () => {
    const seen = mockFetchOnce({ id: "task-9", status: "PENDING" });
    await createReview({ land_record_id: "rec-1", reason: "QA review", priority: "MEDIUM" });
    expect(seen[0].url).toContain("/api/v1/reviews");
    expect(seen[0].method).toBe("POST");
    expect(seen[0].body).toEqual({ land_record_id: "rec-1", reason: "QA review", priority: "MEDIUM" });
  });

  it("getReview GETs the review detail (verdict/approval_blocked/document source)", async () => {
    const seen = mockFetchOnce({ task: {}, verdict: "READY_FOR_APPROVAL", approval_blocked: false });
    const detail = await getReview("task-1");
    expect(seen[0].url).toContain("/api/v1/reviews/task-1");
    expect(seen[0].method).toBe("GET");
    expect(detail.approval_blocked).toBe(false);
  });

  it("getRecordAudit GETs the record audit trail", async () => {
    const seen = mockFetchOnce([]);
    await getRecordAudit("rec-1");
    expect(seen[0].url).toContain("/api/v1/records/rec-1/audit");
    expect(seen[0].method).toBe("GET");
  });

  it("correctionValue maps empty input to null (clear), passes values through", () => {
    expect(correctionValue("")).toBeNull();
    expect(correctionValue("2.50")).toBe("2.50");
    expect(correctionValue("  ")).toBe("  ");
  });

  it("isTerminalRecord gates the read-only approved view", () => {
    expect(isTerminalRecord("APPROVED")).toBe(true);
    expect(isTerminalRecord("REJECTED")).toBe(true);
    expect(isTerminalRecord("REVIEW_REQUIRED")).toBe(false);
    expect(isTerminalRecord("READY_FOR_APPROVAL")).toBe(false);
    expect(isTerminalRecord("")).toBe(false);
  });

  it("validationVerdict maps backend verdicts to human results", () => {
    expect(validationVerdict("READY_FOR_APPROVAL")).toEqual({ label: "Ready", tone: "verified" });
    expect(validationVerdict("REVIEW_REQUIRED")).toEqual({ label: "Review required", tone: "review" });
    expect(validationVerdict("BLOCKED")).toEqual({ label: "Blocked", tone: "failed" });
    expect(validationVerdict("VALIDATION_FAILED")).toEqual({ label: "Blocked", tone: "failed" });
  });

  it("validationVerdict renders unknown verdicts verbatim, never guessed", () => {
    expect(validationVerdict("SOME_FUTURE_VERDICT")).toEqual({ label: "SOME_FUTURE_VERDICT", tone: "neutral" });
  });

  it("resultBanner maps backend states to green/amber/red display", () => {
    expect(resultBanner("FAILED", "REVIEW_REQUIRED").tone).toBe("error");
    expect(resultBanner("VALIDATION_FAILED", null).tone).toBe("error");
    expect(resultBanner("READY_FOR_APPROVAL", "BLOCKED").tone).toBe("error");
    expect(resultBanner("READY_FOR_APPROVAL", "READY_FOR_APPROVAL").tone).toBe("success");
    expect(resultBanner("READY_FOR_APPROVAL", "REVIEW_REQUIRED").tone).toBe("info");
    expect(resultBanner("REVIEW_REQUIRED", "REVIEW_REQUIRED").tone).toBe("info");
    expect(resultBanner("PROCESSING", null).tone).toBe("info");
  });

  it("resultBanner never claims ready without backend backing", () => {
    expect(resultBanner("READY_FOR_APPROVAL", null).tone).toBe("success");
    expect(resultBanner("PROCESSING", "READY_FOR_APPROVAL").tone).not.toBe("success");
    expect(resultBanner("", "").title).toBe("Processing");
  });
});
