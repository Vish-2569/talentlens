import * as Tooltip from "@radix-ui/react-tooltip";
import type { StepState } from "./workflowSteps";

interface Props {
  steps: StepState[];
  onStepClick: (step: StepState) => void;
}

export function WorkflowStrip({ steps, onStepClick }: Props) {
  return (
    <Tooltip.Provider delayDuration={200}>
      <nav aria-label="Workflow progress" className="border-b border-hairline bg-surface">
        <ol className="mx-auto flex max-w-[1280px] items-stretch px-2">
          {steps.map((step, i) => {
            const isLast = i === steps.length - 1;
            const isDecideStep = step.id === 8 || step.id === 9;
            const clickable = step.lit || isDecideStep;

            const pendingText =
              isDecideStep && !step.lit
                ? "pending: approve on Decide"
                : undefined;

            const tooltipContent = pendingText
              ? `${step.label} — ${pendingText}`
              : step.label;

            return (
              <li
                key={step.id}
                className={[
                  "relative flex shrink-0 items-center",
                  !isLast
                    ? "after:mx-0.5 after:text-hairline after:content-['/']"
                    : "",
                ].join(" ")}
              >
                <Tooltip.Root>
                  <Tooltip.Trigger asChild>
                    {clickable ? (
                      <button
                        type="button"
                        onClick={() => onStepClick(step)}
                        className={[
                          "flex items-center gap-1 px-1.5 py-2.5 text-xs font-sans font-medium",
                          step.lit
                            ? "text-accent hover:underline"
                            : "text-muted hover:text-ink",
                          "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent",
                        ].join(" ")}
                        aria-label={tooltipContent}
                      >
                        <StepBadge id={step.id} lit={step.lit} />
                        <span className="whitespace-nowrap">
                          {step.shortLabel}
                        </span>
                      </button>
                    ) : (
                      <span
                        className="flex items-center gap-1 px-1.5 py-2.5 text-xs font-sans text-muted"
                        aria-label={`${step.label} — pending`}
                      >
                        <StepBadge id={step.id} lit={false} />
                        <span className="whitespace-nowrap">
                          {step.shortLabel}
                        </span>
                        <span className="sr-only">(pending)</span>
                      </span>
                    )}
                  </Tooltip.Trigger>
                  <Tooltip.Portal>
                    <Tooltip.Content
                      side="bottom"
                      sideOffset={4}
                      className="rounded bg-ink px-2 py-1 text-xs text-white shadow-md animate-in fade-in-0 zoom-in-95"
                    >
                      {tooltipContent}
                      <Tooltip.Arrow className="fill-ink" />
                    </Tooltip.Content>
                  </Tooltip.Portal>
                </Tooltip.Root>
              </li>
            );
          })}
        </ol>
      </nav>
    </Tooltip.Provider>
  );
}

function StepBadge({ id, lit }: { id: number; lit: boolean }) {
  return (
    <span
      className={[
        "flex h-4 w-4 shrink-0 items-center justify-center rounded-full font-mono text-[10px]",
        lit
          ? "bg-accent text-white"
          : "border border-hairline text-muted",
      ].join(" ")}
      aria-hidden="true"
    >
      {id}
    </span>
  );
}
