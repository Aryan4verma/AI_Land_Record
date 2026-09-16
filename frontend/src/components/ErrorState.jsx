import Button from "./Button.jsx";

/** Shared error state with retry — user-facing message plus an optional
 * muted backend reference (request ID) for support, never the primary text.
 */
export default function ErrorState({ title = "Something went wrong", message, requestId, onRetry }) {
  return (
    <div className="stateblock" role="alert">
      <span className="stateblock-title">{title}</span>
      {message && <p>{message}</p>}
      {requestId && <p className="muted tnum">Reference: {requestId}</p>}
      {onRetry && <Button variant="secondary" onClick={onRetry}>Retry</Button>}
    </div>
  );
}
