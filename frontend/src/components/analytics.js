/** Analytics metric computations over live backend aggregates. Every function
 * returns null when its inputs carry no data — the view renders an honest
 * empty state instead of a zero dressed as a measurement. No accuracy or
 * benchmark figures exist here: evaluation reports are not served by any
 * API and are intentionally never shown.
 */

/** @param {Record<string, number> | null | undefined} map */
export function sumCounts(map) {
  return Object.values(map || {}).reduce((a, b) => a + (Number(b) || 0), 0);
}

/**
 * Share of evaluated validation checks passing. NOT_CHECKED rows were never
 * evaluated and are excluded from both sides; null when nothing evaluated.
 * @param {Record<string, number> | null | undefined} byStatus
 */
export function validationPassRate(byStatus) {
  const rows = byStatus || {};
  const pass = Number(rows.PASS) || 0;
  const denom = ["PASS", "WARNING", "FAIL", "REVIEW_REQUIRED"]
    .reduce((a, k) => a + (Number(rows[k]) || 0), 0);
  if (denom === 0) return null;
  return pass / denom;
}

/**
 * Mean pipeline duration over recent jobs carrying both timestamps.
 * @param {Array<Record<string, unknown>>} jobs
 * @returns {{ seconds: number, count: number } | null}
 */
export function averageJobDuration(jobs) {
  const spans = (jobs || [])
    .map((j) => (Date.parse(j.completed_at) - Date.parse(j.started_at)) / 1000)
    .filter((s) => Number.isFinite(s) && s >= 0);
  if (spans.length === 0) return null;
  return { seconds: spans.reduce((a, b) => a + b, 0) / spans.length, count: spans.length };
}

/** Share of records currently awaiting review; null when no records exist.
 * @param {number} openReviews
 * @param {number} recordsTotal
 */
export function reviewShare(openReviews, recordsTotal) {
  if (!recordsTotal) return null;
  return (Number(openReviews) || 0) / recordsTotal;
}

/** @param {number | null} seconds */
export function formatDuration(seconds) {
  if (seconds === null || seconds === undefined || !Number.isFinite(seconds)) return "—";
  if (seconds < 60) return `${Math.round(seconds)}s`;
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  return `${m}m ${s}s`;
}

/** @param {number | null} fraction */
export function formatPercent(fraction) {
  if (fraction === null || fraction === undefined || !Number.isFinite(fraction)) return "—";
  return `${Math.round(fraction * 100)}%`;
}
