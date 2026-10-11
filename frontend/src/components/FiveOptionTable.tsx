import type { components } from "../api/types";
import { Badge, InfoTip, LiveRegion } from "./ui";
import { displayOptionText } from "./displayNames";

type OptionCard = components["schemas"]["OptionCard"];

interface Props {
  options: OptionCard[];
}

function formatReadyBy(days: number | null | undefined): string {
  if (days == null) return "—";
  if (days === 0) return "Day 0";
  if (days % 7 === 0) return `Week ${days / 7}`;
  return `Day ${days}`;
}

function riskBadgeVariant(label: string): "green" | "amber" | "red" | "muted" {
  if (label === "Low") return "green";
  if (label === "Medium") return "amber";
  if (label === "Medium-high") return "amber";
  if (label === "High") return "red";
  return "muted";
}

export function FiveOptionTable({ options }: Props) {
  return (
    <LiveRegion>
      <div
        id="five-option-table"
        tabIndex={-1}
        className="overflow-x-auto focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
      >
        <div className="hidden md:block">
        <table className="w-full min-w-[900px] text-left font-sans text-sm">
          <caption className="sr-only">
            Five option comparison: {options.filter((o) => o.score != null).length} scored options plus Automate add-on
          </caption>
          <thead>
            <tr className="border-b border-hairline text-xs text-muted">
              <th className="pb-2 pr-3 font-semibold whitespace-nowrap">Option</th>
              <th className="pb-2 pr-3 font-semibold">What it means</th>
              <th className="pb-2 pr-3 font-semibold text-right whitespace-nowrap">Ready by</th>
              <th className="pb-2 pr-3 font-semibold text-right whitespace-nowrap">Year-one cost</th>
              <th className="pb-2 pr-3 font-semibold text-right whitespace-nowrap">Fit</th>
              <th className="pb-2 pr-3 font-semibold whitespace-nowrap">Risk</th>
              <th className="pb-2 pr-3 font-semibold text-right whitespace-nowrap">Score</th>
              <th className="pb-2 font-semibold">Reason</th>
            </tr>
          </thead>
          <tbody>
            {options.map((opt) => (
              <tr
                key={opt.id}
                className="border-b border-hairline last:border-0"
              >
                <td className="py-2 pr-3 font-semibold text-ink whitespace-nowrap">{opt.name}</td>
                <td className="py-2 pr-3 text-xs text-muted">{displayOptionText(opt.what_it_means)}</td>
                <td className="py-2 pr-3 text-right font-mono text-xs whitespace-nowrap">
                  {formatReadyBy(opt.ready_by_p80_days)}
                </td>
                <td className="py-2 pr-3 text-right font-mono text-xs whitespace-nowrap">
                  {opt.year_one_cost_lpa != null ? `₹${opt.year_one_cost_lpa}L` : "—"}
                </td>
                <td className="py-2 pr-3 text-right font-mono text-xs whitespace-nowrap">
                  {opt.fit ?? "—"}
                </td>
                <td className="py-2 pr-3">
                  <Badge variant={riskBadgeVariant(opt.risk_label)}>
                    {opt.risk_label}
                  </Badge>
                </td>
                <td className="py-2 pr-3 text-right font-mono text-xs font-semibold">
                  {opt.score != null ? opt.score : "Add-on"}
                </td>
                <td className="py-2 text-xs text-muted">
                  <span>{displayOptionText(opt.reason)}</span>
                  {opt.evidence_ids.length > 0 && (
                    <InfoTip
                      aria-label="Evidence IDs"
                      content={
                        <ul className="text-xs">
                          {opt.evidence_ids.map((eid) => (
                            <li key={eid}>{eid}</li>
                          ))}
                        </ul>
                      }
                    >
                      <span className="ml-1 text-accent underline">
                        Evidence
                      </span>
                    </InfoTip>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        </div>

        {/* Stacked cards for mobile */}
        <div className="flex flex-col gap-3 md:hidden">
          {options.map((opt) => (
            <div
              key={opt.id}
              className="rounded border border-hairline bg-surface p-3"
            >
              <div className="flex items-center justify-between">
                <span className="font-sans text-sm font-semibold text-ink">
                  {opt.name}
                </span>
                <span className="font-mono text-xs font-semibold">
                  {opt.score != null ? `${opt.score}/100` : "Add-on"}
                </span>
              </div>
              <p className="mt-1 text-xs text-muted">{displayOptionText(opt.what_it_means)}</p>
              <div className="mt-2 flex flex-wrap gap-2 text-xs text-muted font-mono">
                <span>{formatReadyBy(opt.ready_by_p80_days)}</span>
                {opt.year_one_cost_lpa != null && (
                  <span>₹{opt.year_one_cost_lpa}L</span>
                )}
                <span>Fit: {opt.fit ?? "—"}</span>
                <Badge variant={riskBadgeVariant(opt.risk_label)}>
                  {opt.risk_label}
                </Badge>
              </div>
              <p className="mt-1 text-xs text-muted">{displayOptionText(opt.reason)}</p>
            </div>
          ))}
        </div>
      </div>
    </LiveRegion>
  );
}
