/** Shared data table — Stitch §Components.5 styling; headers + rows supplied
 * by the caller from backend data.
 */
export default function DataTable({ columns, children, caption }) {
  return (
    <div className="dtable-scroll">
      <table className="dtable">
        {caption && <caption className="dtable-caption">{caption}</caption>}
        <thead>
          <tr>
            {columns.map((c) => (
              <th key={c} scope="col">{c}</th>
            ))}
          </tr>
        </thead>
        <tbody>{children}</tbody>
      </table>
    </div>
  );
}
