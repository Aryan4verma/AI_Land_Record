/**
 * Workspace-settings store tests. Node environment with stubbed browser
 * globals — asserts the local backend-URL setting round-trips, normalizes,
 * and falls back to the build default. (Profile/password/preferences have
 * no backend endpoints and therefore no editable client state to test.)
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

const { getApiUrl, setApiUrl } = await import("./client.js");

beforeEach(() => {
  localStorageStub.clear();
  sessionStorageStub.clear();
  vi.unstubAllGlobals();
  vi.stubGlobal("localStorage", localStorageStub);
  vi.stubGlobal("sessionStorage", sessionStorageStub);
});

describe("backend API URL setting (local workspace setting)", () => {
  it("falls back to the build default when unset", () => {
    expect(getApiUrl()).toBe("http://127.0.0.1:8000");
  });

  it("round-trips a custom URL", () => {
    setApiUrl("http://backend:9000");
    expect(getApiUrl()).toBe("http://backend:9000");
  });

  it("strips a trailing slash so endpoint joins stay valid", () => {
    setApiUrl("http://backend:9000/");
    expect(getApiUrl()).toBe("http://backend:9000");
  });
});
