import EmptyState from "../components/EmptyState.jsx";
import PageHeader from "../components/PageHeader.jsx";

/** Honest stand-in for sidebar routes whose screens land in later prompts.
 * Renders an empty state — never placeholder business data.
 */
export default function Placeholder({ title, note, children }) {
  return (
    <div>
      <PageHeader title={title} />
      <div className="panel vstack">
        <EmptyState title={`${title} is coming next`}>
          {note || "This section arrives in a later milestone. The sidebar stays complete so the shell matches the design."}
        </EmptyState>
        {children}
      </div>
    </div>
  );
}
