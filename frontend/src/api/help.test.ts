/**
 * Help content coverage tests. Node environment — asserts the manual keeps
 * all ten required sections and the four mandatory trust statements. Bodies
 * live in the view; this registry is the contract the view renders from.
 */
import { describe, expect, it } from "vitest";

const { HELP_SECTIONS, TRUST_POINTS } = await import("../components/help.js");

describe("help manual coverage", () => {
  it("covers all ten required sections in workflow order", () => {
    expect(HELP_SECTIONS.map((s) => s.id)).toEqual([
      "getting-started", "upload", "processing", "extraction", "confidence",
      "review", "validation", "approve", "audit", "export",
    ]);
  });

  it("states the four trust principles, including the legal-validity limit", () => {
    expect(TRUST_POINTS).toHaveLength(4);
    const joined = TRUST_POINTS.join(" ");
    expect(joined).toContain("AI assists");
    expect(joined).toContain("Validation identifies issues");
    expect(joined).toContain("Human review provides workflow approval");
    expect(joined).toContain("does not itself establish legal ownership or legal validity");
  });
});
