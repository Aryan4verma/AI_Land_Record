/** Role affordance helpers. These decide what the UI OFFERS; the backend
 * decides what is allowed. Tested so a future role rename cannot silently
 * hand read-only users operator controls (or lock operators out).
 */
import { describe, expect, it } from "vitest";
import { isOperator, isReadOnly } from "../components/roles.js";

describe("isOperator", () => {
  it("accepts operator and the internal admin rank", () => {
    expect(isOperator({ role: "operator" })).toBe(true);
    expect(isOperator({ role: "admin" })).toBe(true);
  });

  it("rejects the read-only role", () => {
    expect(isOperator({ role: "user" })).toBe(false);
  });

  it("rejects the retired verifier role rather than guessing", () => {
    expect(isOperator({ role: "verifier" })).toBe(false);
  });

  it("normalizes case and whitespace like the backend does", () => {
    expect(isOperator({ role: "  OPERATOR " })).toBe(true);
    expect(isOperator({ role: "Admin" })).toBe(true);
  });

  it("fails closed on missing or malformed input", () => {
    expect(isOperator(null)).toBe(false);
    expect(isOperator(undefined)).toBe(false);
    expect(isOperator({})).toBe(false);
    expect(isOperator({ role: 42 })).toBe(false);
    expect(isOperator({ role: "" })).toBe(false);
  });
});

describe("isReadOnly", () => {
  it("is true only for a signed-in non-operator", () => {
    expect(isReadOnly({ role: "user" })).toBe(true);
    expect(isReadOnly({ role: "operator" })).toBe(false);
    expect(isReadOnly({ role: "admin" })).toBe(false);
  });

  it("is false when nobody is signed in", () => {
    expect(isReadOnly(null)).toBe(false);
  });
});
