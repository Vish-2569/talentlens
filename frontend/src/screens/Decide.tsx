import { EmptyState } from "../components/ui";
import { useAppState } from "../state/context";

export function Decide() {
  const { result } = useAppState();

  if (!result) {
    return (
      <section aria-labelledby="decide-heading">
        <h2 id="decide-heading" className="sr-only">
          Decide
        </h2>
        <EmptyState
          title="No analysis yet"
          description="Submit a requisition on the first tab."
        />
      </section>
    );
  }

  return (
    <section aria-labelledby="decide-heading">
      <h2 id="decide-heading" className="sr-only">
        Decide
      </h2>
      <p className="font-sans text-sm text-muted">
        Decision screen arrives in Phase F6.
      </p>
    </section>
  );
}
