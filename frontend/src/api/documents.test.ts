/**
 * Documents repository wiring tests. Node environment with stubbed browser
 * globals + mocked fetch — asserts the list view's server-side search,
 * filter, and pagination parameters, plus the shared confidence bands.
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

const { searchRecords } = await import("./client.js");
const { confidenceTone } = await import("./types.js");

function jsonResponse(status: number, body: unknown) {
  return { ok: status >= 200 && status < 300, status, json: async () => body };
}

function mockSearch(response: unknown) {
  const seen: string[] = [];
  vi.stubGlobal("fetch", async (url: string) => {
    seen.push(String(url));
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

describe("documents search/filter/pagination wiring", () => {
  it("passes holder, survey, status, page, and limit to the search endpoint", async () => {
    const seen = mockSearch({ items: [], page: 1, limit: 20, total: 0 });
    await searchRecords({ page: 1, limit: 20, owner: "Ramesh", survey_number: "145", status: "APPROVED" });
    expect(seen).toHaveLength(1);
    expect(seen[0]).toContain("/api/v1/records");
    expect(seen[0]).toContain("owner=Ramesh");
    expect(seen[0]).toContain("survey_number=145");
    expect(seen[0]).toContain("status=APPROVED");
    expect(seen[0]).toContain("page=1");
    expect(seen[0]).toContain("limit=20");
  });

  it("omits empty filters (unfiltered repository load)", async () => {
    const seen = mockSearch({ items: [], page: 1, limit: 20, total: 0 });
    await searchRecords({ page: 1, limit: 20 });
    expect(seen[0]).not.toContain("owner=");
    expect(seen[0]).not.toContain("status=");
  });

  it("advances pages server-side", async () => {
    const seen = mockSearch({ items: [], page: 3, limit: 20, total: 55 });
    const result = await searchRecords({ page: 3, limit: 20 });
    expect(seen[0]).toContain("page=3");
    expect(result.total).toBe(55);
  });
});

describe("confidenceTone (Stitch §Components.2 bands)", () => {
  it.each([
    [0.99, "verified"],
    [0.9, "verified"],
    [0.83, "review"],
    [0.7, "review"],
    [0.61, "failed"],
    [0, "failed"],
  ])("%s maps to %s", (value, tone) => {
    expect(confidenceTone(value)).toBe(tone);
  });

  it("null/undefined confidence is neutral (never a wrong semantic color)", () => {
    expect(confidenceTone(null)).toBe("neutral");
    expect(confidenceTone(undefined)).toBe("neutral");
  });
});
