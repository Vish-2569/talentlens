import { useState } from "react";
import { ChevronDown, ChevronUp, Hammer, ShoppingCart, Handshake, UserCheck, LogOut, CircleStop } from "lucide-react";
import type { components } from "../api/types";
import { Badge, Card, Figure, InfoTip, SectionHeader } from "./ui";
import { useAppDispatch } from "../state/context";

type DejaReqData = components["schemas"]["DejaReq"];
type TimelineEntry = components["schemas"]["TimelineEntry"];
type Pattern = components["schemas"]["Pattern"];

interface Props {
  dejareq: DejaReqData;
}

const DECISION_ICONS: Record<string, typeof Hammer> = {
  build: Hammer,
  buy: ShoppingCart,
  borrow: Handshake,
};

const OUTCOME_ICONS: Record<string, typeof UserCheck> = {
  stayed: UserCheck,
  left: LogOut,
  ended: CircleStop,
};

function outcomeCategory(text: string): "stayed" | "left" | "ended" {
  const lower = text.toLowerCase();
  if (lower.includes("left")) return "left";
  if (lower.includes("ended") || lower.includes("contract")) return "ended";
  return "stayed";
}

function formatDate(opened: string): string {
  const [year, month] = opened.split("-");
  const months = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
  ];
  return `${months[parseInt(month, 10) - 1]} ${year}`;
}

function capitalize(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1);
}

function TimelineRow({ entry }: { entry: TimelineEntry }) {
  const DecisionIcon = DECISION_ICONS[entry.decision] ?? ShoppingCart;
  const category = outcomeCategory(entry.outcome_text);
  const OutcomeIcon = OUTCOME_ICONS[category];

  return (
    <li className="flex items-start gap-3 border-b border-hairline py-3 last:border-b-0">
      <div className="flex shrink-0 flex-col items-center gap-1">
        <span
          data-testid="timeline-date"
          className="font-mono text-xs text-muted whitespace-nowrap"
        >
          {formatDate(entry.opened)}
        </span>
      </div>

      <div className="flex-1 space-y-1">
        <div className="flex items-center gap-2">
          <DecisionIcon size={14} strokeWidth={1.5} className="shrink-0 text-ink" aria-hidden="true" />
          <span className="font-sans text-sm font-medium text-ink">
            {capitalize(entry.decision)}
          </span>
          {entry.time_to_fill_days != null && entry.time_to_fill_days > 0 && (
            <Badge variant="muted">{entry.time_to_fill_days}d to fill</Badge>
          )}
          <Badge variant="muted">₹{entry.first_year_cost_lpa}L</Badge>
        </div>

        <div className="flex items-center gap-1.5" data-testid="timeline-outcome">
          <OutcomeIcon size={12} strokeWidth={1.5} className="shrink-0 text-muted" aria-hidden="true" />
          <span className="font-sans text-xs text-muted">{entry.outcome_text}</span>
        </div>
      </div>

      <InfoTip
        aria-label={`Source for ${entry.req_id}`}
        content={
          <span>Evidence: {entry.evidence_ids.join(", ")}</span>
        }
      >
        <span className="font-mono text-xs text-muted underline decoration-dotted">
          Source
        </span>
      </InfoTip>
    </li>
  );
}

function PatternRow({ pattern, onNavigate }: { pattern: Pattern; onNavigate: () => void }) {
  const riskText =
    pattern.risk_option && pattern.risk_penalty > 0
      ? `${capitalize(pattern.risk_option)} risk +${pattern.risk_penalty.toFixed(2)}`
      : null;

  return (
    <div className="flex items-start gap-2 py-2">
      <div className="flex-1">
        <p className="font-sans text-sm text-ink">{pattern.text}</p>
        <div className="mt-1 flex flex-wrap items-center gap-2">
          {riskText && <Badge variant="red">{riskText}</Badge>}
          <button
            type="button"
            onClick={onNavigate}
            className="font-sans text-xs text-accent underline hover:text-accent/80 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
          >
            applied in the option scores
          </button>
        </div>
      </div>
    </div>
  );
}

