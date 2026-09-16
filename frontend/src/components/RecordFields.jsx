import ConfidenceBadge from "./ConfidenceBadge.jsx";
import EvidenceHighlight from "./EvidenceHighlight.jsx";
import StatusBadge from "./StatusBadge.jsx";
import { FIELD_GROUPS, fieldLabel } from "../api/fields";

/** Shared extracted-field renderer — the single field display used by the
 * extraction result and the approved record. Values, confidence, and
 * validation chips are backend data verbatim. Evidence toggles render only
 * when the caller wires them (fields carrying OCR evidence).
 */
export default function RecordFields({ fields, evidenceFor, onToggleEvidence }) {
  const byName = new Map((fields || []).map((f) => [f.field_name, f]));
  return (
    <>
      {FIELD_GROUPS.map((group) => (
        <section key={group.title} className="fieldgroup" aria-label={group.title}>
          <h3 className="fieldgroup-title">{group.title}</h3>
          {group.fields.map((name) => {
            const f = byName.get(name);
            if (!f) return null;
            const hasEvidence = Boolean(
              f.bounding_box !== null && f.bounding_box !== undefined,
            ) || Boolean(f.source_text) || (
              f.source_page !== null && f.source_page !== undefined
            );
            return (
              <div key={name} className="xfield">
                <div className="xfield-head">
                  <span className="xfield-label">{fieldLabel(name)}</span>
                  <span className="xfield-flags">
                    <ConfidenceBadge value={f.confidence} />
                    {f.validation_status && f.validation_status !== "NOT_CHECKED" && (
                      <StatusBadge tone={f.validation_status === "PASS" ? "verified" : "review"}>
                        {f.validation_status}
                      </StatusBadge>
                    )}
                  </span>
                </div>
                <div className="xfield-value">
                  {f.value === null ? <span className="muted">Not found</span> : String(f.value)}
                  {f.extraction_status && f.extraction_status !== "EXTRACTED" && (
                    <span className="muted"> ({f.extraction_status})</span>
                  )}
                </div>
                {hasEvidence && onToggleEvidence && (
                  <button
                    type="button"
                    className="xfield-evidence-btn"
                    onClick={() => onToggleEvidence(evidenceFor === name ? null : name)}
                    aria-expanded={evidenceFor === name}
                  >
                    {evidenceFor === name ? "Hide evidence" : "View evidence"}
                  </button>
                )}
                {evidenceFor === name && <EvidenceHighlight field={f} />}
              </div>
            );
          })}
        </section>
      ))}
    </>
  );
}
