/** Shared empty state — used wherever the backend legitimately has no rows
 * (never a substitute for invented data).
 */
export default function EmptyState({ title, children }) {
  return (
    <div className="stateblock">
      <span className="stateblock-title">{title}</span>
      {children && <p>{children}</p>}
    </div>
  );
}
