/** Shared human-readable record summary — the friendly face in front of the
 * technical Export JSON download. Every row renders backend data verbatim;
 * rows with null/empty values are omitted (never invented, never zero-filled).
 */
export default function RecordSummary({ rows }) {
  const visible = (rows || []).filter(
    (r) => r && r.value !== null && r.value !== undefined && r.value !== "",
  );
  if (visible.length === 0) return null;
  return (
    <dl className="kv">
      {visible.map((r) => (
        <div key={r.label}>
          <dt>{r.label}</dt>
          <dd>{r.value}</dd>
        </div>
      ))}
    </dl>
  );
}
