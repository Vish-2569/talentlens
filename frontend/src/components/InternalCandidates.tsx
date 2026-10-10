import type { components } from "../api/types";
import { Badge, Card } from "./ui";

type InternalCandidate = components["schemas"]["InternalCandidate"];

interface Props {
  candidates: InternalCandidate[];
  onSelectPerson: (id: string) => void;
}

function bandBadgeVariant(band: string): "green" | "accent" | "amber" | "muted" {
  if (band === "redeploy") return "green";
  if (band === "Build") return "accent";
  return "muted";
}

export function InternalCandidates({ candidates, onSelectPerson }: Props) {
  if (candidates.length === 0) return null;

  return (
    <Card
      header={{
        title: "Internal candidates",
        meaning: `${candidates.length} matched`,
      }}
    >
      <ul className="flex flex-col gap-2">
        {candidates.map((c) => (
          <li key={c.person_id}>
            <button
              type="button"
              onClick={() => onSelectPerson(c.person_id)}
              className="flex w-full items-center justify-between rounded border border-hairline bg-paper p-2 text-left hover:border-accent focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
            >
              <div>
                <span className="font-sans text-sm font-semibold text-ink">
                  {c.display_name}
                </span>
                <div className="mt-0.5 flex flex-wrap gap-2 font-mono text-xs text-muted">
                  <span>{c.match}% match</span>
                  {c.readiness_weeks != null && (
                    <span>
                      {c.readiness_weeks === 0
                        ? "Ready now"
                        : `${c.readiness_weeks} weeks`}
                    </span>
                  )}
                  {c.build_cost_lpa != null && c.build_cost_lpa > 0 && (
                    <span>₹{c.build_cost_lpa}L</span>
                  )}
                </div>
              </div>
              <Badge variant={bandBadgeVariant(c.band)}>{c.band}</Badge>
            </button>
          </li>
        ))}
      </ul>
    </Card>
  );
}
