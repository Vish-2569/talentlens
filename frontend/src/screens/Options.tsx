import { useCallback, useState } from "react";
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
import { RelocateCard } from "../components/RelocateCard";
import { MarketCard } from "../components/MarketCard";
import { ContractorCards } from "../components/ContractorCards";
import { SourcingPanel } from "../components/SourcingPanel";
import { InternalCandidates } from "../components/InternalCandidates";
import { useAppState, useAppDispatch } from "../state/context";
import type { components } from "../api/types";

type OptionCard = components["schemas"]["OptionCard"];
type ConstraintKind = components["schemas"]["ConstraintKind"];

const CONSTRAINT_LABELS: Record<string, string> = {
  location: "location",
  years: "years of experience",
  skill: "key skill requirement",
  budget: "budget",
  deadline: "deadline",
};

function describeMask(
  mask: string,
  constraintOrder: ConstraintKind[],
): string {
  const relaxed: string[] = [];
  for (let i = 0; i < mask.length; i++) {
    if (mask[i] === "1") {
      relaxed.push(CONSTRAINT_LABELS[constraintOrder[i]] ?? constraintOrder[i]);
    }
  }
  if (relaxed.length === 0) return "the request as written";
  return `no ${relaxed.join(", no ")} constraint`;
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
  const constraintOrder = result.redline.constraint_order;
  const relaxedMask = opts.relaxed_mask;
  const maskMismatch = mask !== relaxedMask;
  const maskDescription = describeMask(relaxedMask, constraintOrder as ConstraintKind[]);

  return (
    <section aria-labelledby="options-heading" className="space-y-6">
      <h2 id="options-heading" className="sr-only">
        Weigh the options
      </h2>

      <DataQualityLine line={result.data_quality.line} />

      {/* Relaxed mask notice */}
      <p className="font-sans text-xs text-muted">
        These options assume: {maskDescription}.
      </p>
      {maskMismatch && (
        <p className="font-sans text-xs text-amber">
          Tab 1&apos;s live panel reflects your current choices; the detailed
          options below assume: {maskDescription}.
        </p>
      )}

      {result.ripple.candidates.length > 0 && (
        <RippleComparison candidates={result.ripple.candidates} />
      )}

      <SectionHeader as="h3">Recommended mix</SectionHeader>
      <RecommendedMix mixes={opts.mixes} />

      <SectionHeader as="h3">All options</SectionHeader>
      <FiveOptionTable options={opts.five as OptionCard[]} />

      <WeightSliders
        defaultWeights={opts.weights}
        options={opts.five as OptionCard[]}
        mixes={opts.mixes}
        onRerank={handleRerank}
      />

      <SectionHeader as="h3">Location alternatives</SectionHeader>
      <RelocateCard rows={opts.relocate_card} />

      <SectionHeader as="h3">Market snapshot</SectionHeader>
      <MarketCard data={opts.market_card} />

      <SectionHeader as="h3">Contractors</SectionHeader>
      <ContractorCards
        cards={opts.contractor_cards}
        onSelectPerson={handleSelectPerson}
      />

      <SectionHeader as="h3">Sourcing</SectionHeader>
      <SourcingPanel sourcing={opts.sourcing} />

      <SectionHeader as="h3">Internal candidates</SectionHeader>
      <InternalCandidates
        candidates={opts.internal_candidates}
        onSelectPerson={handleSelectPerson}
      />
    </section>
  );
}
