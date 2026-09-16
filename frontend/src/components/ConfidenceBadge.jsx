import StatusBadge from "./StatusBadge.jsx";
import { confidenceTone } from "../api/types";

/** Shared confidence badge — HIGH ≥90% verified, MEDIUM 70–89% review,
 * LOW <70% failed; null/undefined renders a neutral dash (no measurement,
 * never a fabricated score).
 */
export default function ConfidenceBadge({ value }) {
  if (value === null || value === undefined) {
    return <StatusBadge tone="neutral">—</StatusBadge>;
  }
  const pct = Math.round(value * 100);
  const label = pct >= 90 ? `High ${pct}%` : pct >= 70 ? `Medium ${pct}%` : `Low ${pct}%`;
  return (
    <StatusBadge tone={confidenceTone(value)} mono>
      {label}
    </StatusBadge>
  );
}
