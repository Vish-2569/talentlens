import { useEffect, useRef, useState } from "react";
import { AssumptionLedger } from "../components/AssumptionLedger";
import { LiveRecommendation } from "../components/LiveRecommendation";
import { LoadingStages } from "../components/LoadingStages";
import { ParsedFields } from "../components/ParsedFields";
import { RedlineCards } from "../components/RedlineCards";
import { RedlineText } from "../components/RedlineText";
import { RequestComposer } from "../components/RequestComposer";
import { TitleNormPanel } from "../components/TitleNormPanel";
import { EmptyState } from "../components/ui";
import { useAppDispatch, useAppState } from "../state/context";
import { currentScenario } from "../state/AppState";

const DEMO_SENTENCE =
  "Senior Full Stack Developer, Bengaluru, on-site, 5+ years, must know React, Node.js and Kubernetes, budget ₹28L, need in 30 days.";

export function Challenge() {
  const state = useAppState();
  const dispatch = useAppDispatch();
  const { status, result, requestText, mask } = state;
  const [editing, setEditing] = useState(false);

  const scenario = currentScenario(state);
  const prevPanelRef = useRef<string | null>(null);

  useEffect(() => {
    const panelText = scenario?.panel_text ?? null;
    if (panelText && panelText !== prevPanelRef.current) {
      const el = document.getElementById("recommendation-live");
      if (el) el.textContent = `Recommendation updated: ${panelText}`;
    }
    prevPanelRef.current = panelText;
  }, [scenario]);

  const composerVisible =
    status === "idle" ||
    status === "error" ||
    status === "loading" ||
    (status === "ready" && editing);

  const composerHidden = status === "loading";

  return (
    <section aria-labelledby="challenge-heading" id="challenge-tab">
      <h2 id="challenge-heading" className="sr-only">
        Challenge the request
      </h2>

      <div id="challenge-input" className="mb-6">
        {composerVisible && (
          <div className={composerHidden ? "hidden" : undefined}>
            <RequestComposer
              demoSentence={DEMO_SENTENCE}
              initialText={requestText}
            />
          </div>
        )}

        {status === "loading" && <LoadingStages />}

        {status === "ready" && !editing && (
          <div className="flex items-baseline gap-3">
            <p className="font-sans text-sm text-ink">{requestText}</p>
            <button
              onClick={() => setEditing(true)}
              className="shrink-0 font-sans text-sm font-medium text-accent hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
            >
              Edit request
            </button>
          </div>
        )}
      </div>

      {status === "ready" && result && (
        <>
          <div className="mb-6">
            <ParsedFields parsed={result.parsed} />
          </div>

          {/* Redline */}
          <section id="redline-section" aria-label="Requisition redline" className="mt-6">
            <div className="lg:grid lg:grid-cols-[1fr_320px] lg:gap-6">
              <div>
                <RedlineText
                  requestText={requestText}
                  constraints={result.redline.constraints}
                  mask={mask}
                />
                <div className="mt-4">
                  <RedlineCards
                    constraints={result.redline.constraints}
                    constraintOrder={result.redline.constraint_order}
                    mask={mask}
                    onToggle={(index, relaxed) =>
                      dispatch({
                        type: "TOGGLE_CONSTRAINT",
                        payload: { index, relaxed },
                      })
                    }
                  />
                </div>
                <AssumptionLedger
                  constraints={result.redline.constraints}
                  constraintOrder={result.redline.constraint_order}
                  mask={mask}
                  decisionBoundaries={result.options.decision_boundaries}
                />
              </div>
              <div className="mt-4 lg:mt-0">
                <LiveRecommendation
                  scenario={scenario}
                  fiveOptions={result.options.five}
                  mask={mask}
                  onReset={() => dispatch({ type: "RESET_MASK" })}
                />
              </div>
            </div>
          </section>

          {/* Déjà Req slot — built in F5 */}

          <div className="mt-6">
            <TitleNormPanel
              titleNormalization={result.parsed.title_normalization}
            />
          </div>
        </>
      )}

      {status === "idle" && (
        <EmptyState
          title="Submit a requisition to begin"
          description="Enter job requirements above and click Analyse."
        />
      )}
    </section>
  );
}
