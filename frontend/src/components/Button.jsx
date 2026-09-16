/** Shared Button — Stitch §Components.1.
 * Variants: primary (navy solid) | secondary (white/border) | destructive.
 * Focus ring is always the steel-blue accent; never remove it.
 */
export default function Button({
  variant = "primary",
  type = "button",
  disabled = false,
  fullWidth = false,
  className = "",
  onClick,
  children,
}) {
  const cls = ["btn", `btn-${variant}`, fullWidth ? "btn-full" : "", className].filter(Boolean).join(" ");
  return (
    <button type={type} className={cls} disabled={disabled} onClick={onClick}>
      {children}
    </button>
  );
}
