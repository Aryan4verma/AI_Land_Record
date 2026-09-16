/** Audit-event presentation mapping. Titles/descriptions derive strictly
 * from backend AuditOut rows (action, old/new values, metadata reason,
 * actor id); unknown actions render their raw code — never hidden, never
 * invented. No secrets ever appear (see backend reviews/schemas docstring).
 */
export const ACTION_TITLES = {
  PROCESSING_STARTED: "Processing started",
  PROCESSING_COMPLETED: "Processing completed",
  PROCESSING_FAILED: "Processing failed",
  REVIEW_CREATED: "Review opened",
  FIELD_CORRECTED: "Field corrected",
  REVIEW_COMPLETED: "Review completed",
  RECORD_APPROVED: "Record approved",
  RECORD_REJECTED: "Record rejected",
};

/** Officer = human actor recorded; everything else is pipeline/system. */
export function eventSource(entry) {
  if (!entry) return "System";
  if (entry.user_id) return "Officer";
  return "Pipeline";
}

function fmtValue(v) {
  if (v === null || v === undefined) return "—";
  return typeof v === "object" ? JSON.stringify(v) : String(v);
}

/**
 * Backend row -> display event {id, timestamp, title, source, actor,
 * description, changes}. `changes` is [{label, old, neu}] only when the row
 * carries both sides — differences are never manufactured.
 */
export function describeAuditEvent(entry) {
  const oldValue = entry.old_value;
  const newValue = entry.new_value;
  const reason = entry.metadata && entry.metadata.reason;
  let changes = null;
  if (
    oldValue !== null && oldValue !== undefined &&
    newValue !== null && newValue !== undefined
  ) {
    const olds = typeof oldValue === "object" && !Array.isArray(oldValue) ? oldValue : { value: oldValue };
    const news = typeof newValue === "object" && !Array.isArray(newValue) ? newValue : { value: newValue };
    const keys = [...new Set([...Object.keys(olds), ...Object.keys(news)])];
    changes = keys.map((k) => ({ label: k, old: fmtValue(olds[k]), neu: fmtValue(news[k]) }));
  }
  let description = "";
  if (entry.action === "FIELD_CORRECTED" && reason) description = `Reason: ${reason}`;
  else if (entry.action === "RECORD_REJECTED" && reason) description = `Reason: ${reason}`;
  else if (entry.action === "RECORD_APPROVED") description = "The authorized reviewer accepted the current record.";
  return {
    id: entry.id,
    timestamp: entry.timestamp,
    title: ACTION_TITLES[entry.action] || entry.action,
    source: eventSource(entry),
    actor: entry.user_id ? `${entry.user_id.slice(0, 8)}…` : "System",
    description,
    changes,
  };
}
