import { useState } from "react";
import { LoadingStages } from "../components/LoadingStages";
import { ParsedFields } from "../components/ParsedFields";
import { RequestComposer } from "../components/RequestComposer";
import { TitleNormPanel } from "../components/TitleNormPanel";
import { EmptyState } from "../components/ui";
import { useAppState } from "../state/context";

const DEMO_SENTENCE =
  "Senior Full Stack Developer, Bengaluru, on-site, 5+ years, must know React, Node.js and Kubernetes, budget ₹28L, need in 30 days.";

export function Challenge() {
  const { status, result, requestText } = useAppState();
  const [editing, setEditing] = useState(false);

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

          {/* Redline + Déjà Req slot — built in F4/F5 */}

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
