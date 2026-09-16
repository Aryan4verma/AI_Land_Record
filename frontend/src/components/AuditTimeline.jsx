import { timeAgo } from "./format.js";

/** Shared audit timeline — Stitch event rail. Renders display events from
 * describeAuditEvent: timestamp, title, source chip, actor, description,
 * and original→updated value pairs when the backend row carries both.
 */
export default function AuditTimeline({ events }) {
  return (
    <ol className="timeline">
      {events.map((e) => (
        <li key={e.id} className="tline-event">
          <span className="tline-dot" aria-hidden="true" />
          <div className="tline-body">
            <div className="tline-head">
              <span className="tline-title">{e.title}</span>
              <span className={`tline-source tline-source-${e.source === "Officer" ? "officer" : "pipeline"}`}>
                {e.source}
              </span>
            </div>
            <div className="tline-meta">
              <span className="tnum">{e.timestamp ? new Date(e.timestamp).toLocaleString() : "—"}</span>
              <span>•</span>
              <span>{e.timestamp ? timeAgo(e.timestamp) : ""}</span>
              <span>•</span>
              <span>Actor: {e.actor}</span>
            </div>
            {e.description && <p className="tline-desc">{e.description}</p>}
            {e.changes && (
              <dl className="tline-changes">
                {e.changes.map((c) => (
                  <div key={c.label}>
                    <dt>{c.label}</dt>
                    <dd>
                      <span className="tline-old">{c.old}</span>
                      <span aria-hidden="true"> → </span>
                      <span className="tline-new">{c.neu}</span>
                    </dd>
                  </div>
                ))}
              </dl>
            )}
          </div>
        </li>
      ))}
    </ol>
  );
}
