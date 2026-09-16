/** OCR source-evidence box. Renders only evidence the backend actually
 * returned (source page/text/bounding region); renders nothing at all when
 * the field carries none — evidence is never fabricated.
 */
export default function EvidenceHighlight({ field }) {
  if (!field) return null;
  const rows = [];
  if (field.source_page !== null && field.source_page !== undefined) {
    rows.push(["Source page", String(field.source_page)]);
  }
  if (field.source_text) {
    rows.push(["Source text", field.source_text]);
  }
  if (field.bounding_box !== null && field.bounding_box !== undefined) {
    rows.push(["Bounding region", JSON.stringify(field.bounding_box)]);
  }
  if (rows.length === 0) return null;
  return (
    <div className="evidence" aria-label={`Source evidence for ${field.field_name}`}>
      <div className="evidence-title">Source evidence</div>
      <dl className="kv">
        {rows.map(([k, v]) => (
          <div key={k}><dt>{k}</dt><dd>{v}</dd></div>
        ))}
      </dl>
    </div>
  );
}
