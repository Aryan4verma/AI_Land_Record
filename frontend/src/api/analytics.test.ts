/**
 * Analytics metric tests. Node environment, pure functions — asserts honest
 * math over backend aggregates: pass rate excludes unevaluated checks,
 * latency averages only completed jobs, every empty input yields null
 * (rendered as an empty state, never a zero-as-measurement).
 */
import { describe, expect, it } from "vitest";

const {
  averageJobDuration,
  formatDuration,
  formatPercent,
  reviewShare,
  sumCounts,
  validationPassRate,
} = await import("../components/analytics.js");

describe("analytics metrics (real aggregates only)", () => {
  it("sums status maps, tolerating missing input", () => {
    expect(sumCounts({ A: 2, B: 3 })).toBe(5);
    expect(sumCounts({})).toBe(0);
    expect(sumCounts(null)).toBe(0);
  });

  it("pass rate counts evaluated checks, excluding NOT_CHECKED", () => {
    expect(validationPassRate({ PASS: 8, WARNING: 1, FAIL: 1, NOT_CHECKED: 50 })).toBeCloseTo(0.8, 5);
    expect(validationPassRate({ NOT_CHECKED: 5 })).toBeNull();
    expect(validationPassRate({})).toBeNull();
  });

  it("latency averages completed jobs only, null when none", () => {
    const jobs = [
      { started_at: "2026-09-05T12:00:00Z", completed_at: "2026-09-05T12:01:00Z" },
      { started_at: "2026-09-05T12:00:00Z", completed_at: "2026-09-05T12:03:00Z" },
      { started_at: "2026-09-05T12:00:00Z", completed_at: null },
    ];
    expect(averageJobDuration(jobs)).toEqual({ seconds: 120, count: 2 });
    expect(averageJobDuration([])).toBeNull();
    expect(averageJobDuration([{ started_at: "bad", completed_at: "worse" }])).toBeNull();
  });

  it("review share divides open reviews by records, null when empty", () => {
    expect(reviewShare(2, 8)).toBeCloseTo(0.25, 5);
    expect(reviewShare(0, 0)).toBeNull();
  });

  it("formatters render dashes for null, never fake precision", () => {
    expect(formatDuration(null)).toBe("—");
    expect(formatDuration(45)).toBe("45s");
    expect(formatDuration(192)).toBe("3m 12s");
    expect(formatPercent(null)).toBe("—");
    expect(formatPercent(0.964)).toBe("96%");
  });
});
