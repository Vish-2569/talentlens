import { EmptyState } from "../components/ui";
import { useAppState } from "../state/context";

export function Options() {
  const { result } = useAppState();

  if (!result) {
    return (
      <section aria-labelledby="options-heading">
        <h2 id="options-heading" className="sr-only">
          Weigh the options
        </h2>
        <EmptyState
          title="No analysis yet"
          description="Submit a requisition on the first tab."
        />
      </section>
    );
  }

  return (
    <section aria-labelledby="options-heading">
      <h2 id="options-heading" className="sr-only">
        Weigh the options
      </h2>
      <p className="font-sans text-sm text-muted">
        Options screens arrive in Phase F3–F5.
      </p>
    </section>
  );
}
