import { useCallback, useState } from "react";
import { SectionHeader } from "../components/ui";
import { RecommendedMix } from "../components/RecommendedMix";
import { FiveOptionTable } from "../components/FiveOptionTable";
import {
  WeightSliders,
  type RankedOption,
  type RankedMix,
} from "../components/WeightSliders";
import { useAppState } from "../state/context";
import { describeMaskNote } from "../components/maskNote";
import type { components } from "../api/types";

type OptionCard = components["schemas"]["OptionCard"];
type ConstraintKind = components["schemas"]["ConstraintKind"];
type Constraint = components["schemas"]["Constraint"];

export function StepOptions() {
  const { result, mask } = useAppState();
  const [, setReranked] = useState<{
    options: RankedOption[];
    mixes: RankedMix[];
  } | null>(null);

  const handleRerank = useCallback(
    (options: RankedOption[], mixes: RankedMix[]) => {
      setReranked({ options, mixes });
    },
    [],
  );

  if (!result) return null;

  const opts = result.options;
  const constraints = result.redline.constraints as Constraint[];
  const constraintOrder = result.redline.constraint_order as ConstraintKind[];
  const relaxedMask = opts.relaxed_mask;
  const maskMismatch = mask !== relaxedMask;

  const { assumeText, keptText } = describeMaskNote(
    relaxedMask,
    constraintOrder,
    constraints,
  );

  return (
    <section aria-labelledby="step-7-heading" className="space-y-6">
      <h2 id="step-7-heading" className="font-serif text-lg font-semibold text-ink" tabIndex={-1}>
        Five options
      </h2>

      <p className="font-sans text-xs text-muted" data-testid="mask-notice">
        These options assume: {assumeText}.
        {keptText && <> Kept: {keptText}.</>}
      </p>
      {maskMismatch && (
        <p className="font-sans text-xs text-amber">
          Step 1&apos;s live panel reflects your current choices; the detailed
          options below use a different constraint set.
        </p>
      )}

      <SectionHeader as="h3">Recommended mix</SectionHeader>
      <RecommendedMix mixes={opts.mixes} />

      <div id="options-section">
        <SectionHeader as="h3">Build / Buy / Borrow / Relocate / Automate</SectionHeader>
        <p className="mt-1 mb-3 font-sans text-sm text-muted">
          Every way to fill this seat — scored, side by side.
        </p>
      </div>
      <FiveOptionTable options={opts.five as OptionCard[]} />

      <WeightSliders
        defaultWeights={opts.weights}
        options={opts.five as OptionCard[]}
        mixes={opts.mixes}
        onRerank={handleRerank}
      />
    </section>
  );
}
