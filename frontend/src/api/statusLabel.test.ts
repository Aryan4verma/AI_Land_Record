/** Human status labels. The backend vocabulary is the contract and must not
 * change; this maps it to language an operator can read. An unknown code must
 * degrade gracefully rather than render an empty chip.
 */
import { describe, expect, it } from "vitest";
import { statusLabel, statusTone } from "./types";

describe("statusLabel", () => {
  it("translates the workflow codes an operator actually sees", () => {
    expect(statusLabel("REVIEW_REQUIRED")).toBe("Review required");
    expect(statusLabel("READY_FOR_APPROVAL")).toBe("Ready for approval");
    expect(statusLabel("VALIDATION_FAILED")).toBe("Needs attention");
    expect(statusLabel("APPROVED")).toBe("Approved");
    expect(statusLabel("REJECTED")).toBe("Rejected");
    expect(statusLabel("IN_REVIEW")).toBe("In review");
  });

  it("never leaks an underscored code to the interface", () => {
    for (const code of ["REVIEW_REQUIRED", "READY_FOR_APPROVAL", "VALIDATION_FAILED",
                        "OCR_PROCESSING", "NOT_CHECKED", "IN_REVIEW"]) {
      expect(statusLabel(code)).not.toContain("_");
    }
  });

  it("degrades an unknown code to sentence case instead of blanking it", () => {
    expect(statusLabel("SOME_NEW_STATE")).toBe("Some new state");
  });

  it("is case and whitespace tolerant", () => {
    expect(statusLabel("  approved ")).toBe("Approved");
  });

  it("returns an empty string only for genuinely empty input", () => {
    expect(statusLabel("")).toBe("");
    // @ts-expect-error exercising the runtime guard
    expect(statusLabel(null)).toBe("");
  });

  it("labels and tones stay independent so colour never carries meaning alone", () => {
    expect(statusTone("APPROVED")).toBe("verified");
    expect(statusLabel("APPROVED")).toBe("Approved");
  });
});