export function DejaReq({ dejareq }: Props) {
  const dispatch = useAppDispatch();
  const [expanded, setExpanded] = useState(false);

  const { match_count, banner_text, chip, timeline, patterns, insight_text, averages_by_decision } = dejareq;

  if (match_count === 0 && !chip) return null;

  const firedPatterns = patterns.filter((p) => p.fired);
  const buyAvg = averages_by_decision.find((a) => a.decision === "buy");
  const buildAvg = averages_by_decision.find((a) => a.decision === "build");

  function navigateToOptions() {
    dispatch({ type: "SET_TAB", payload: "options" });
    requestAnimationFrame(() => {
      document.getElementById("five-option-table")?.focus({ preventScroll: false });
    });
  }

  if (match_count < 2 && chip) {
    return (
      <div data-testid="dejareq-section" className="mt-4">
        <Badge variant="muted">{chip}</Badge>
      </div>
    );
  }

  if (!banner_text) return null;

  const sortedTimeline = [...timeline].sort((a, b) => {
    if (a.opened > b.opened) return -1;
    if (a.opened < b.opened) return 1;
    return 0;
  });

  return (
    <section
      data-testid="dejareq-section"
      aria-label="Déjà Req — requisition history"
      className="mt-6"
    >
      {/* Banner */}
      <button
        type="button"
        aria-expanded={expanded}
        onClick={() => setExpanded(!expanded)}
        className="flex w-full items-center gap-2 rounded-md border border-hairline bg-surface px-4 py-3 text-left font-sans text-sm font-medium text-ink transition-colors hover:bg-paper focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
      >
        <span className="flex-1">{banner_text}</span>
        {expanded ? (
          <ChevronUp size={16} strokeWidth={1.5} aria-hidden="true" />
        ) : (
          <ChevronDown size={16} strokeWidth={1.5} aria-hidden="true" />
        )}
      </button>

      {/* Expanded content */}
      {expanded && (
        <div className="mt-3 space-y-4">
          {/* Timeline */}
          <Card>
            <ol aria-label="Requisition history" className="divide-y-0">
              {sortedTimeline.map((entry) => (
                <TimelineRow key={entry.req_id} entry={entry} />
              ))}
            </ol>
          </Card>

          {/* Insight box */}
          {insight_text && (
            <Card>
              <SectionHeader as="h3" className="text-sm mb-2">
                What your own history says
              </SectionHeader>
              <p className="font-sans text-sm text-ink mb-3">{insight_text}</p>

              <div className="flex gap-6">
                {buyAvg && (
                  <Figure
                    value={`₹${buyAvg.avg_cost_lpa}L`}
                    caption={`Avg external hire (${buyAvg.count}${buyAvg.avg_tenure_months ? `, stayed ${buyAvg.avg_tenure_months}mo` : ""})`}
                    size="md"
                  />
                )}
                {buildAvg && (
                  <Figure
                    value={`₹${buildAvg.avg_cost_lpa}L`}
                    caption={`Avg internal move (${buildAvg.count})`}
                    size="md"
                  />
                )}
              </div>
            </Card>
          )}

          {/* Patterns */}
          {firedPatterns.length > 0 && (
            <Card>
              <SectionHeader as="h3" className="text-sm mb-2">
                Patterns
              </SectionHeader>
              <div className="divide-y divide-hairline">
                {firedPatterns.map((p) => (
                  <PatternRow
                    key={p.name}
                    pattern={p}
                    onNavigate={navigateToOptions}
                  />
                ))}
              </div>
            </Card>
          )}

          {/* Guardrail */}
          <p className="font-sans text-xs text-muted">
            History is shown per requisition. No individual is scored on tenure.
          </p>
        </div>
      )}
    </section>
  );
}
