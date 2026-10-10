import { useCallback } from "react";
import type { KeyboardEvent } from "react";
import type { components } from "../api/types";
import { StatusMark } from "./ui";

type Constraint = components["schemas"]["Constraint"];
type ConstraintKind = components["schemas"]["ConstraintKind"];

interface Props {
  constraints: Constraint[];
  constraintOrder: ConstraintKind[];
  mask: string;
  onToggle: (index: number, relaxed: boolean) => void;
}

function formatCost(cost: components["schemas"]["ConstraintCost"]): string {
  const parts: string[] = [];
  if (cost.supply_delta != null) {
    parts.push(`+${cost.supply_delta} candidates`);
  }
  if (cost.days_delta != null) {
    const sign = cost.days_delta < 0 ? "" : "+";
    parts.push(`${sign}${cost.days_delta} days`);
  }
  if (cost.rupees_delta_lpa != null) {
    const sign = cost.rupees_delta_lpa < 0 ? "−" : "+";
    parts.push(`${sign}₹${Math.abs(cost.rupees_delta_lpa)}L/yr`);
  }
  return parts.length > 0 ? parts.join(", ") : "Internal impact only";
}

function KeepRelaxControl({
  relaxed,
  onChange,
  constraintId,
}: {
  relaxed: boolean;
  onChange: (relaxed: boolean) => void;
  constraintId: string;
}) {
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === "ArrowLeft" || e.key === "ArrowUp") {
        e.preventDefault();
        onChange(false);
      } else if (e.key === "ArrowRight" || e.key === "ArrowDown") {
        e.preventDefault();
        onChange(true);
      }
    },
    [onChange],
  );

  const base =
    "px-3 py-1.5 text-xs font-medium font-sans rounded transition-colors duration-150 " +
    "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent";

  return (
    <div
      role="radiogroup"
      aria-label={`Keep or relax ${constraintId}`}
      className="inline-flex rounded border border-hairline"
      tabIndex={-1}
      onKeyDown={handleKeyDown}
    >
      <button
        type="button"
        role="radio"
        aria-checked={!relaxed}
        tabIndex={!relaxed ? 0 : -1}
        onClick={() => onChange(false)}
        className={`${base} ${!relaxed ? "bg-accent text-white" : "bg-surface text-muted hover:text-ink"}`}
      >
        Keep
      </button>
      <button
        type="button"
        role="radio"
        aria-checked={relaxed}
        tabIndex={relaxed ? 0 : -1}
        onClick={() => onChange(true)}
        className={`${base} ${relaxed ? "bg-accent text-white" : "bg-surface text-muted hover:text-ink"}`}
      >
        Relax
      </button>
    </div>
  );
}

export function RedlineCards({ constraints, constraintOrder, mask, onToggle }: Props) {
  const byKind = new Map(constraints.map((c, i) => [c.kind, { constraint: c, index: i }]));

  return (
    <ul className="flex flex-col gap-3" aria-label="Redline constraints">
      {constraintOrder.map((kind) => {
        const entry = byKind.get(kind);
        if (!entry) return null;
        const { constraint: c, index } = entry;
        const relaxed = mask[index] === "1";

        return (
          <li
            key={c.id}
            className="rounded border border-hairline bg-surface px-4 py-3"
          >
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div className="flex-1 min-w-0">
                <p className="font-sans text-sm font-semibold text-ink">
                  {c.phrase}
                </p>
                <div className="mt-1">
                  <StatusMark status={c.severity === "none" ? "green" : c.severity} />
                </div>
                <p className="mt-1 font-mono text-xs text-muted">
                  {formatCost(c.cost)}
                </p>
                {c.relaxed_value && (
                  <p className="mt-1 font-sans text-xs text-muted">
                    Relax to: {c.relaxed_value}
                  </p>
                )}
              </div>
              <KeepRelaxControl
                relaxed={relaxed}
                onChange={(r) => onToggle(index, r)}
                constraintId={c.id}
              />
            </div>
          </li>
        );
      })}
    </ul>
  );
}
