/**
 * Registration flow tests. Node environment with stubbed browser globals +
 * mocked fetch — asserts client validation messages, the register request
 * shape (no role, no token stored), and server-error mapping inputs.
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

const { registerAccount } = await import("./client.js");
const { loginRoleMatches, mapRegistrationError, validateLoginIdentifier, validateRegistration } = await import("../components/auth.js");

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

const VALID = { name: "Asha", idNumber: "ID-1", email: "a@b.co", password: "password-42", confirm: "password-42" };

describe("role-specific login validation", () => {
  it("requires the current email identifier contract for either access type", () => {
    expect(validateLoginIdentifier("", "officer")).toContain("official email");
    expect(validateLoginIdentifier("not-an-email", "officer")).toContain("valid official email");
    expect(validateLoginIdentifier("", "public")).toContain("read-only account");
    expect(validateLoginIdentifier("not-an-email", "public")).toContain("read-only account");
    expect(validateLoginIdentifier("operator@example.gov", "officer")).toBe("");
    expect(validateLoginIdentifier("citizen@example.com", "public")).toBe("");
  });

  it("accepts only the matching authenticated backend role", () => {
    expect(loginRoleMatches("officer", { role: "operator" })).toBe(true);
    expect(loginRoleMatches("officer", { role: "admin" })).toBe(true);
    expect(loginRoleMatches("officer", { role: "user" })).toBe(false);
    expect(loginRoleMatches("public", { role: "user" })).toBe(true);
    expect(loginRoleMatches("public", { role: "operator" })).toBe(false);
    expect(loginRoleMatches("public", { role: "admin" })).toBe(false);
  });
});

describe("validateRegistration (exact user-facing messages)", () => {
  it("accepts a complete valid form", () => {
    expect(validateRegistration(VALID)).toEqual({});
  });

  it("requires every field", () => {
    const errors = validateRegistration({ name: "  ", idNumber: "", email: "", password: "", confirm: "" });
    expect(errors.name).toBe("Name is required.");
    expect(errors.idNumber).toBe("ID number is required.");
    expect(errors.email).toBe("Enter a valid email address.");
    expect(errors.password).toBe("Password is required.");
    expect(errors.confirm).toBe("Please confirm your password.");
  });

  it("rejects malformed emails", () => {
    expect(validateRegistration({ ...VALID, email: "not-an-email" }).email).toBe("Enter a valid email address.");
  });

  it("enforces the 8-character password minimum", () => {
    expect(validateRegistration({ ...VALID, password: "short7", confirm: "short7" }).password)
      .toBe("Password must be at least 8 characters.");
  });

  it("detects confirmation mismatch", () => {
    expect(validateRegistration({ ...VALID, confirm: "different-42" }).confirm).toBe("Passwords do not match.");
  });
});

describe("registerAccount (real endpoint wiring)", () => {
  it("POSTs name/id/email/password without role or stored token", async () => {
    const seen: { url: string; method: string; body: unknown; auth: unknown }[] = [];
    vi.stubGlobal("fetch", async (url: string, init: RequestInit = {}) => {
      seen.push({
        url: String(url),
        method: (init.method || "GET").toUpperCase(),
        body: init.body ? JSON.parse(String(init.body)) : undefined,
        auth: (init.headers as Record<string, string> | undefined)?.["Authorization"],
      });
      return jsonResponse(201, { id: "u1", name: "Asha", id_number: "ID-1", email: "a@b.co", role: "user", status: "active", created_at: "now" });
    });
    const created = await registerAccount({ name: "Asha", id_number: "ID-1", email: "a@b.co", password: "password-42" });
    expect(created.role).toBe("user");
    expect(seen).toHaveLength(1);
    expect(seen[0].url).toContain("/api/v1/auth/register");
    expect(seen[0].method).toBe("POST");
    expect(seen[0].body).toEqual({ name: "Asha", id_number: "ID-1", email: "a@b.co", password: "password-42" });
    expect(seen[0].body).not.toHaveProperty("role");
    expect(seen[0].auth).toBeUndefined();
    expect(sessionStorageStub.getItem("qa_token")).toBeNull();
  });

  it("surfaces the duplicate-email envelope for the view to map", async () => {
    vi.stubGlobal("fetch", async () =>
      jsonResponse(409, { error: { code: "USER_EXISTS", message: "An account with this email already exists.", request_id: "r1" } }),
    );
    await expect(registerAccount({ name: "A", id_number: "ID-1", email: "a@b.co", password: "password-42" }))
      .rejects.toThrow(/USER_EXISTS/);
  });
});

describe("mapRegistrationError (truthful failure texts)", () => {
  function apiError(code: string, status: number) {
    const err = new Error(`${code}: boom`) as Error & { code: string; status: number };
    err.code = code;
    err.status = status;
    return err;
  }

  it("maps known backend codes to field errors", () => {
    expect(mapRegistrationError(apiError("USER_EXISTS", 409)).fields).toEqual({
      email: "An account with this email already exists.",
    });
    expect(mapRegistrationError(apiError("INVALID_EMAIL", 422)).fields).toEqual({
      email: "Enter a valid email address.",
    });
  });

  it("names a stale backend without the route", () => {
    const mapped = mapRegistrationError(apiError("NOT_FOUND", 404));
    expect(mapped.fields).toEqual({});
    expect(mapped.form).toContain("backend may need to be updated and restarted");
  });

  it("names unreachable backend and server failures distinctly", () => {
    expect(mapRegistrationError(new TypeError("Failed to fetch")).form)
      .toBe("We couldn't reach the authentication service. Please try again.");
    expect(mapRegistrationError(apiError("503", 503)).form)
      .toBe("We couldn't reach the authentication service. Please try again.");
  });

  it("keeps a generic fallback for anything unrecognized", () => {
    expect(mapRegistrationError(apiError("WEIRD", 418)).form)
      .toBe("We couldn't create your account. Please try again.");
  });
});
