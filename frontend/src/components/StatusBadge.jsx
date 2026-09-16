/** Shared status chip — Stitch §Components.2/5.
 * Tones: verified | review | failed | processing | neutral.
 * Always pairs color with text (and usually a leading dot) — never color alone.
 * Map backend statuses at the call site, e.g. APPROVED->verified,
 * REVIEW_REQUIRED/VALIDATION_FAILED->review, FAILED/REJECTED->failed,
 * UPLOADED/PROCESSING/EXTRACTED->processing.
 */
export default function StatusBadge({ tone = "neutral", dot = true, mono = false, children }) {
  return (
    <span className={`statusbadge statusbadge-${tone}${mono ? " tnum" : ""}`}>
      {dot && <span className="statusbadge-dot" aria-hidden="true" />}
      {children}
    </span>
  );
}
