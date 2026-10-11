import { EmptyState } from "../components/ui";
import { useAppState } from "../state/context";
import { BriefView } from "../components/BriefView";
import { DecisionPanel } from "../components/DecisionPanel";
import { ActionsPanel } from "../components/ActionsPanel";

export { parseActionItems } from "../components/ActionsPanel";

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
    <section aria-labelledby="decide-heading" className="space-y-6">
      <h2 id="decide-heading" className="sr-only">
        Decide
      </h2>
      <BriefView
        brief={result.brief}
        dataQuality={result.data_quality}
        reqId={result.parsed.req_id}
      />
      <DecisionPanel />
      <ActionsPanel />
    </section>
  );
}
