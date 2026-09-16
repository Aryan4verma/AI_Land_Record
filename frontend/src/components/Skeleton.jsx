/** Shared loading skeleton — block rows matching the surrounding density. */
export default function Skeleton({ lines = 4 }) {
  return (
    <div aria-busy="true" aria-label="Loading">
      {Array.from({ length: lines }, (_, i) => (
        <div key={i} className="skel" style={{ height: "2.25rem", marginBottom: "0.5rem" }} />
      ))}
    </div>
  );
}
