import type { components } from "../api/types";
import { Badge } from "./ui";

type ScenarioResult = components["schemas"]["ScenarioResult"];
type OptionCard = components["schemas"]["OptionCard"];

interface Props {
  scenario: ScenarioResult | null;
  fiveOptions: OptionCard[];
  mask: string;
  onReset: () => void;
}

function formatReadyBy(days: number | null | undefined): string {
  if (days == null) return "—";
  if (days === 0) return "Day 0";
  if (days % 7 === 0) return `Week ${days / 7}`;
  return `Day ${days}`;
}

export function LiveRecommendation({ scenario, fiveOptions, mask, onReset }: Props) {
  if (!scenario) return null;

  const top = scenario.options[0];
  const isDefault = mask === "0".repeat(mask.length);

  return (
    <aside
      aria-label="Live recommendation"
      className="rounded border border-hairline bg-surface p-4 lg:sticky lg:top-4"
    >
      <p className="font-sans text-sm font-semibold text-ink">
        {scenario.panel_text}
      </p>

      {top && (
        <div className="mt-3 flex flex-wrap items-baseline gap-3">
          <Badge variant="accent">{top.name}</Badge>
          <span className="font-mono text-xs text-muted">
            {formatReadyBy(top.ready_by_p80_days)}
          </span>
          {top.year_one_cost_lpa != null && (
            <span className="font-mono text-xs text-muted">
              ₹{top.year_one_cost_lpa}L
            </span>
          )}
          {top.score != null && (
            <span className="font-mono text-xs text-muted">
              {top.score}/100
            </span>
          )}
        </div>
      )}

      <ul className="mt-3 flex flex-col gap-1" aria-label="All options">
        {fiveOptions.map((opt) => (
          <li
            key={opt.id}
            className={`flex items-center justify-between font-sans text-xs ${
              top && opt.id === top.option_id
                ? "font-semibold text-ink"
                : "text-muted"
            }`}
          >
            <span>{opt.name}</span>
            <span className="font-mono">{opt.score ?? "—"}</span>
          </li>
        ))}
      </ul>

      {!isDefault && (
        <button
          type="button"
          onClick={onReset}
          className="mt-3 font-sans text-xs font-medium text-accent hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
        >
          Reset to original request
        </button>
      )}
    </aside>
  );
}
