import { useCallback } from "react";
import { RippleComparison } from "../components/RippleComparison";
import { InternalCandidates } from "../components/InternalCandidates";
import { useAppDispatch, useAppState } from "../state/context";

export function StepInternal() {
  const { result } = useAppState();
  const dispatch = useAppDispatch();

  const handleSelectPerson = useCallback(
    (id: string) => dispatch({ type: "SELECT_PERSON", payload: id }),
    [dispatch],
  );

  if (!result) return null;

  return (
    <section aria-labelledby="step-3-heading" className="space-y-6">
      <h2 id="step-3-heading" className="font-serif text-lg font-semibold text-ink" tabIndex={-1}>
        Internal talent
      </h2>

      {result.ripple.candidates.length > 0 && (
        <RippleComparison candidates={result.ripple.candidates} />
      )}

      <InternalCandidates
        candidates={result.options.internal_candidates}
        onSelectPerson={handleSelectPerson}
      />
    </section>
  );
}
