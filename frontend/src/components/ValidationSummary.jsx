import Alert from "./Alert.jsx";
import StatusBadge from "./StatusBadge.jsx";
import { fieldLabel } from "../api/fields";
import { statusLabel, validationVerdict } from "../api/types";

/** Generic reviewer guidance per severity. Static help text — it never
 * decides pass/fail (the backend already did that).
 */
function recommendedAction(severity) {
  const s = (severity || "").toUpperCase();
  if (s === "ERROR" || s === "CRITICAL") return "Correct the value in review, then re-check.";
  if (s === "WARNING") return "Compare against the source document and correct if needed.";
  return "No action needed.";
}

function severityTone(severity) {
  const s = (severity || "").toUpperCase();
  if (s === "ERROR" || s === "CRITICAL") return "failed";
  if (s === "WARNING") return "review";
  return "neutral";
}

/** Shared validation summary — overall backend verdict plus one plain row
 * per issue (severity, human field name, backend message, recommended
 * action). Rule IDs live in a collapsed technical-details area so they
 * never dominate the UI. `status` may be omitted where the backend retains
 * no verdict (rows only) — the badge is then skipped, never guessed.
 */
export default function ValidationSummary({ status, issues }) {
  const verdict = status ? validationVerdict(status) : null;
  const rows = issues || [];
  return (
    <div>
      <div className="val-overall">
        {verdict && <StatusBadge tone={verdict.tone}>{verdict.label}</StatusBadge>}
        <span className="muted">
          {rows.length === 0
            ? "Every verification check passed."
            : `${rows.length} item${rows.length === 1 ? "" : "s"} need${rows.length === 1 ? "s" : ""} attention.`}
        </span>
      </div>
      {rows.length === 0 && (
        <Alert tone="success" title={statusLabel(status)}>Nothing needs attention on this record.</Alert>
      )}
      {rows.map((issue, i) => (
        <div key={i} className="val-issue">
          <div className="val-issue-head">
            <StatusBadge tone={severityTone(issue.severity)}>{statusLabel(issue.severity)}</StatusBadge>
            <span className="val-issue-field">{issue.field_name ? fieldLabel(issue.field_name) : "Whole record"}</span>
          </div>
          <p className="val-issue-message">{issue.message}</p>
          <p className="muted">Recommended: {recommendedAction(issue.severity)}</p>
          <details className="val-tech">
            <summary>Technical details</summary>
            <div className="tnum">Rule {issue.rule_id} • check status {issue.status}</div>
          </details>
        </div>
      ))}
    </div>
  );
}
