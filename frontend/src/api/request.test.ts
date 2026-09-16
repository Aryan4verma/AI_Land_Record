/**
 * Request plumbing tests (Phase 1B): signal forwarding, abort semantics,
 * and the unchanged happy path. No DOM, no network.
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

const { ApiError, getRecord } = await import("./client.js");

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

describe("request plumbing", () => {
  it("forwards AbortSignal to fetch", async () => {
    let seenSignal: AbortSignal | null | undefined;
    vi.stubGlobal(
      "fetch",
      async (_url: string, init: { signal?: AbortSignal }) => {
        seenSignal = init.signal ?? null;
        return jsonResponse(200, { record: {}, extracted_fields: [], validation: [], document: null });
      },
    );
    const controller = new AbortController();
    await getRecord("some-id", { signal: controller.signal });
    expect(seenSignal).toBe(controller.signal);
  });

  it("lets aborts propagate raw so callers can ignore them silently", async () => {
    const controller = new AbortController();
    vi.stubGlobal("fetch", async () => {
      controller.abort();
      const err = new DOMException("aborted", "AbortError");
      throw err;
    });
    await expect(getRecord("some-id", { signal: controller.signal })).rejects.toMatchObject({
      name: "AbortError",
    });
    try {
      await getRecord("some-id", { signal: controller.signal });
      expect.unreachable("should have thrown");
    } catch (err) {
      expect(err).not.toBeInstanceOf(ApiError);
    }
  });

  it("works without a signal (backward compatible)", async () => {
    vi.stubGlobal("fetch", async () =>
      jsonResponse(200, { record: { id: "r1" }, extracted_fields: [], validation: [], document: null }),
    );
    const detail = await getRecord("r1");
    expect(detail.record.id).toBe("r1");
  });

  it("still wraps HTTP errors in ApiError with request_id", async () => {
    vi.stubGlobal("fetch", async () =>
      jsonResponse(404, { error: { code: "RECORD_NOT_FOUND", message: "gone", request_id: "abc" } }),
    );
    try {
      await getRecord("missing");
      expect.unreachable("should have thrown");
    } catch (err) {
      expect(err).toBeInstanceOf(ApiError);
      expect((err as { requestId?: string }).requestId).toBe("abc");
    }
  });
});
