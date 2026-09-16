import { useState } from "react";
import Button from "./Button.jsx";
import ConfidenceBadge from "./ConfidenceBadge.jsx";
import EvidenceHighlight from "./EvidenceHighlight.jsx";
import StatusBadge from "./StatusBadge.jsx";
import TextInput from "./TextInput.jsx";
import { friendlyMessage } from "./errors.js";
import { fieldLabel } from "../api/fields";

/** One reviewable field — Stitch review row. Read mode shows the
 * authoritative record value plus backend confidence/validation badges and
 * an evidence toggle (only when OCR evidence exists). Edit mode drafts
 * locally; Save resolves through the real correction API via onSave and
 * exits edit mode only on success — drafts survive unrelated reloads
 * because the parent never touches this component's state.
 */
export default function ReviewField({ name, value, confidence, validationStatus, evidence, disabled, onSave }) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState("");
  const [reason, setReason] = useState("");
  const [showEvidence, setShowEvidence] = useState(false);
  const [saving, setSaving] = useState(false);
  const [localError, setLocalError] = useState("");

  function beginEdit() {
    setDraft(value === null || value === undefined ? "" : String(value));
    setReason("");
    setLocalError("");
    setEditing(true);
  }

  function cancel() {
    if (saving) return;
    setEditing(false);
    setLocalError("");
  }

  async function save(e) {
    e.preventDefault();
    if (saving) return;
    if (!reason.trim()) {
      setLocalError("A reason is required for every correction.");
      return;
    }
    setSaving(true);
    setLocalError("");
    try {
      // Empty input means null (clear the value); the parent maps and POSTs.
      await onSave(name, draft, reason.trim());
      setEditing(false);
    } catch (err) {
      setLocalError(friendlyMessage(err));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="rfield">
      <div className="rfield-head">
        <span className="rfield-label">{fieldLabel(name)}</span>
        <span className="xfield-flags">
          <ConfidenceBadge value={confidence} />
          {validationStatus && validationStatus !== "NOT_CHECKED" && (
            <StatusBadge tone={validationStatus === "PASS" ? "verified" : "review"}>
              {validationStatus}
            </StatusBadge>
          )}
        </span>
      </div>
      {!editing ? (
        <>
          <div className="xfield-value">
            {value === null || value === undefined ? <span className="muted">Not found</span> : String(value)}
          </div>
          <div className="rfield-tools">
            {evidence ? (
              <button
                type="button"
                className="xfield-evidence-btn"
                disabled={disabled}
                onClick={() => setShowEvidence((v) => !v)}
                aria-expanded={showEvidence}
              >
                {showEvidence ? "Hide evidence" : "View evidence"}
              </button>
            ) : (
              <span className="muted">No source evidence</span>
            )}
            <button
              type="button"
              className="xfield-evidence-btn"
              disabled={disabled}
              onClick={beginEdit}
            >
              Edit
            </button>
          </div>
          {showEvidence && evidence && <EvidenceHighlight field={evidence} />}
        </>
      ) : (
        <form onSubmit={save}>
          <TextInput
            label="New value"
            hint="Empty clears the value"
            id={`edit-${name}`}
            value={draft}
            disabled={saving}
            onChange={(e) => setDraft(e.target.value)}
          />
          <TextInput
            label="Reason"
            hint="Required"
            id={`reason-${name}`}
            value={reason}
            disabled={saving}
            error={localError}
            placeholder="Why is this correction needed?"
            onChange={(e) => setReason(e.target.value)}
          />
          <div className="rfield-tools">
            <Button type="button" variant="secondary" disabled={saving} onClick={cancel}>Cancel</Button>
            <Button type="submit" variant="primary" disabled={saving || disabled}>
              {saving ? "Saving…" : "Save correction"}
            </Button>
          </div>
        </form>
      )}
    </div>
  );
}
