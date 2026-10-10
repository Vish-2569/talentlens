import { EmptyState } from "../components/ui";
import { DataQualityLine } from "../components/DataQualityLine";
import { RippleComparison } from "../components/RippleComparison";
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
    <section aria-labelledby="options-heading" className="space-y-6">
      <h2 id="options-heading" className="sr-only">
        Weigh the options
      </h2>

      <DataQualityLine line={result.data_quality.line} />

      {result.ripple.candidates.length > 0 && (
        <RippleComparison candidates={result.ripple.candidates} />
      )}
    </section>
  );
}
