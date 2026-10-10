import type { components } from "../api/types";
import { Card } from "./ui";

type Sourcing = components["schemas"]["Sourcing"];

interface Props {
  sourcing: Sourcing;
}

export function SourcingPanel({ sourcing }: Props) {
  const remoteReady = sourcing.past_finalists.filter(
    (f) => f.open_to_remote,
  ).length;

  return (
    <Card header={{ title: "Sourcing channels" }}>
      <table className="w-full text-left font-sans text-xs">
        <thead>
          <tr className="border-b border-hairline text-muted">
            <th className="pb-1 pr-2 font-semibold">Rank</th>
            <th className="pb-1 pr-2 font-semibold">Channel</th>
            <th className="pb-1 pr-2 font-semibold">Evidence</th>
            <th className="pb-1 font-semibold">Use for</th>
          </tr>
        </thead>
        <tbody>
          {sourcing.channels.map((ch, i) => (
            <tr key={i} className="border-b border-hairline last:border-0">
              <td className="py-1 pr-2 font-mono text-muted">
                {ch.rank ?? "—"}
              </td>
              <td className="py-1 pr-2 text-ink">{ch.channel}</td>
              <td className="py-1 pr-2 text-muted">{ch.evidence}</td>
              <td className="py-1 text-muted">{ch.use_for}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className="mt-3 flex flex-wrap gap-4 text-xs text-muted">
        <span>
          Past finalists: {sourcing.past_finalists.length} ({remoteReady} remote-ready)
        </span>
        <span>Suppliers: {sourcing.suppliers.length}</span>
      </div>

      {sourcing.suppliers.length > 0 && (
        <table className="mt-2 w-full text-left font-sans text-xs">
          <thead>
            <tr className="border-b border-hairline text-muted">
              <th className="pb-1 pr-2 font-semibold">Supplier</th>
              <th className="pb-1 pr-2 font-semibold text-right">Fill rate</th>
              <th className="pb-1 font-semibold text-right">Median days</th>
            </tr>
          </thead>
          <tbody>
            {sourcing.suppliers.map((s) => (
              <tr
                key={s.supplier_id}
                className="border-b border-hairline last:border-0"
              >
                <td className="py-1 pr-2 text-ink">{s.name}</td>
                <td className="py-1 pr-2 text-right font-mono">
                  {(s.fill_rate * 100).toFixed(0)}%
                </td>
                <td className="py-1 text-right font-mono">
                  {s.median_days_to_submit}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Card>
  );
}
