/**
 * Document-processing mapping tests. Node environment, pure function —
 * asserts the Stitch stage list maps honestly to aggregate backend states:
 * no fabricated per-stage events, terminal/failure flags exact.
 */
import { describe, expect, it } from "vitest";

const { processingSteps } = await import("./types.js");

const KEYS = ["uploaded", "preprocessing", "ocr", "normalization", "extraction", "validation", "confidence", "review"];

describe("processingSteps (aggregate backend mapping)", () => {
  it("exposes the eight Stitch stages in order", () => {
    const view = processingSteps("PROCESSING");
    expect(view.steps.map((s) => s.key)).toEqual(KEYS);
  });

  it("UPLOADED: only the upload step is done", () => {
    const view = processingSteps("UPLOADED");
    expect(view.steps[0].state).toBe("done");
    expect(view.steps.slice(1).map((s) => s.state)).toEqual(Array(7).fill("queued"));
    expect(view.terminal).toBe(false);
    expect(view.failed).toBe(false);
  });

  it.each(["PROCESSING", "EXTRACTED"])("%s: pipeline block active, later stages queued", (status) => {
    const view = processingSteps(status);
    expect(view.steps[0].state).toBe("done");
    expect(view.steps.slice(1, 5).map((s) => s.state)).toEqual(Array(4).fill("active"));
    expect(view.steps.slice(5).map((s) => s.state)).toEqual(Array(3).fill("queued"));
    expect(view.terminal).toBe(false);
    expect(view.failed).toBe(false);
  });

  it.each(["REVIEW_REQUIRED", "READY_FOR_APPROVAL", "APPROVED", "REJECTED"])("%s: all done, terminal, not failed", (status) => {
    const view = processingSteps(status);
    expect(view.steps.map((s) => s.state)).toEqual(Array(8).fill("done"));
    expect(view.terminal).toBe(true);
    expect(view.failed).toBe(false);
  });

  it.each(["VALIDATION_FAILED", "FAILED"])("%s: pipeline block failed, terminal and failed", (status) => {
    const view = processingSteps(status);
    expect(view.steps[0].state).toBe("done");
    expect(view.steps.slice(1, 5).map((s) => s.state)).toEqual(Array(4).fill("failed"));
    expect(view.steps.slice(5).map((s) => s.state)).toEqual(Array(3).fill("queued"));
    expect(view.terminal).toBe(true);
    expect(view.failed).toBe(true);
  });

  it("unknown statuses never claim progress (fail-safe default)", () => {
    const view = processingSteps("SOME_FUTURE_STATE");
    expect(view.steps[0].state).toBe("done");
    expect(view.steps.slice(1).map((s) => s.state)).toEqual(Array(7).fill("queued"));
    expect(view.terminal).toBe(false);
    expect(view.failed).toBe(false);
  });
});
