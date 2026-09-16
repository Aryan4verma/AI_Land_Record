/** Shared labeled input — Stitch §Components.4.
 * Label row is uppercase 12px semibold with an optional mono hint;
 * invalid state swaps the border to failed-ink and shows the error text.
 * `trailing` renders an adornment (e.g. password visibility toggle) inside
 * the input's right edge.
 */
export default function TextInput({
  label,
  hint,
  error,
  note,
  id,
  trailing,
  ...inputProps
}) {
  const inputId = id || (label ? label.toLowerCase().replace(/[^a-z0-9]+/g, "-") : undefined);
  return (
    <div className="field">
      {label && (
        <div className="field-label">
          <label htmlFor={inputId}>{label}</label>
          {hint && <span className="field-hint">{hint}</span>}
        </div>
      )}
      <div className={trailing ? "input-wrap" : undefined}>
        <input
          id={inputId}
          className={error ? "input input-invalid" : "input"}
          aria-invalid={!!error}
          {...inputProps}
        />
        {trailing && <span className="input-trailing">{trailing}</span>}
      </div>
      {error && <p className="field-error">{error}</p>}
      {!error && note && <p className="field-note">{note}</p>}
    </div>
  );
}
