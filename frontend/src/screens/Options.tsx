import { lazy, Suspense, useCallback, useState } from "react";
import { EmptyState, SectionHeader } from "../components/ui";
import { DataQualityLine } from "../components/DataQualityLine";
import { RippleComparison } from "../components/RippleComparison";
import { RecommendedMix } from "../components/RecommendedMix";
import { FiveOptionTable } from "../components/FiveOptionTable";
import {
  WeightSliders,
  type RankedOption,
  type RankedMix,
} from "../components/WeightSliders";

const RelocateCard = lazy(() =>
  import("../components/RelocateCard").then((m) => ({ default: m.RelocateCard })),
);
import { MarketCard } from "../components/MarketCard";
import { ContractorCards } from "../components/ContractorCards";
import { SourcingPanel } from "../components/SourcingPanel";
import { InternalCandidates } from "../components/InternalCandidates";
import { useAppState, useAppDispatch } from "../state/context";
import type { components } from "../api/types";

type OptionCard = components["schemas"]["OptionCard"];
type ConstraintKind = components["schemas"]["ConstraintKind"];
type Constraint = components["schemas"]["Constraint"];

function relaxedPhrase(kind: ConstraintKind, constraint: Constraint): string {
  switch (kind) {
    case "location":
      return "any location (including Remote-India)";
    case "years":
      return "experience requirement relaxed";
    case "skill": {
      // constraint.value is e.g. "must know Kubernetes"
      const skillName = constraint.value.replace(/^must know\s+/i, "").trim();
      return `${skillName} treated as nice-to-have`;
    }
    case "budget":
      return "budget at market rate";
    case "deadline":
      return `deadline relaxed (was: ${constraint.phrase})`;
    default:
      return kind;
  }
}

export function describeMaskNote(
  mask: string,
  constraintOrder: ConstraintKind[],
  constraints: Constraint[],
): { assumeText: string; keptText: string | null } {
  const byKind = new Map(constraints.map((c) => [c.kind, c]));
  const relaxed: string[] = [];
  const kept: string[] = [];

  for (let i = 0; i < mask.length; i++) {
    const kind = constraintOrder[i];
    const c = byKind.get(kind);
    if (!c) continue;
    if (mask[i] === "1") {
      relaxed.push(relaxedPhrase(kind, c));
    } else {
      kept.push(c.phrase);
    }
  }

  const assumeText =
    relaxed.length === 0
      ? "the request as written"
      : relaxed.join(", ");
  const keptText = kept.length > 0 ? kept.join(", ") : null;
  return { assumeText, keptText };
}

export function Options() {
  const { result, mask } = useAppState();
  const dispatch = useAppDispatch();
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

  const handleSelectPerson = useCallback(
    (id: string) => dispatch({ type: "SELECT_PERSON", payload: id }),
    [dispatch],
  );

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
    <section aria-labelledby="options-heading" className="space-y-6">
      <h2 id="options-heading" className="sr-only">
        Weigh the options
      </h2>

      <DataQualityLine line={result.data_quality.line} />

      {/* Relaxed mask notice */}
      <p className="font-sans text-xs text-muted" data-testid="mask-notice">
        These options assume: {assumeText}.
        {keptText && <> Kept: {keptText}.</>}
      </p>
      {maskMismatch && (
        <p className="font-sans text-xs text-amber">
          Tab 1&apos;s live panel reflects your current choices; the detailed
          options below use a different constraint set.
        </p>
      )}

      {result.ripple.candidates.length > 0 && (
        <RippleComparison candidates={result.ripple.candidates} />
      )}

      <SectionHeader as="h3">Recommended mix</SectionHeader>
      <RecommendedMix mixes={opts.mixes} />

      <div id="options-section">
        <SectionHeader as="h3">Five options</SectionHeader>
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

      <div id="relocate-section">
        <SectionHeader as="h3">Location alternatives</SectionHeader>
      </div>
      <Suspense fallback={<div className="h-48 animate-pulse rounded bg-surface" />}>
        <RelocateCard rows={opts.relocate_card} />
      </Suspense>

      <div id="market-section">
        <SectionHeader as="h3">Market snapshot</SectionHeader>
      </div>
      <MarketCard data={opts.market_card} />

      <div id="contractor-section">
        <SectionHeader as="h3">Contractors</SectionHeader>
      </div>
      <ContractorCards
        cards={opts.contractor_cards}
        onSelectPerson={handleSelectPerson}
      />

      <SectionHeader as="h3">Sourcing</SectionHeader>
      <SourcingPanel sourcing={opts.sourcing} />

      <div id="evidence-section">
        <SectionHeader as="h3">Skill Evidence</SectionHeader>
        <p className="mt-1 mb-3 font-sans text-sm text-muted">
          Click any name to see assessed, certified, and self-reported skill scores.
        </p>
      </div>
      <InternalCandidates
        candidates={opts.internal_candidates}
        onSelectPerson={handleSelectPerson}
      />
    </section>
  );
}
