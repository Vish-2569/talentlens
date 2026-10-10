import type { components } from "../api/types";
import { SectionHeader } from "./ui";

type Constraint = components["schemas"]["Constraint"];

interface Props {
  constraints: Constraint[];
  mask: string;
  decisionBoundaries: string[];
}

function formatCostShort(cost: components["schemas"]["ConstraintCost"]): string {
  const parts: string[] = [];
  if (cost.supply_delta != null) parts.push(`+${cost.supply_delta} candidates`);
  if (cost.days_delta != null) {
    const sign = cost.days_delta < 0 ? "" : "+";
    parts.push(`${sign}${cost.days_delta} days`);
  }
  if (cost.rupees_delta_lpa != null) {
    const sign = cost.rupees_delta_lpa < 0 ? "−" : "+";
    parts.push(`${sign}₹${Math.abs(cost.rupees_delta_lpa)}L`);
  }
  return parts.length > 0 ? `(${parts.join(", ")})` : "";
}

export function AssumptionLedger({
  constraints,
  mask,
  decisionBoundaries,
}: Props) {
  return (
    <div className="mt-4 space-y-3">
      <div>
        <SectionHeader as="h4" className="text-xs uppercase tracking-wide text-muted">
          Assumption ledger
        </SectionHeader>
        <ul className="mt-1 flex flex-col gap-0.5" aria-label="Assumption ledger">
          {constraints.map((c, index) => {
            const relaxed = mask[index] === "1";
            const costStr = formatCostShort(c.cost);

            return (
              <li key={c.id} className="font-sans text-xs text-ink">
                {relaxed ? (
                  <span>
                    <span className="font-medium text-amber">Relax:</span>{" "}
                    <span className="line-through">{c.phrase}</span>{" "}
                    → {c.relaxed_value}{" "}
                    {costStr && <span className="text-muted">{costStr}</span>}
                  </span>
                ) : (
                  <span>
                    <span className="font-medium">Keep:</span> {c.phrase}{" "}
                    {costStr && <span className="text-muted">{costStr}</span>}
                  </span>
                )}
              </li>
            );
          })}
        </ul>
      </div>

      {decisionBoundaries.length > 0 && (
        <div>
          <SectionHeader as="h4" className="text-xs uppercase tracking-wide text-muted">
            What would change the answer
          </SectionHeader>
          <ul className="mt-1 flex flex-col gap-0.5">
            {decisionBoundaries.map((text, i) => (
              <li key={i} className="font-sans text-xs text-muted">
                {text}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
