import type { components } from "../api/types";
import { Card, Figure } from "./ui";

type MixOption = components["schemas"]["MixOption"];

interface Props {
  mixes: MixOption[];
}

export function RecommendedMix({ mixes }: Props) {
  if (mixes.length === 0) return null;
  const top = mixes[0];

  return (
    <Card header={{ title: "Recommended mix", meaning: top.name }}>
      <div className="flex flex-wrap gap-4">
        <Figure
          value={String(top.score)}
          unit="/100"
          caption="Fit score"
          size="lg"
        />
        <Figure
          value={top.ready_by_p80_days === 0 ? "Day 0" : `Day ${top.ready_by_p80_days}`}
          caption="Ready by (P80)"
          size="md"
        />
        <Figure
          value={`₹${top.year_one_cost_lpa}L`}
          caption="Year-one cost"
          size="md"
        />
      </div>

      <p className="mt-3 font-sans text-xs text-muted">{top.reason}</p>

      <ul className="mt-2 font-mono text-xs text-muted" aria-label="Mix atoms">
        {top.atoms.map((a) => (
          <li key={a}>{a}</li>
        ))}
      </ul>

      {mixes.length > 1 && (
        <div className="mt-4 border-t border-hairline pt-3">
          <p className="font-sans text-xs font-semibold text-ink">
            Other mixes
          </p>
          <ul className="mt-1 flex flex-col gap-1">
            {mixes.slice(1).map((m) => (
              <li
                key={m.id}
                className="flex items-center justify-between font-sans text-xs text-muted"
              >
                <span>{m.name}</span>
                <span className="font-mono">
                  {m.score}/100 · ₹{m.year_one_cost_lpa}L
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </Card>
  );
}
