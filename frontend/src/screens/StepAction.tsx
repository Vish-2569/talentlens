import { useAppState } from "../state/context";
import { ActionsPanel } from "../components/ActionsPanel";

export function StepAction() {
  const { result, decision } = useAppState();
  if (!result) return null;

  return (
    <section aria-labelledby="step-9-heading" className="space-y-6">
      <h2 id="step-9-heading" className="font-serif text-lg font-semibold text-ink" tabIndex={-1}>
        Recruiting action
      </h2>

      {!decision && (
        <p className="rounded border border-amber/20 bg-amber/5 px-3 py-2 font-sans text-sm text-amber">
          Pending — record a decision on step 8 first.
        </p>
      )}

      <ActionsPanel />
    </section>
  );
}
