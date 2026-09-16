/**
 * Central error-mapping tests. Node environment, pure functions — asserts
 * the exact user-facing texts per HTTP status (403 is permission, never
 * "unavailable"; 404 is not-found, never "permission denied"), request-ID
 * preservation separate from the primary message, and safe fallbacks.
 */
import { describe, expect, it } from "vitest";

const { friendlyMessage, requestIdOf } = await import("../components/errors.js");

function apiError(status: number, code = "X", message = "raw backend text", requestId = "") {
  const err = new Error(message + (requestId ? ` [request ${requestId}]` : "")) as Error & {
    status: number;
    code: string;
    requestId: string;
  };
  err.status = status;
  err.code = code;
  err.requestId = requestId;
  return err;
}

describe("friendlyMessage (central status mapping)", () => {
  it("401 is a session message", () => {
    expect(friendlyMessage(apiError(401, "TOKEN_EXPIRED"))).toBe(
      "Your session has expired. Please sign in again.",
    );
  });

  it("403 is permission, never unavailable", () => {
    const text = friendlyMessage(apiError(403, "INSUFFICIENT_ROLE"));
    expect(text).toBe("You don't have permission to perform this action.");
    expect(text.toLowerCase()).not.toContain("unavailable");
  });

  it("404 is not-found, never permission", () => {
    const text = friendlyMessage(apiError(404, "RECORD_NOT_FOUND"));
    expect(text).toBe("The requested record could not be found.");
    expect(text.toLowerCase()).not.toContain("permission");
  });

  it("409 keeps the workflow conflict visible", () => {
    expect(friendlyMessage(apiError(409, "RECORD_FINALIZED"))).toBe(
      "This action is no longer available because the record has changed.",
    );
  });

  it("422 points at the highlighted fields", () => {
    expect(friendlyMessage(apiError(422, "VALIDATION_ERROR"))).toBe(
      "Some information is invalid. Please review the highlighted fields.",
    );
  });

  it("5xx is a server problem", () => {
    expect(friendlyMessage(apiError(500, "X"))).toBe(
      "The server encountered a problem. Please try again.",
    );
    expect(friendlyMessage(apiError(503, "DATABASE_UNAVAILABLE"))).toBe(
      "The server encountered a problem. Please try again.",
    );
  });

  it("network failure (no status) names the connection", () => {
    expect(friendlyMessage(new TypeError("Failed to fetch"))).toBe(
      "Unable to connect to the server. Please check the connection.",
    );
  });

  it("unknown statuses fall back to the backend text without the request suffix", () => {
    expect(friendlyMessage(apiError(418, "TEAPOT", "Short and stout", "abc"))).toBe("Short and stout");
  });

  it("aborts produce no message", () => {
    const abort = new DOMException("aborted", "AbortError");
    expect(friendlyMessage(abort)).toBe("");
  });
});

describe("requestIdOf (debug reference, never primary)", () => {
  it("reads explicit fields first", () => {
    expect(requestIdOf(apiError(500, "X", "m", "req-1"))).toBe("req-1");
    expect(requestIdOf({ request_id: "req-2" })).toBe("req-2");
  });

  it("parses the embedded suffix as a last resort", () => {
    expect(requestIdOf(new Error("boom [request req-3]"))).toBe("req-3");
  });

  it("returns empty when there is nothing to reference", () => {
    expect(requestIdOf(new Error("boom"))).toBe("");
    expect(requestIdOf(null)).toBe("");
  });
});
