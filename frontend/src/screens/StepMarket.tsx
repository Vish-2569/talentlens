import { MarketCard } from "../components/MarketCard";
import { SourcingPanel } from "../components/SourcingPanel";
import { useAppState } from "../state/context";

export function StepMarket() {
  const { result } = useAppState();
  if (!result) return null;

  return (
    <section aria-labelledby="step-5-heading" className="space-y-6">
      <h2 id="step-5-heading" className="font-serif text-lg font-semibold text-ink" tabIndex={-1}>
        External market
      </h2>

      <MarketCard data={result.options.market_card} />
      <SourcingPanel sourcing={result.options.sourcing} />
    </section>
  );
}
