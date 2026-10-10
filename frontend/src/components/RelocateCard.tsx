import { useState } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  LabelList,
  ResponsiveContainer,
} from "recharts";
import type { components } from "../api/types";
import { Card } from "./ui";

type RelocateRow = components["schemas"]["RelocateRow"];

interface Props {
  rows: RelocateRow[];
}

export function RelocateCard({ rows }: Props) {
  const [showTable, setShowTable] = useState(false);

  const chartData = rows.map((r) => ({
    location: r.location,
    score: r.score,
    supply: r.supply,
  }));

  const prefersReduced =
    typeof window !== "undefined" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  return (
    <Card header={{ title: "Location comparison", meaning: "Relocate card" }}>
      <div className="flex justify-end">
        <button
          type="button"
          onClick={() => setShowTable((v) => !v)}
          className="font-sans text-xs font-medium text-accent hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
        >
          {showTable ? "Show chart" : "Show as table"}
        </button>
      </div>

      {showTable ? (
        <table className="mt-2 w-full text-left font-sans text-xs">
          <thead>
            <tr className="border-b border-hairline text-muted">
              <th className="pb-1 pr-2 font-semibold">Location</th>
              <th className="pb-1 pr-2 font-semibold text-right">Supply</th>
              <th className="pb-1 pr-2 font-semibold text-right">P50 days</th>
              <th className="pb-1 pr-2 font-semibold text-right">P80 days</th>
              <th className="pb-1 pr-2 font-semibold text-right">P50 pay</th>
              <th className="pb-1 font-semibold text-right">Score</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.location} className="border-b border-hairline last:border-0">
                <td className="py-1 pr-2 text-ink">{r.location}</td>
                <td className="py-1 pr-2 text-right font-mono">{r.supply}</td>
                <td className="py-1 pr-2 text-right font-mono">{r.ttf_p50}</td>
                <td className="py-1 pr-2 text-right font-mono">{r.ttf_p80}</td>
                <td className="py-1 pr-2 text-right font-mono">₹{r.pay_p50_lpa}L</td>
                <td className="py-1 text-right font-mono">{r.score.toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <div className="mt-2 h-40" aria-hidden="true">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={chartData}
              layout="vertical"
              margin={{ left: 10, right: 30, top: 5, bottom: 5 }}
            >
              <XAxis type="number" domain={[0, 1]} hide />
              <YAxis
                type="category"
                dataKey="location"
                width={120}
                tick={{ fontSize: 11, fontFamily: "IBM Plex Sans" }}
              />
              <Bar
                dataKey="score"
                fill="var(--color-accent, #3B82F6)"
                radius={[0, 4, 4, 0]}
                isAnimationActive={!prefersReduced}
                animationDuration={200}
              >
                <LabelList
                  dataKey="score"
                  position="right"
                  formatter={(v: unknown) =>
                    typeof v === "number" ? v.toFixed(2) : ""
                  }
                  style={{ fontSize: 11, fontFamily: "IBM Plex Mono" }}
                />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </Card>
  );
}
