/** Shared form/page alert — tones map to the Stitch semantic tiers.
 * Tones: error | success | info. Returns null when there is no message.
 */
export default function Alert({ tone = "error", title, children }) {
  if (!children) return null;
  return (
    <div className={`alert alert-${tone}`} role={tone === "error" ? "alert" : "status"}>
      <div>
        {title && <div className="alert-title">{title}</div>}
        <div>{children}</div>
      </div>
    </div>
  );
}
