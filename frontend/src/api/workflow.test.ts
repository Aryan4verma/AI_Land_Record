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

const sessionStorageStub = memoryStorage();

vi.stubGlobal("sessionStorage", sessionStorageStub);

const {
  clearLastDocumentId,
  createSubmitGuard,
  getLastDocumentId,
  isProcessingTerminal,
  setLastDocumentId,
} = await import("./client.js");

beforeEach(() => {
  sessionStorageStub.clear();
});

// Phase 1C: document workflow reliability — sync double-submit guard.
// React `busy` state updates are async, so two clicks in the same tick both
// pass a flag check; the guard closes that race synchronously.
describe("createSubmitGuard (duplicate-submit protection)", () => {
  it("second acquire while held is rejected", () => {
    const guard = createSubmitGuard();
    expect(guard.tryAcquire()).toBe(true);
    expect(guard.tryAcquire()).toBe(false);
  });

  it("acquire succeeds again after release (finally-block pattern)", () => {
    const guard = createSubmitGuard();
    guard.tryAcquire();
    guard.release();
    expect(guard.tryAcquire()).toBe(true);
  });

  it("guards are independent per action", () => {
    const upload = createSubmitGuard();
    const process = createSubmitGuard();
    upload.tryAcquire();
    expect(process.tryAcquire()).toBe(true);
  });
});

// Phase 1C: polling must stop exactly on backend terminal states and keep
// polling on transient ones; unknown states keep polling (poll cap stops).
describe("isProcessingTerminal (status-poll stop conditions)", () => {
  it.each(["REVIEW_REQUIRED", "READY_FOR_APPROVAL", "VALIDATION_FAILED", "APPROVED", "REJECTED", "FAILED"])(
    "stops polling on terminal state %s",
    (status) => {
      expect(isProcessingTerminal(status)).toBe(true);
    },
  );

  it.each(["UPLOADED", "PROCESSING", "EXTRACTED"])("keeps polling on transient state %s", (status) => {
    expect(isProcessingTerminal(status)).toBe(false);
  });

  it("keeps polling on unknown states (fail-open, poll cap is the backstop)", () => {
    expect(isProcessingTerminal("SOME_FUTURE_STATE")).toBe(false);
  });
});

// Phase 1C: last-document persistence must survive refresh/navigation and
// never fabricate an id (stale ids are cleared on 404 by the view).
describe("last-document persistence (refresh/navigation survival)", () => {
  it("round-trips the document id", () => {
    setLastDocumentId("doc-123");
    expect(getLastDocumentId()).toBe("doc-123");
    clearLastDocumentId();
  });

  it("starts empty and clears cleanly", () => {
    clearLastDocumentId();
    expect(getLastDocumentId()).toBeNull();
  });

  it("ignores empty ids (never persists a fabricated reference)", () => {
    setLastDocumentId("");
    expect(getLastDocumentId()).toBeNull();
  });
});
