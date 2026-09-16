/** Shared metric tile.
 *
 * Values and sub-text are caller-formatted from real backend aggregates and
 * are never computed or invented here.
 *
 * `tone` marks a metric that represents outstanding work ("review", "failed")
 * so an operator's eye lands on what needs attention first. Tone changes a
 * thin accent rule and the value colour only — never the whole card — so the
 * strip still reads as one calm row rather than a traffic-light panel.
 *
 * `href` turns the tile into the route that acts on the number. A count of
 * pending work should be the way you reach that work.
 */
export default function StatCard({ label, value, sub, tone = "neutral", href, hint }) {
  const body = (
    <>
      <span className="stat-label">{label}</span>
      <span className="stat-value">{value}</span>
      {sub && <span className="stat-sub">{sub}</span>}
    </>
  );

  const className = `stat stat-${tone}${href ? " stat-link" : ""}`;

  if (href) {
    return (
      <a className={className} href={href} title={hint || undefined}>
        {body}
        <span className="stat-go" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
          </svg>
        </span>
      </a>
    );
  }
  return <div className={className}>{body}</div>;
}
