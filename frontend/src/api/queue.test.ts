/**
 * Review-queue helper tests. Node environment, pure functions — asserts
 * client-side filtering/sorting/aging over loaded task rows plus the
 * two-call list wiring (the API filters one status per call).
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

const { listReviews } = await import("./client.js");
const { averageAgeHours, filterQueue, priorityRank, sortQueue } = await import("../components/queue.js");

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

const T1 = { id: "t1", land_record_id: "r1", status: "PENDING", priority: "HIGH", reason: "Low confidence area", created_at: "2026-09-05T10:00:00Z", completed_at: null, assigned_to: null };
const T2 = { id: "t2", land_record_id: "r2", status: "IN_REVIEW", priority: "URGENT", reason: "Possible duplicate", created_at: "2026-09-05T11:00:00Z", completed_at: null, assigned_to: "user-1" };
const T3 = { id: "t3", land_record_id: "r3", status: "PENDING", priority: "LOW", reason: "Routine check", created_at: "2026-09-05T12:00:00Z", completed_at: null, assigned_to: "user-2" };
const ALL = [T1, T2, T3];

describe("queue list wiring (one status per call)", () => {
  it("GETs the reviews endpoint with the requested status", async () => {
    const seen: string[] = [];
    vi.stubGlobal("fetch", async (url: string) => {
      seen.push(String(url));
      return jsonResponse(200, []);
    });
    await listReviews("PENDING");
    await listReviews("IN_REVIEW");
    expect(seen[0]).toContain("/api/v1/reviews");
    expect(seen[0]).toContain("status=PENDING");
    expect(seen[1]).toContain("status=IN_REVIEW");
  });
});

describe("filterQueue", () => {
  it("passes everything through with no filters", () => {
    expect(filterQueue(ALL, {})).toHaveLength(3);
  });

  it("filters by status", () => {
    expect(filterQueue(ALL, { status: "PENDING" }).map((t) => t.id)).toEqual(["t1", "t3"]);
  });

  it("HIGH_PLUS keeps high and urgent only", () => {
    expect(filterQueue(ALL, { priority: "HIGH_PLUS" }).map((t) => t.id)).toEqual(["t1", "t2"]);
  });

  it("assignee filters resolve mine/unassigned without invented names", () => {
    expect(filterQueue(ALL, { assignee: "MINE", me: "user-1" }).map((t) => t.id)).toEqual(["t2"]);
    expect(filterQueue(ALL, { assignee: "UNASSIGNED" }).map((t) => t.id)).toEqual(["t1"]);
  });

  it("query matches reason or record id, case-insensitively", () => {
    expect(filterQueue(ALL, { query: "duplicate" }).map((t) => t.id)).toEqual(["t2"]);
    expect(filterQueue(ALL, { query: "R3" }).map((t) => t.id)).toEqual(["t3"]);
  });
});

describe("sortQueue", () => {
  it("priority puts urgent first, oldest within a tier", () => {
    expect(sortQueue([T3, T1, T2], "PRIORITY").map((t) => t.id)).toEqual(["t2", "t1", "t3"]);
  });

  it("oldest/newest follow creation time", () => {
    expect(sortQueue(ALL, "OLDEST").map((t) => t.id)).toEqual(["t1", "t2", "t3"]);
    expect(sortQueue(ALL, "NEWEST").map((t) => t.id)).toEqual(["t3", "t2", "t1"]);
  });

  it("unknown priorities rank last, never crash", () => {
    expect(priorityRank("BOGUS")).toBe(priorityRank("LOW"));
  });
});

describe("averageAgeHours", () => {
  it("averages creation ages honestly, null when empty", () => {
    const now = new Date("2026-09-05T13:00:00Z").getTime();
    expect(averageAgeHours([T1, T2, T3], now)).toBeCloseTo(2, 5);
    expect(averageAgeHours([], now)).toBeNull();
  });
});
