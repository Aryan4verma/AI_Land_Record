/**
 * Extraction-result wiring tests. Node environment — asserts the export
 * action hits the canonical endpoint and the shared field schema covers the
 * 14 data-dictionary fields exactly once (views must never invent fields).
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

const { exportRecord } = await import("./client.js");
const { FIELD_GROUPS, fieldLabel } = await import("./fields.js");

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

describe("export action (canonical backend JSON)", () => {
  it("GETs the record export endpoint", async () => {
    const seen: string[] = [];
    vi.stubGlobal("fetch", async (url: string) => {
      seen.push(String(url));
      return jsonResponse(200, { record: {}, exported_at: "now", format_version: "v1" });
    });
    const payload = await exportRecord("rec-1");
    expect(seen[0]).toContain("/api/v1/records/rec-1/export");
    expect(payload.format_version).toBe("v1");
  });
});

describe("shared field schema (04_DATA_DICTIONARY)", () => {
  const CANONICAL = [
    "owner_name", "father_or_spouse_name", "survey_number", "khasra_number",
    "khata_number", "area", "area_unit", "village", "tehsil", "district",
    "land_classification", "mutation_number", "registration_number", "record_date",
  ];

  it("groups cover the 14 canonical fields exactly once — no invented fields", () => {
    const grouped = FIELD_GROUPS.flatMap((g) => g.fields);
    expect([...grouped].sort()).toEqual([...CANONICAL].sort());
  });

  it("every canonical field has a human label", () => {
    for (const name of CANONICAL) {
      expect(fieldLabel(name)).not.toBe(name);
      expect(fieldLabel(name).length).toBeGreaterThan(0);
    }
  });
});
