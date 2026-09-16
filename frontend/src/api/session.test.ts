/**
 * Focused session/auth tests (Phase 1A). Node environment with stubbed
 * browser globals — no DOM, no network, no extra libraries beyond vitest.
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

const { ApiError, getMe, getToken, login, logout, onSessionExpired, setToken, setUser } = await import("./client.js");

function jsonResponse(status: number, body: unknown) {
  return { ok: status >= 200 && status < 300, status, json: async () => body };
}

beforeEach(() => {
  localStorageStub.clear();
  sessionStorageStub.clear();
  onSessionExpired(null);
  vi.unstubAllGlobals();
  vi.stubGlobal("localStorage", localStorageStub);
  vi.stubGlobal("sessionStorage", sessionStorageStub);
});

describe("token store", () => {
  it("round-trips and clears", () => {
    expect(getToken()).toBe("");
    setToken("abc");
    expect(getToken()).toBe("abc");
    setToken("");
    expect(getToken()).toBe("");
  });
});

describe("ApiError", () => {
  it("preserves backend request_id", () => {
    const err = new ApiError(409, { code: "APPROVAL_BLOCKED", message: "blocked", request_id: "req123" });
    expect(err.code).toBe("APPROVAL_BLOCKED");
    expect(err.requestId).toBe("req123");
    expect(err.message).toContain("req123");
  });
});

describe("session-expiry handling", () => {
  it("expired token on a data call clears session and fires the handler once", async () => {
    setToken("stale");
    const seen: string[] = [];
    onSessionExpired(() => void seen.push("fired"));
    vi.stubGlobal("fetch", async () =>
      jsonResponse(401, { error: { code: "TOKEN_EXPIRED", message: "expired", request_id: "r1" } }),
    );
    await expect(getMe()).rejects.toThrow(/TOKEN_EXPIRED/);
    expect(getToken()).toBe("");
    expect(seen).toEqual(["fired"]);
  });

  it("login-endpoint 401 stays a form error (no redirect, session untouched)", async () => {
    setToken("stale");
    let fired = 0;
    onSessionExpired(() => void (fired += 1));
    vi.stubGlobal("fetch", async () =>
      jsonResponse(401, { error: { code: "INVALID_CREDENTIALS", message: "bad", request_id: "r2" } }),
    );
    await expect(login({ email: "a@b.co", password: "wrong" })).rejects.toThrow(/INVALID_CREDENTIALS/);
    expect(fired).toBe(0);
    expect(getToken()).toBe("stale");
  });

  it("401 without a stored token does not fire the handler", async () => {
    let fired = 0;
    onSessionExpired(() => void (fired += 1));
    vi.stubGlobal("fetch", async () =>
      jsonResponse(401, { error: { code: "UNAUTHENTICATED", message: "nope", request_id: "r3" } }),
    );
    await expect(getMe()).rejects.toThrow();
    expect(fired).toBe(0);
  });

  it("403 never triggers session expiry", async () => {
    setToken("good");
    let fired = 0;
    onSessionExpired(() => void (fired += 1));
    vi.stubGlobal("fetch", async () =>
      jsonResponse(403, { error: { code: "INSUFFICIENT_ROLE", message: "no", request_id: "r4" } }),
    );
    await expect(getMe()).rejects.toThrow(/INSUFFICIENT_ROLE/);
    expect(fired).toBe(0);
    expect(getToken()).toBe("good");
  });

  it("logout calls the backend endpoint then clears even on failure", async () => {
    setToken("tok");
    setUser({ id: "1", name: "n", email: "e", role: "operator", status: "active" });
    const calls: string[] = [];
    vi.stubGlobal("fetch", async (url: string, init: { method?: string }) => {
      calls.push(`${init.method} ${url}`);
      return jsonResponse(200, { status: "ok" });
    });
    await logout();
    expect(calls[0]).toContain("POST");
    expect(calls[0]).toContain("/api/v1/auth/logout");
    expect(getToken()).toBe("");

    setToken("tok2");
    vi.stubGlobal("fetch", async () => jsonResponse(500, {}));
    await logout();
    expect(getToken()).toBe("");
  });

  it("login POSTs credentials as JSON to the auth endpoint", async () => {
    const seen: { url: string; method: string; body: unknown }[] = [];
    vi.stubGlobal("fetch", async (url: string, init: RequestInit = {}) => {
      seen.push({
        url: String(url),
        method: (init.method || "GET").toUpperCase(),
        body: init.body ? JSON.parse(String(init.body)) : undefined,
      });
      return jsonResponse(200, { access_token: "t", token_type: "bearer" });
    });
    const data = await login({ email: "officer@example.com", password: "secret" });
    expect(data.access_token).toBe("t");
    expect(seen).toHaveLength(1);
    expect(seen[0].url).toContain("/api/v1/auth/login");
    expect(seen[0].method).toBe("POST");
    expect(seen[0].body).toEqual({ email: "officer@example.com", password: "secret" });
  });

  it("authenticated requests carry the Bearer token; login sends none", async () => {
    const seen: (string | null)[] = [];
    vi.stubGlobal("fetch", async (_url: string, init: { headers?: Record<string, string> }) => {
      seen.push(init.headers?.["Authorization"] ?? null);
      return jsonResponse(200, { access_token: "t", token_type: "bearer" });
    });
    await login({ email: "a@b.co", password: "p" });
    expect(seen[0]).toBeNull(); // helper records missing header as null: no Authorization sent
    setToken("tok");
    vi.stubGlobal("fetch", async (_url: string, init: { headers?: Record<string, string> }) => {
      seen.push(init.headers?.["Authorization"] ?? null);
      return jsonResponse(200, {});
    });
    await getMe();
    expect(seen[1]).toBe("Bearer tok");
  });
});
