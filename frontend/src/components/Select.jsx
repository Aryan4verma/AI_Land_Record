/** Shared labeled select — matches TextInput label treatment and .input look.
 * Native <select> keeps keyboard/AT behavior without a dependency.
 */
export default function Select({ label, hint, error, note, id, children, ...selectProps }) {
  const selectId = id || (label ? label.toLowerCase().replace(/[^a-z0-9]+/g, "-") : undefined);
  return (
    <div className="field">
      {label && (
        <div className="field-label">
          <label htmlFor={selectId}>{label}</label>
          {hint && <span className="field-hint">{hint}</span>}
        </div>
      )}
      <select
        id={selectId}
        className={error ? "input input-invalid" : "input"}
        aria-invalid={!!error}
        {...selectProps}
      >
        {children}
      </select>
      {error && <p className="field-error">{error}</p>}
      {!error && note && <p className="field-note">{note}</p>}
    </div>
  );
}
