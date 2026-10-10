import { useCallback, useRef, useState } from "react";
import { analyze } from "../api/client";
import type { ApiError } from "../api/client";
import { useAppDispatch, useAppState } from "../state/context";
import { Button, ErrorBanner } from "./ui";

const MAX_CHARS = 1000;
const COUNTER_ID = "req-char-counter";

interface Props {
  demoSentence: string;
  initialText?: string;
}

export function RequestComposer({ demoSentence, initialText = "" }: Props) {
  const dispatch = useAppDispatch();
  const { status } = useAppState();
  const [text, setText] = useState(initialText);
  const [fieldError, setFieldError] = useState<string | null>(null);
  const [networkError, setNetworkError] = useState<string | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const overLimit = text.length > MAX_CHARS;
  const canSubmit = text.trim().length > 0 && !overLimit && status !== "loading";

  const submit = useCallback(async () => {
    if (!canSubmit) return;
    setFieldError(null);
    setNetworkError(null);
    dispatch({ type: "ANALYZE_START", payload: { requestText: text } });
    try {
      const result = await analyze({ text });
      dispatch({ type: "ANALYZE_SUCCESS", payload: result });
    } catch (err: unknown) {
      const apiErr = err as ApiError;
      if (apiErr.status === 422 && apiErr.fieldErrors) {
        const msg =
          apiErr.fieldErrors.map((e) => e.msg).join("; ") ||
          apiErr.message;
        setFieldError(msg);
        dispatch({ type: "ANALYZE_ERROR", payload: msg });
      } else if (apiErr.status && apiErr.message) {
        setFieldError(apiErr.message);
        dispatch({ type: "ANALYZE_ERROR", payload: apiErr.message });
      } else {
        const msg = "Network error. Please try again.";
        setNetworkError(msg);
        dispatch({ type: "ANALYZE_ERROR", payload: msg });
      }
    }
  }, [canSubmit, text, dispatch]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
        e.preventDefault();
        submit();
      }
    },
    [submit],
  );

  const fillExample = useCallback(() => {
    setText(demoSentence);
    setFieldError(null);
    textareaRef.current?.focus();
  }, [demoSentence]);

  return (
    <div>
      <label
        htmlFor="req-textarea"
        className="mb-1 block font-sans text-sm font-medium text-ink"
      >
        Describe the role you want to open
      </label>
      <textarea
        ref={textareaRef}
        id="req-textarea"
        value={text}
        onChange={(e) => {
          setText(e.target.value);
          if (fieldError) setFieldError(null);
        }}
        onKeyDown={handleKeyDown}
        aria-describedby={COUNTER_ID}
        rows={4}
        className="w-full resize-y rounded-md border border-hairline bg-surface px-3 py-2 font-sans text-sm text-ink placeholder:text-muted focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
        placeholder="e.g. Senior Full Stack Developer, Bengaluru, on-site…"
      />

      <div className="mt-1 flex items-center justify-between gap-2">
        <span
          id={COUNTER_ID}
          className={`font-mono text-xs ${overLimit ? "text-redline" : "text-muted"}`}
        >
          {overLimit
            ? `Over ${MAX_CHARS.toLocaleString()} characters — shorten to submit`
            : `${text.length.toLocaleString()}/${MAX_CHARS.toLocaleString()}`}
        </span>
      </div>

      {fieldError && (
        <p className="mt-2 font-sans text-sm text-redline" role="alert">
          {fieldError}
        </p>
      )}

      {networkError && (
        <div className="mt-2">
          <ErrorBanner
            message={networkError}
            onDismiss={() => {
              setNetworkError(null);
              dispatch({ type: "DISMISS_ERROR" });
            }}
          />
        </div>
      )}

      <div className="mt-3 flex flex-wrap items-center gap-2">
        <Button
          variant="primary"
          disabled={!canSubmit}
          onClick={submit}
          aria-label="Challenge this request"
        >
          Challenge this request
        </Button>
        <Button variant="secondary" onClick={fillExample}>
          Use the example request
        </Button>
      </div>
    </div>
  );
}
