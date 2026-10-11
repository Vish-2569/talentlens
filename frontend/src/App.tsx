import { useCallback, useEffect, useRef } from "react";
import { Badge, LiveRegion, SkipLink } from "./components/ui";
import { WorkflowStrip } from "./components/WorkflowStrip";
import { getStepStates } from "./components/workflowSteps";
import type { StepState } from "./components/workflowSteps";
import { HealthBanner } from "./components/HealthBanner";
import { StepNeed } from "./screens/StepNeed";
import { StepSkills } from "./screens/StepSkills";
import { StepInternal } from "./screens/StepInternal";
import { StepContractors } from "./screens/StepContractors";
import { StepMarket } from "./screens/StepMarket";
import { StepLocation } from "./screens/StepLocation";
import { StepOptions } from "./screens/StepOptions";
import { StepDecision } from "./screens/StepDecision";
import { StepAction } from "./screens/StepAction";
import { useAppDispatch, useAppState } from "./state/AppState";

function parseHash(): number | null {
  const m = window.location.hash.match(/^#step-(\d)$/);
  return m ? Number(m[1]) : null;
}

export function App() {
  const state = useAppState();
  const dispatch = useAppDispatch();
  const { result, activeStep, decision } = state;
  const prevStepRef = useRef(activeStep);

  const steps = getStepStates(result, decision !== null);
  const tokens = result?.tokens ?? null;

  // Sync hash → state on mount and popstate
  useEffect(() => {
    function onHashChange() {
      const n = parseHash();
      if (n && n >= 1 && n <= 9) {
        const step = steps.find((s) => s.id === n);
        if (step && !step.disabled) {
          dispatch({ type: "SET_STEP", payload: n });
        }
      }
    }
    onHashChange();
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dispatch, result !== null]);

  // Sync state → hash + focus heading on step change
  useEffect(() => {
    if (activeStep !== prevStepRef.current) {
      window.history.replaceState(null, "", `#step-${activeStep}`);
      window.scrollTo({ top: 0 });
      requestAnimationFrame(() => {
        const heading = document.getElementById(`step-${activeStep}-heading`);
        heading?.focus({ preventScroll: true });
      });
      prevStepRef.current = activeStep;
    }
  }, [activeStep]);

  const handleStepClick = useCallback(
    (step: StepState) => {
      if (step.disabled) return;
      dispatch({ type: "SET_STEP", payload: step.id });
      window.location.hash = `#step-${step.id}`;
    },
    [dispatch],
  );

  const goBack = useCallback(() => {
    if (activeStep > 1) {
      const next = activeStep - 1;
      dispatch({ type: "SET_STEP", payload: next });
      window.location.hash = `#step-${next}`;
    }
  }, [activeStep, dispatch]);

  const goNext = useCallback(() => {
    if (activeStep < 9) {
      const next = activeStep + 1;
      const step = steps.find((s) => s.id === next);
      if (step && !step.disabled) {
        dispatch({ type: "SET_STEP", payload: next });
        window.location.hash = `#step-${next}`;
      }
    }
  }, [activeStep, steps, dispatch]);

  const disabledMessage = (
    <p className="py-8 text-center font-sans text-sm text-muted">
      Run an analysis first.
    </p>
  );

  function stepContent() {
    switch (activeStep) {
      case 1:
        return <StepNeed />;
      case 2:
        return result ? <StepSkills /> : disabledMessage;
      case 3:
        return result ? <StepInternal /> : disabledMessage;
      case 4:
        return result ? <StepContractors /> : disabledMessage;
      case 5:
        return result ? <StepMarket /> : disabledMessage;
      case 6:
        return result ? <StepLocation /> : disabledMessage;
      case 7:
        return result ? <StepOptions /> : disabledMessage;
      case 8:
        return result ? <StepDecision /> : disabledMessage;
      case 9:
        return result ? <StepAction /> : disabledMessage;
      default:
        return null;
    }
  }

  const canBack = activeStep > 1;
  const canNext = activeStep < 9 && !(activeStep === 1 && !result);

  return (
    <>
      <SkipLink />

      <div className="flex min-h-screen flex-col bg-paper font-sans text-ink">
        <HealthBanner />

        {/* Header */}
        <header className="border-b border-hairline bg-surface" role="banner">
          <div className="mx-auto flex max-w-[1280px] items-baseline gap-3 px-4 py-2">
            <h1 className="font-serif text-lg font-semibold text-ink">
              TalentLens
            </h1>
            <span className="font-sans text-xs text-muted" aria-hidden="true">·</span>
            <span className="font-sans text-xs text-muted">
              Requisition challenger · Full Stack Developer
            </span>
            {result && (
              <Badge variant="muted" className="ml-auto">
                {result.parsed.req_id}
              </Badge>
            )}
          </div>
        </header>

        {/* Workflow strip — the sole navigation */}
        <WorkflowStrip
          steps={steps}
          activeStep={activeStep}
          onStepClick={handleStepClick}
        />

        {/* Step content */}
        <main
          id="main-content"
          className="mx-auto w-full max-w-[1280px] flex-1 px-4 py-4"
          tabIndex={-1}
        >
          {stepContent()}

          {/* Back / Next */}
          <div className="mt-6 flex items-center justify-between border-t border-hairline pt-4">
            <button
              type="button"
              onClick={goBack}
              disabled={!canBack}
              className="rounded border border-hairline bg-surface px-4 py-1.5 font-sans text-sm font-medium text-ink transition-colors hover:bg-paper disabled:cursor-not-allowed disabled:opacity-40 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
            >
              ← Back
            </button>
            <span className="font-mono text-xs text-muted">
              Step {activeStep} of 9
            </span>
            <button
              type="button"
              onClick={goNext}
              disabled={!canNext}
              className="rounded border border-hairline bg-surface px-4 py-1.5 font-sans text-sm font-medium text-ink transition-colors hover:bg-paper disabled:cursor-not-allowed disabled:opacity-40 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
            >
              Next →
            </button>
          </div>
        </main>

        {/* Footer */}
        <footer
          className="border-t border-hairline bg-surface"
          role="contentinfo"
        >
          <div className="mx-auto flex max-w-[1280px] flex-wrap items-center justify-between gap-2 px-4 py-1.5 text-xs font-sans text-muted">
            <div aria-label="LLM token usage" className="flex items-center gap-3 font-mono">
              {tokens ? (
                tokens.cache_hit ? (
                  <span>0 live tokens — cached</span>
                ) : tokens.calls === 0 ? (
                  <span>0 live tokens — parsed by rules, Gemini not needed</span>
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
              <span>Occupation and skill data: O*NET (CC BY 4.0) and ESCO.</span>
            </div>
          </div>
        </footer>
      </div>

      <LiveRegion id="recommendation-live" />
    </>
  );
}
