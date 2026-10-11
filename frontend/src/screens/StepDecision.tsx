import { useAppState } from "../state/context";
import { BriefView } from "../components/BriefView";
import { DecisionPanel } from "../components/DecisionPanel";

export function StepDecision() {
  const { result, decision } = useAppState();
  if (!result) return null;

  return (
    <section aria-labelledby="step-8-heading" className="space-y-6">
      <h2 id="step-8-heading" className="font-serif text-lg font-semibold text-ink" tabIndex={-1}>
        Human decision
      </h2>

      {!decision && (
        <p className="rounded border border-amber/20 bg-amber/5 px-3 py-2 font-sans text-sm text-amber">
          Pending — review the brief and record your decision below.
        </p>
      )}

      <BriefView
        brief={result.brief}
        dataQuality={result.data_quality}
        reqId={result.parsed.req_id}
      />
      <DecisionPanel />
    </section>
  );
}
