/** Shared pipeline stepper — Stitch stage list. Step states come from the
 * aggregate backend mapping (processingSteps); per-stage timing/events are
 * never rendered because the backend does not expose them.
 */
export default function ProcessingStepper({ steps }) {
  return (
    <ol className="stepper">
      {steps.map((s, i) => (
        <li key={s.key} className={`step step-${s.state}`}>
          <span className="step-marker" aria-hidden="true">
            {s.state === "done" ? (
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
              </svg>
            ) : s.state === "failed" ? (
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <path strokeLinecap="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            ) : s.state === "active" ? (
              <span className="step-pulse" />
            ) : (
              <span className="step-num">{i + 1}</span>
            )}
          </span>
          <span className="step-body">
            <span className="step-label">{s.label}</span>
            <span className="step-state">
              {s.state === "done" && "Done"}
              {s.state === "active" && "In progress"}
              {s.state === "queued" && "Queued"}
              {s.state === "failed" && "Failed"}
            </span>
          </span>
        </li>
      ))}
    </ol>
  );
}
