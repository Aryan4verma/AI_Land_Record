/**
 * Upload wiring tests. Node environment with stubbed browser globals +
 * mocked fetch — asserts the multipart contract (file + supported metadata
 * only), abort-signal forwarding for Cancel, and the client-side pre-check
 * matrix mirroring backend/app/documents validation.
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

const { uploadDocument } = await import("./client.js");
const { UPLOAD_MAX_BYTES, uploadFileCheck } = await import("./types.js");

function jsonResponse(status: number, body: unknown) {
  return { ok: status >= 200 && status < 300, status, json: async () => body };
}

beforeEach(() => {
  localStorageStub.clear();
  sessionStorageStub.clear();
  vi.unstubAllGlobals();
  vi.stubGlobal("localStorage", localStorageStub);
  vi.stubGlobal("sessionStorage", sessionStorageStub);
  vi.stubGlobal("FormData", class {
    parts: Record<string, unknown[]> = {};
    append(key: string, value: unknown) {
      (this.parts[key] ||= []).push(value);
    }
  });
});

describe("uploadDocument multipart contract", () => {
  it("POSTs file + supported metadata to /api/v1/documents", async () => {
    const seen: { url: string; method: string; form: unknown }[] = [];
    vi.stubGlobal("fetch", async (url: string, init: RequestInit = {}) => {
      seen.push({ url: String(url), method: (init.method || "GET").toUpperCase(), form: init.body });
      return jsonResponse(201, { document_id: "doc-1", status: "UPLOADED" });
    });
    const file = new File(["%PDF-1.4"], "record.pdf", { type: "application/pdf" });
    const created = await uploadDocument(file, { documentType: "khata", language: "en" });
    expect(created.document_id).toBe("doc-1");
    expect(seen).toHaveLength(1);
    expect(seen[0].url).toContain("/api/v1/documents");
    expect(seen[0].method).toBe("POST");
    const parts = (seen[0].form as { parts: Record<string, unknown[]> }).parts;
    expect(parts["file"][0]).toBe(file);
    expect(parts["document_type"]).toEqual(["khata"]);
    expect(parts["language"]).toEqual(["en"]);
  });

  it("omits empty metadata (backend treats them as null)", async () => {
    const seen: { form: unknown }[] = [];
    vi.stubGlobal("fetch", async (_url: string, init: RequestInit = {}) => {
      seen.push({ form: init.body });
      return jsonResponse(201, { document_id: "doc-1", status: "UPLOADED" });
    });
    await uploadDocument(new File(["%PDF-1.4"], "r.pdf", { type: "application/pdf" }), {});
    const parts = (seen[0].form as { parts: Record<string, unknown[]> }).parts;
    expect("document_type" in parts).toBe(false);
    expect("language" in parts).toBe(false);
  });

  it("forwards the abort signal so Cancel stops an in-flight upload", async () => {
    const seen: { signal: unknown }[] = [];
    vi.stubGlobal("fetch", async (_url: string, init: RequestInit = {}) => {
      seen.push({ signal: init.signal });
      return jsonResponse(201, { document_id: "doc-1", status: "UPLOADED" });
    });
    const controller = new AbortController();
    await uploadDocument(new File(["%PDF-1.4"], "r.pdf", { type: "application/pdf" }), {}, { signal: controller.signal });
    expect(seen[0].signal).toBe(controller.signal);
  });
});

describe("uploadFileCheck (client pre-check mirror)", () => {
  it("accepts supported types within the limit", () => {
    expect(uploadFileCheck("record.pdf", 100, "application/pdf")).toBeNull();
    expect(uploadFileCheck("scan.tif", UPLOAD_MAX_BYTES, "")).toBeNull();
    expect(uploadFileCheck("photo.JPEG", 100, "image/jpeg")).toBeNull();
  });

  it("rejects unsupported extensions", () => {
    expect(uploadFileCheck("notes.docx", 100, "")).toBe("UNSUPPORTED_FILE_TYPE");
    expect(uploadFileCheck("run.exe", 100, "")).toBe("UNSUPPORTED_FILE_TYPE");
    expect(uploadFileCheck("noext", 100, "")).toBe("UNSUPPORTED_FILE_TYPE");
  });

  it("rejects extension/MIME disagreement when the browser reports a type", () => {
    expect(uploadFileCheck("record.pdf", 100, "image/png")).toBe("FILE_TYPE_MISMATCH");
  });

  it("rejects oversized files at exactly the backend cap", () => {
    expect(uploadFileCheck("big.pdf", UPLOAD_MAX_BYTES + 1, "application/pdf")).toBe("FILE_TOO_LARGE");
  });
});
