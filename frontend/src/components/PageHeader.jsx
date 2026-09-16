/** Shared page header — Stitch title + env pill + description + meta strip,
 * plus an optional actions cluster (e.g. workspace Approve/Reject).
 */
export default function PageHeader({ title, env, sub, meta, actions }) {
  return (
    <div className="pagehead">
      <div className="pagehead-row pagehead-split">
        <div className="pagehead-titles">
          <div className="pagehead-row">
            <h1>{title}</h1>
            {env && (
              <span className="pagehead-env">
                <span className="pagehead-env-dot" aria-hidden="true" />
                {env}
              </span>
            )}
          </div>
          {sub && <p className="pagehead-sub">{sub}</p>}
        </div>
        {actions && <div className="pagehead-actions">{actions}</div>}
      </div>
      {meta && <div className="pagehead-meta">{meta}</div>}
    </div>
  );
}
