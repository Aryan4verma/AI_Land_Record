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

  it("VALIDATION_FAILED: only validation is known to have failed", () => {
    const view = processingSteps("VALIDATION_FAILED");
    expect(view.steps.slice(0, 5).map((s) => s.state)).toEqual(Array(5).fill("done"));
    expect(view.steps[5].state).toBe("failed");
    expect(view.steps.slice(6).map((s) => s.state)).toEqual(Array(2).fill("unknown"));
    expect(view.terminal).toBe(true);
    expect(view.failed).toBe(true);
  });

  it("FAILED without a stage code does not infer failures", () => {
    const view = processingSteps("FAILED");
    expect(view.steps[0].state).toBe("done");
    expect(view.steps.slice(1).map((s) => s.state)).toEqual(Array(7).fill("unknown"));
    expect(view.terminal).toBe(true);
    expect(view.failed).toBe(true);
  });

  it("uses a precise OCR error code when the backend provides one", () => {
    const view = processingSteps("FAILED", "OCR_ENGINE_UNAVAILABLE");
    expect(view.steps.slice(0, 2).map((s) => s.state)).toEqual(["done", "done"]);
    expect(view.steps[2].state).toBe("failed");
    expect(view.steps.slice(3).map((s) => s.state)).toEqual(Array(5).fill("unknown"));
  });

  it("unknown statuses never claim progress (fail-safe default)", () => {
    const view = processingSteps("SOME_FUTURE_STATE");
    expect(view.steps[0].state).toBe("done");
    expect(view.steps.slice(1).map((s) => s.state)).toEqual(Array(7).fill("queued"));
    expect(view.terminal).toBe(false);
    expect(view.failed).toBe(false);
  });
});
