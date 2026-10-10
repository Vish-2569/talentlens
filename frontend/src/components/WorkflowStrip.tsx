import type { StepState } from "./workflowSteps";

interface Props {
  steps: StepState[];
  onStepClick: (step: StepState) => void;
}

export function WorkflowStrip({ steps, onStepClick }: Props) {
  return (
    <nav aria-label="Workflow progress" className="border-b border-hairline bg-surface">
      <ol
        className="mx-auto flex max-w-[1280px] items-stretch overflow-x-auto px-4"
      >
        {steps.map((step, i) => {
          const isLast = i === steps.length - 1;

          return (
            <li
              key={step.id}
              className={[
                "relative flex shrink-0 items-center",
                !isLast ? "after:mx-1 after:text-hairline after:content-['/']" : "",
              ].join(" ")}
            >
              {step.lit ? (
                <button
                  type="button"
                  onClick={() => onStepClick(step)}
                  className={[
                    "flex items-center gap-1.5 px-2 py-3 text-xs font-sans font-medium",
                    "text-accent hover:underline",
                    "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent",
                  ].join(" ")}
                  aria-label={`Go to ${step.label}`}
                >
                  <span
                    className="flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-accent font-mono text-[10px] text-white"
                    aria-hidden="true"
                  >
                    {step.id}
                  </span>
                  <span>{step.label}</span>
                </button>
              ) : (
                <span
                  className="flex items-center gap-1.5 px-2 py-3 text-xs font-sans text-muted"
                  aria-label={`${step.label} — pending`}
                >
                  <span
                    className="flex h-4 w-4 shrink-0 items-center justify-center rounded-full border border-hairline font-mono text-[10px] text-muted"
                    aria-hidden="true"
                  >
                    {step.id}
                  </span>
                  <span>{step.label}</span>
                  <span className="sr-only">(pending)</span>
                </span>
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
