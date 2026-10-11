import { TitleNormPanel } from "../components/TitleNormPanel";
import { DataQualityLine } from "../components/DataQualityLine";
import { InternalCandidates } from "../components/InternalCandidates";
import { useAppDispatch, useAppState } from "../state/context";
import { useCallback } from "react";

export function StepSkills() {
  const { result } = useAppState();
  const dispatch = useAppDispatch();

  const handleSelectPerson = useCallback(
    (id: string) => dispatch({ type: "SELECT_PERSON", payload: id }),
    [dispatch],
  );

  if (!result) return null;

  return (
    <section aria-labelledby="step-2-heading" className="space-y-6">
      <h2 id="step-2-heading" className="font-serif text-lg font-semibold text-ink" tabIndex={-1}>
        Role / skill analysis
      </h2>

      <TitleNormPanel titleNormalization={result.parsed.title_normalization} />

      <div id="evidence-section">
        <h3 className="font-serif text-base font-semibold text-ink">
          Skill evidence summary
        </h3>
        <p className="mt-1 mb-3 font-sans text-sm text-muted">
          Click any name to see assessed, certified, and self-reported skill scores.
        </p>
      </div>
      <InternalCandidates
        candidates={result.options.internal_candidates}
        onSelectPerson={handleSelectPerson}
      />

      <DataQualityLine line={result.data_quality.line} />
    </section>
  );
}
