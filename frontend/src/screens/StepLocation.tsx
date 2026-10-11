import { lazy, Suspense } from "react";
import { useAppState } from "../state/context";
import type { components } from "../api/types";
import { describeMaskNote } from "../components/maskNote";

const RelocateCard = lazy(() =>
  import("../components/RelocateCard").then((m) => ({ default: m.RelocateCard })),
);

type ConstraintKind = components["schemas"]["ConstraintKind"];
type Constraint = components["schemas"]["Constraint"];

export function StepLocation() {
  const { result } = useAppState();
  if (!result) return null;

  const constraints = result.redline.constraints as Constraint[];
  const constraintOrder = result.redline.constraint_order as ConstraintKind[];
  const relaxedMask = result.options.relaxed_mask;
  const { assumeText } = describeMaskNote(relaxedMask, constraintOrder, constraints);

  const compSection = result.brief.sections.find((s) => s.key === "compensation");

  return (
    <section aria-labelledby="step-6-heading" className="space-y-6">
      <h2 id="step-6-heading" className="font-serif text-lg font-semibold text-ink" tabIndex={-1}>
        Location and compensation
      </h2>

      <p className="font-sans text-xs text-muted">
        Options assume: {assumeText}.
      </p>

      <Suspense fallback={<div className="h-48 animate-pulse rounded bg-surface" />}>
        <RelocateCard rows={result.options.relocate_card} />
      </Suspense>

      {compSection && (
        <div className="rounded border border-hairline bg-surface p-4">
          <h3 className="font-serif text-sm font-semibold text-ink mb-2">
            Compensation guidance
          </h3>
          <p className="font-sans text-sm text-muted whitespace-pre-line">
            {compSection.markdown}
          </p>
        </div>
      )}
    </section>
  );
}
