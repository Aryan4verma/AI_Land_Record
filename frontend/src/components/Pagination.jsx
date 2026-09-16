import Button from "./Button.jsx";

/** Shared server-side pagination — Stitch "Showing X of Y • Prev/Next".
 * The parent owns fetching; this only renders state and emits intents.
 */
export default function Pagination({ page, limit, total, disabled, onPrev, onNext }) {
  const start = total === 0 ? 0 : (page - 1) * limit + 1;
  const end = Math.min(page * limit, total);
  const hasPrev = page > 1;
  const hasNext = page * limit < total;
  return (
    <div className="pager">
      <span className="muted">
        Showing <span className="tnum">{start}–{end}</span> of <span className="tnum">{total}</span>
      </span>
      <span className="pager-btns">
        <Button variant="secondary" disabled={disabled || !hasPrev} onClick={onPrev}>Previous</Button>
        <Button variant="secondary" disabled={disabled || !hasNext} onClick={onNext}>Next</Button>
      </span>
    </div>
  );
}
