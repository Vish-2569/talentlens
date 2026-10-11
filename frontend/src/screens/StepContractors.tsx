import { useCallback } from "react";
import { ContractorCards } from "../components/ContractorCards";
import { useAppDispatch, useAppState } from "../state/context";

export function StepContractors() {
  const { result } = useAppState();
  const dispatch = useAppDispatch();

  const handleSelectPerson = useCallback(
    (id: string) => dispatch({ type: "SELECT_PERSON", payload: id }),
    [dispatch],
  );

  if (!result) return null;

  return (
    <section aria-labelledby="step-4-heading" className="space-y-6">
      <h2 id="step-4-heading" className="font-serif text-lg font-semibold text-ink" tabIndex={-1}>
        Contractor talent
      </h2>

      <ContractorCards
        cards={result.options.contractor_cards}
        onSelectPerson={handleSelectPerson}
      />
    </section>
  );
}
