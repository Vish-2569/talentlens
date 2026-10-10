import type { components } from "../api/types";
import { InfoTip, VisuallyHidden } from "./ui";

type Constraint = components["schemas"]["Constraint"];

interface Props {
  requestText: string;
  constraints: Constraint[];
  mask: string;
}

const severityStyle: Record<string, string> = {
  red: "decoration-redline decoration-double underline decoration-2 text-redline",
  amber: "decoration-amber decoration-dashed underline decoration-1 text-amber",
};

const severityIcon: Record<string, string> = {
  red: "▲",
  amber: "◆",
};

const severityLabel: Record<string, string> = {
  red: "High cost",
  amber: "Moderate cost",
};

export function RedlineText({ requestText, constraints, mask }: Props) {
  const spanned = constraints
    .map((c, i) => ({ constraint: c, index: i }))
    .filter((e) => e.constraint.span_start != null && e.constraint.span_end != null)
    .sort((a, b) => a.constraint.span_start - b.constraint.span_start);

  const segments: React.ReactNode[] = [];
  let cursor = 0;

  for (const { constraint: c, index } of spanned) {
    if (c.span_start > cursor) {
      segments.push(
        <span key={`gap-${cursor}`}>
          {requestText.slice(cursor, c.span_start)}
        </span>,
      );
    }

    const relaxed = mask[index] === "1";
    const sev = c.severity;
    const style = severityStyle[sev] ?? "";
    const icon = severityIcon[sev];
    const label = severityLabel[sev];

    segments.push(
      <InfoTip key={c.id} content={c.hover_text} aria-label={`${c.phrase} constraint`}>
        <mark
          className={`bg-transparent ${relaxed ? "line-through opacity-60" : style}`}
          data-severity={sev}
        >
          {label && <VisuallyHidden>{label}</VisuallyHidden>}
          {icon && (
            <span aria-hidden="true" className="mr-0.5 text-[0.65em]">
              {icon}
            </span>
          )}
          {requestText.slice(c.span_start, c.span_end)}
        </mark>
        {relaxed && c.relaxed_value && (
          <span className="ml-1 text-sm text-muted">{c.relaxed_value}</span>
        )}
      </InfoTip>,
    );

    cursor = c.span_end;
  }

  if (cursor < requestText.length) {
    segments.push(
      <span key={`tail-${cursor}`}>{requestText.slice(cursor)}</span>,
    );
  }

  return (
    <p className="font-sans text-base leading-relaxed text-ink">{segments}</p>
  );
}
