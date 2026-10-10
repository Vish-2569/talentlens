import type { components } from "../api/types";
import { Card, Figure } from "./ui";

type MarketCardData = components["schemas"]["MarketCard"];

interface Props {
  data: MarketCardData;
}

export function MarketCard({ data }: Props) {
  return (
    <Card
      header={{
        title: "Market snapshot",
        meaning: `${data.location} · ${data.level}`,
      }}
    >
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <Figure value={String(data.supply)} caption="Matching supply" size="md" />
        <Figure value={String(data.demand)} caption="Active demand" size="md" />
        <Figure value={`${data.ttf_p50}`} unit=" days" caption="TTF P50" size="md" />
        <Figure value={`${data.ttf_p80}`} unit=" days" caption="TTF P80" size="md" />
      </div>
      <div className="mt-3 grid grid-cols-3 gap-4">
        <Figure value={`₹${data.sal_p25}L`} caption="Salary P25" size="md" />
        <Figure value={`₹${data.sal_p50}L`} caption="Salary P50" size="md" />
        <Figure value={`₹${data.sal_p75}L`} caption="Salary P75" size="md" />
      </div>
    </Card>
  );
}
