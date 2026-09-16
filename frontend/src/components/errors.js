/** Central frontend error-to-message mapping. HTTP status decides the
 * user-facing text — never the raw backend code, and never a swapped
 * meaning (403 is permission, never "unavailable"; 404 is not-found, never
 * "permission denied"). Workflow conflicts (409) and validation (422) stay
 * visible as such; backend rules are not duplicated, only surfaced.
 * Request IDs are preserved separately via requestIdOf() for the muted
 * reference line — never as the primary message.
 */
export function friendlyMessage(err) {
  const status = err && err.status;
  if (err && (err.name === "AbortError" || (typeof DOMException !== "undefined" && err instanceof DOMException))) {
    return "";
  }
  if (status === 401) return "Your session has expired. Please sign in again.";
  if (status === 403) return "You don't have permission to perform this action.";
  if (status === 404) return "The requested record could not be found.";
  if (status === 409) return "This action is no longer available because the record has changed.";
  if (status === 422) return "Some information is invalid. Please review the highlighted fields.";
  if (typeof status === "number" && status >= 500) {
    return "The server encountered a problem. Please try again.";
  }
  if (status === undefined || status === null) {
    return "Unable to connect to the server. Please check the connection.";
  }
  const raw = String((err && err.message) || err || "Something went wrong.");
  return raw.replace(/\s*[([]request [^)\]]+[)\]]\s*$/i, "").trim() || "Something went wrong.";
}

/** Backend request ID for the muted developer reference line (if any). */
export function requestIdOf(err) {
  if (!err) return "";
  if (typeof err.requestId === "string") return err.requestId;
  if (err.request_id) return String(err.request_id);
  const m = String((err && err.message) || "").match(/[([]request ([^)\]]+)[)\]]/i);
  return m ? m[1] : "";
}
