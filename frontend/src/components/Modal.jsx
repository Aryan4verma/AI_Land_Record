import { useEffect, useRef } from "react";
import Button from "./Button.jsx";

/** Shared confirmation dialog. Escape cancels; focus lands on the dialog's
 * primary safe action when opened. Lightweight on purpose — one dialog at
 * a time in this app.
 */
export default function Modal({ title, children, confirmLabel, cancelLabel = "Cancel", onConfirm, onCancel, busy = false, danger = false, confirmDisabled = false }) {
  const dialogRef = useRef(null);

  useEffect(() => {
    function onKey(e) {
      if (e.key === "Escape" && !busy) onCancel();
    }
    window.document.addEventListener("keydown", onKey);
    dialogRef.current?.focus();
    return () => window.document.removeEventListener("keydown", onKey);
  }, [busy, onCancel]);

  return (
    <div className="modal-scrim" onMouseDown={(e) => { if (e.target === e.currentTarget && !busy) onCancel(); }}>
      <div
        ref={dialogRef}
        className="modal"
        role="dialog"
        aria-modal="true"
        aria-label={title}
        tabIndex={-1}
      >
        <h2 className="modal-title">{title}</h2>
        <div className="modal-body">{children}</div>
        <div className="modal-actions">
          <Button variant="secondary" onClick={onCancel} disabled={busy}>{cancelLabel}</Button>
          <Button variant={danger ? "destructive" : "primary"} onClick={onConfirm} disabled={busy || confirmDisabled}>
            {busy ? "Working…" : confirmLabel}
          </Button>
        </div>
      </div>
    </div>
  );
}
