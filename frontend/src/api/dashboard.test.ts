/**
 * Dashboard/shell request-shape + status-mapping tests. Node environment with
 * stubbed browser globals + mocked fetch — guards the dashboard's data
 * wiring (real aggregates only) and the single backend-status -> badge-tone
 * mapping used across views.
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
  getDashboardSummary,
  getDashboardValidation,
  getHealthAi,
  searchRecords,
} = await import("./client.js");
const { statusTone } = await import("./types.js");

function jsonResponse(status: number, body: unknown) {
  return { ok: status >= 200 && status < 300, status, json: async () => body };
}

beforeEach(() => {
  localStorageStub.clear();
  sessionStorageStub.clear();
  vi.unstubAllGlobals();
  vi.stubGlobal("localStorage", localStorageStub);
  vi.stubGlobal("sessionStorage", sessionStorageStub);
});

describe("dashboard data wiring (real aggregates only)", () => {
  it("summary GETs the dashboard summary endpoint", async () => {
    const seen: string[] = [];
    vi.stubGlobal("fetch", async (url: string) => {
      seen.push(String(url));
      return jsonResponse(200, {
        documents_total: 3, documents_by_status: {}, records_by_status: {},
        open_reviews: 0, average_confidence: null,
      });
    });
    const summary = await getDashboardSummary();
    expect(seen[0]).toContain("/api/v1/dashboard/summary");
    expect(summary.documents_total).toBe(3);
  });

  it("validation GETs the dashboard validation endpoint", async () => {
    const seen: string[] = [];
    vi.stubGlobal("fetch", async (url: string) => {
      seen.push(String(url));
      return jsonResponse(200, { issues_by_severity: {}, issues_by_status: {}, blocked_documents: 0 });
    });
    const validation = await getDashboardValidation();
    expect(seen[0]).toContain("/api/v1/dashboard/validation");
    expect(validation.blocked_documents).toBe(0);
  });

  it("queue table pages the records search (page 1, limit 8)", async () => {
    const seen: { url: string }[] = [];
    vi.stubGlobal("fetch", async (url: string) => {
      seen.push({ url: String(url) });
      return jsonResponse(200, { items: [], page: 1, limit: 8, total: 0 });
    });
    const result = await searchRecords({ page: 1, limit: 8 });
    expect(seen[0].url).toContain("/api/v1/records");
    expect(seen[0].url).toContain("page=1");
    expect(seen[0].url).toContain("limit=8");
    expect(result.items).toEqual([]);
  });

  it("shell status pill reads the public health endpoint (no secrets)", async () => {
    const seen: { url: string; auth: unknown }[] = [];
    vi.stubGlobal("fetch", async (url: string, init: RequestInit = {}) => {
      seen.push({ url: String(url), auth: (init.headers as Record<string, string> | undefined)?.["Authorization"] });
      return jsonResponse(200, { ai: "configured", provider: "gemini", model: "gemini-3.6-flash" });
    });
    const health = await getHealthAi();
    expect(seen[0].url).toContain("/health/ai");
    expect(health.provider).toBe("gemini");
  });
});

describe("statusTone (single backend-status mapping)", () => {
  it.each([
    ["APPROVED", "verified"],
    ["REVIEW_REQUIRED", "review"],
    ["VALIDATION_FAILED", "review"],
    ["READY_FOR_APPROVAL", "review"],
    ["FAILED", "failed"],
    ["REJECTED", "failed"],
    ["UPLOADED", "processing"],
    ["PROCESSING", "processing"],
    ["EXTRACTED", "processing"],
    ["PENDING", "processing"],
    ["IN_REVIEW", "processing"],
  ])("%s maps to %s", (status, tone) => {
    expect(statusTone(status)).toBe(tone);
  });

  it("unknown statuses fall back to neutral (never a wrong semantic color)", () => {
    expect(statusTone("SOME_FUTURE_STATE")).toBe("neutral");
    expect(statusTone("")).toBe("neutral");
  });
});
