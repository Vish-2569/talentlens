import { useState } from "react";
import type { components } from "../api/types";
import { Card, SectionHeader } from "./ui";
import { RippleTree } from "./RippleTree";
import { PersonDrawer } from "./PersonDrawer";

type RippleCandidate = components["schemas"]["RippleCandidate"];
type NetImpact = components["schemas"]["NetImpact"];

interface Props {
  candidates: RippleCandidate[];
}

function NetImpactStrip({ impact }: { impact: NetImpact }) {
  return (
    <div className="mt-4 flex flex-wrap gap-4 border-t border-hairline pt-3">
      <div>
        <p className="font-sans text-xs text-muted">Last gap</p>
        <p className="font-mono text-sm font-medium text-ink">
          {impact.days_to_fill_last_gap != null
            ? `${impact.days_to_fill_last_gap} days`
            : "—"}
        </p>
      </div>
      <div>
        <p className="font-sans text-xs text-muted">Year-one cost</p>
        <p className="font-mono text-sm font-medium text-ink">
          {"₹"}
          {impact.total_cost_lpa}L
        </p>
      </div>
      <div>
        <p className="font-sans text-xs text-muted">Promotions</p>
        <p className="font-mono text-sm font-medium text-ink">
          {impact.promotions}
        </p>
      </div>
      <div>
        <p className="font-sans text-xs text-muted">Red flags</p>
        <p
          className={`font-mono text-sm font-medium ${
            impact.red_flags > 0 ? "text-redline" : "text-ink"
          }`}
        >
          {impact.red_flags}
        </p>
      </div>
    </div>
  );
}

function parseSeat(seat: string): { level: string; team: string } | null {
  const parts = seat.split("/");
  if (parts.length < 2) return null;
  return { level: parts[0], team: parts[1] };
}

export function RippleComparison({ candidates }: Props) {
  const [drawerId, setDrawerId] = useState<string | null>(null);
  const [drawerName, setDrawerName] = useState<string>("");

  function openDrawer(personId: string, name: string) {
    setDrawerId(personId);
    setDrawerName(name);
  }

  const top2 = candidates.slice(0, 2);

  return (
    <section aria-labelledby="ripple-heading">
      <SectionHeader className="text-lg">
        <span id="ripple-heading">Moving a person moves the vacancy</span>
      </SectionHeader>
      <p className="mt-1 font-sans text-sm text-muted">
        Promoting an internal candidate creates a backfill chain. A higher
        match score can be the worse decision if the chain is harder to fill.
      </p>

      <div className="mt-4 grid gap-4 md:grid-cols-2">
        {top2.map((c) => {
          const seat = parseSeat(c.chain.seat);
          const subtitle = seat
            ? `${seat.level.charAt(0).toUpperCase() + seat.level.slice(1)}, ${seat.team}`
            : "";

          return (
            <Card key={c.person_id}>
              <div className="mb-3 flex items-center justify-between gap-2">
                <div>
                  <h3 className="font-serif text-base font-semibold text-ink">
                    {c.display_name}
                  </h3>
                  {subtitle && (
                    <p className="font-sans text-xs text-muted">{subtitle}</p>
                  )}
                </div>
                <div className="flex items-center gap-3">
                  <span className="font-mono text-sm font-medium text-accent">
                    {c.match}% match
                  </span>
                  <button
                    type="button"
                    onClick={() => openDrawer(c.person_id, c.display_name)}
                    className="rounded border border-hairline px-2 py-1 font-sans text-xs text-accent hover:bg-accent/5 focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent"
                  >
                    View skills
                  </button>
                </div>
              </div>

              <RippleTree node={c.chain} onPersonClick={openDrawer} />
              <NetImpactStrip impact={c.net_impact} />
            </Card>
          );
        })}
      </div>

      <PersonDrawer
        personId={drawerId}
        onClose={() => setDrawerId(null)}
        displayName={drawerName}
      />
    </section>
  );
}
