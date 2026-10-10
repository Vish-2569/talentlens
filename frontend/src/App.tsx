import * as Tabs from "@radix-ui/react-tabs";
import { Badge, LiveRegion, SkipLink } from "./components/ui";
import { WorkflowStrip } from "./components/WorkflowStrip";
import { getStepStates } from "./components/workflowSteps";
import type { StepState } from "./components/workflowSteps";
import { Challenge } from "./screens/Challenge";
import { Decide } from "./screens/Decide";
import { Options } from "./screens/Options";
import { useAppDispatch, useAppState } from "./state/context";

const TAB_VALUES = ["challenge", "options", "decide"] as const;
type TabValue = (typeof TAB_VALUES)[number];

const TAB_LABELS: Record<TabValue, string> = {
  challenge: "Challenge the request",
  options: "Weigh the options",
  decide: "Decide",
};

export function App() {
  const state = useAppState();
  const dispatch = useAppDispatch();

  const { analysis, activeTab, decisionRecorded } = state;

  const steps = getStepStates(analysis, decisionRecorded);
  const tokens = analysis?.tokens ?? null;

  function handleStepClick(step: StepState) {
    dispatch({ type: "SET_TAB", payload: step.tab });
    requestAnimationFrame(() => {
      document.getElementById(step.scrollTarget)?.focus({ preventScroll: false });
    });
  }

  function handleTabChange(value: string) {
    const idx = TAB_VALUES.indexOf(value as TabValue) as 0 | 1 | 2;
    if (idx >= 0) dispatch({ type: "SET_TAB", payload: idx });
  }

  const activeValue = TAB_VALUES[activeTab];

  return (
    <>
      <SkipLink />

      <div className="flex min-h-screen flex-col bg-paper font-sans text-ink">
        {/* Header */}
        <header className="border-b border-hairline bg-surface" role="banner">
          <div className="mx-auto flex max-w-[1280px] items-baseline gap-3 px-4 py-3">
            <h1 className="font-serif text-lg font-semibold text-ink">
              TalentLens
            </h1>
            <span className="font-sans text-xs text-muted" aria-hidden="true">·</span>
            <span className="font-sans text-xs text-muted">
              Requisition challenger · Full Stack Developer
            </span>
            {analysis && (
              <Badge variant="muted" className="ml-auto">
                {analysis.parsed.req_id}
              </Badge>
            )}
          </div>
        </header>

        {/* Workflow strip */}
        <WorkflowStrip steps={steps} onStepClick={handleStepClick} />

        {/* Tabs */}
        <Tabs.Root
          value={activeValue}
          onValueChange={handleTabChange}
          className="flex flex-1 flex-col"
        >
          <Tabs.List
            aria-label="Screens"
            className="border-b border-hairline bg-surface"
          >
            <div className="mx-auto flex max-w-[1280px] gap-0 px-4">
              {TAB_VALUES.map((v) => (
                <Tabs.Trigger
                  key={v}
                  value={v}
                  className={[
                    "px-4 py-2.5 font-sans text-sm font-medium transition-colors duration-150",
                    "border-b-2 -mb-px",
                    "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent",
                    "data-[state=active]:border-accent data-[state=active]:text-accent",
                    "data-[state=inactive]:border-transparent data-[state=inactive]:text-muted data-[state=inactive]:hover:text-ink",
                  ].join(" ")}
                >
                  {TAB_LABELS[v]}
                </Tabs.Trigger>
              ))}
            </div>
          </Tabs.List>

          <main
            id="main-content"
            className="mx-auto w-full max-w-[1280px] flex-1 px-4 py-6"
            tabIndex={-1}
          >
            <Tabs.Content value="challenge" tabIndex={-1}>
              <Challenge />
            </Tabs.Content>
            <Tabs.Content value="options" tabIndex={-1}>
              <Options />
            </Tabs.Content>
            <Tabs.Content value="decide" tabIndex={-1}>
              <Decide />
            </Tabs.Content>
          </main>
        </Tabs.Root>

        {/* Footer */}
        <footer
          className="border-t border-hairline bg-surface"
          role="contentinfo"
        >
          <div className="mx-auto flex max-w-[1280px] flex-wrap items-center justify-between gap-2 px-4 py-2 text-xs font-sans text-muted">
            {/* Token meter */}
            <div aria-label="LLM token usage" className="flex items-center gap-3 font-mono">
              {tokens ? (
                tokens.cache_hit ? (
                  <span>0 live tokens · cached</span>
                ) : (
                  <span>
                    {tokens.calls} call{tokens.calls !== 1 ? "s" : ""} ·{" "}
                    {tokens.input_tokens} in / {tokens.output_tokens} out ·{" "}
                    est. {tokens.est_cost}
                  </span>
                )
              ) : (
                <span>—</span>
              )}
            </div>

            <div className="flex flex-col items-end gap-0.5 text-right">
              <span>All market and people data is simulated.</span>
              <span>
                Occupation and skill data: O*NET (CC BY 4.0) and ESCO.
              </span>
            </div>
          </div>
        </footer>
      </div>

      {/* aria-live region for recommendation changes */}
      <LiveRegion id="recommendation-live" />
    </>
  );
}
