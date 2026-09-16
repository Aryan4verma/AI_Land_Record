/** Review-queue presentation helpers. All pure: filtering/sorting/aging over
 * already-loaded backend tasks. No business rules, no invented data —
 * confidence/issue-type dimensions are absent because the task API exposes
 * neither per-task confidence nor a validation feed.
 */
export const PRIORITY_RANK = { URGENT: 0, HIGH: 1, MEDIUM: 2, LOW: 3 };

/** @param {string} priority */
export function priorityRank(priority) {
  return PRIORITY_RANK[(priority || "").toUpperCase()] ?? PRIORITY_RANK.LOW;
}

/**
 * @param {import("../api/types.js").ReviewTask[]} tasks
 * @param {{ query?: string, status?: string, priority?: string, assignee?: string, me?: string }} filters
 */
export function filterQueue(tasks, { query = "", status = "", priority = "", assignee = "", me = "" }) {
  const q = query.trim().toLowerCase();
  return (tasks || []).filter((t) => {
    if (status && t.status !== status) return false;
    if (priority === "HIGH_PLUS" && !(t.priority === "HIGH" || t.priority === "URGENT")) return false;
    if (priority && priority !== "HIGH_PLUS" && t.priority !== priority) return false;
    if (assignee === "MINE" && t.assigned_to !== me) return false;
    if (assignee === "UNASSIGNED" && t.assigned_to) return false;
    if (q && !`${t.reason || ""} ${t.land_record_id || ""}`.toLowerCase().includes(q)) return false;
    return true;
  });
}

/**
 * @param {import("../api/types.js").ReviewTask[]} tasks
 * @param {string} mode
 */
export function sortQueue(tasks, mode) {
  const rows = [...(tasks || [])];
  if (mode === "OLDEST") rows.sort((a, b) => (a.created_at || "").localeCompare(b.created_at || ""));
  else if (mode === "NEWEST") rows.sort((a, b) => (b.created_at || "").localeCompare(a.created_at || ""));
  else {
    // Statutory priority first, oldest within a tier.
    rows.sort(
      (a, b) => priorityRank(a.priority) - priorityRank(b.priority)
        || (a.created_at || "").localeCompare(b.created_at || ""),
    );
  }
  return rows;
}

/** Mean age in hours over task creation timestamps; null when uncomputable.
 * @param {import("../api/types.js").ReviewTask[]} tasks
 * @param {number} [now]
 */
export function averageAgeHours(tasks, now = Date.now()) {
  const ages = (tasks || [])
    .map((t) => (now - new Date(t.created_at).getTime()) / 3600000)
    .filter((h) => Number.isFinite(h) && h >= 0);
  if (ages.length === 0) return null;
  return ages.reduce((a, b) => a + b, 0) / ages.length;
}
