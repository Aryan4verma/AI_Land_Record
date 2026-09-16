/**
 * Audit-trail mapping tests. Node environment, pure functions — asserts
 * backend rows render honestly: known titles, officer/pipeline sourcing,
 * original→updated pairs only when both sides exist, unknown actions pass
 * through verbatim (never hidden or invented).
 */
import { describe, expect, it } from "vitest";

const { describeAuditEvent, eventSource } = await import("../components/audit.js");

const CORRECTION = {
  id: "a1", timestamp: "2026-09-05T12:13:35Z", action: "FIELD_CORRECTED",
  user_id: "39b47d7b-2d8e-4a13-bc97-438503934833",
  old_value: { area: "2.45" }, new_value: { area: "2.50" },
  metadata: { review_id: "t1", field: "area", reason: "OCR misread" },
};

describe("describeAuditEvent (honest row rendering)", () => {
  it("titles known actions and sources officers by actor id", () => {
    const e = describeAuditEvent(CORRECTION);
    expect(e.title).toBe("Field corrected");
    expect(e.source).toBe("Officer");
    expect(e.actor).toBe("39b47d7b…");
    expect(e.description).toBe("Reason: OCR misread");
  });

  it("shows original→updated pairs only when both sides exist", () => {
    const e = describeAuditEvent(CORRECTION);
    expect(e.changes).toEqual([{ label: "area", old: "2.45", neu: "2.50" }]);
    const half = describeAuditEvent({ ...CORRECTION, id: "a2", new_value: null });
    expect(half.changes).toBeNull();
  });

  it("approval carries its fixed description, no legal claims", () => {
    const e = describeAuditEvent({ ...CORRECTION, id: "a3", action: "RECORD_APPROVED", old_value: { status: "READY" }, new_value: { status: "APPROVED" }, metadata: {} });
    expect(e.title).toBe("Record approved");
    expect(e.description).toContain("authorized reviewer");
    expect(e.description.toLowerCase()).not.toContain("ownership");
  });

  it("unknown actions pass through verbatim", () => {
    const e = describeAuditEvent({ ...CORRECTION, id: "a4", action: "SOME_FUTURE_EVENT" });
    expect(e.title).toBe("SOME_FUTURE_EVENT");
  });

  it("pipeline rows without an actor source to Pipeline", () => {
    expect(eventSource({ action: "PROCESSING_COMPLETED", user_id: null })).toBe("Pipeline");
    expect(eventSource({ action: "X", user_id: "u1" })).toBe("Officer");
    expect(eventSource(null)).toBe("System");
  });
});
