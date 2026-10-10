import { EmptyState } from "../components/ui";
import { useAppState } from "../state/context";

const DEMO_SENTENCE =
  "Senior Full Stack Developer, Bengaluru, on-site, 5+ years, must know React, Node.js and Kubernetes, budget ₹28L, need in 30 days.";

export function Challenge() {
  const { result } = useAppState();

  return (
    <section aria-labelledby="challenge-heading" id="challenge-tab">
      <h2 id="challenge-heading" className="sr-only">
        Challenge the request
      </h2>

      <div id="challenge-input" className="mb-6">
        {/* Requisition input — wired in Phase F3 */}
        <p className="mb-2 font-sans text-xs text-muted">
          Demo sentence (F3 will wire the submit):
        </p>
        <blockquote className="rounded-md border border-hairline bg-paper p-3 font-sans text-sm text-ink">
          {DEMO_SENTENCE}
        </blockquote>
      </div>

      {!result && (
        <EmptyState
          title="Submit a requisition to begin"
          description="Enter job requirements above and click Analyse."
        />
      )}
    </section>
  );
}
