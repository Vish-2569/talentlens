import { useState, useRef } from "react";
import type { FormEvent } from "react";
import { Button } from "./ui";
import { useAppState, useAppDispatch, currentScenario } from "../state/context";
import { postDecision, ApiError } from "../api/client";
import { describeMaskNote } from "../screens/Options";
import type { components } from "../api/types";

type ConstraintKind = components["schemas"]["ConstraintKind"];
type Constraint = components["schemas"]["Constraint"];
type DecisionVerb = components["schemas"]["DecisionVerb"];
type OptionSummary = components["schemas"]["OptionSummary"];

interface DecisionConfirm {
  status: string;
  req_id: string;
  option_id: string;
  verb: string;
  inputs_hash?: string;
}

export function DecisionPanel() {
  const state = useAppState();
  const dispatch = useAppDispatch();
  const { result, mask } = state;
  const scenario = currentScenario(state);

  const constraintOrder = result!.redline.constraint_order as ConstraintKind[];
  const constraints = result!.redline.constraints as Constraint[];
  const { assumeText, keptText } = describeMaskNote(mask, constraintOrder, constraints);

  const scenarioOptions: OptionSummary[] = scenario?.options ?? [];
  const defaultOptionId = scenario?.top_option_id ?? scenarioOptions[0]?.option_id ?? "";

  const [selectedOption, setSelectedOption] = useState(defaultOptionId);
  const [verb, setVerb] = useState<DecisionVerb | "">("");
  const [approver, setApprover] = useState("");
  const [reason, setReason] = useState("");
  const [sending, setSending] = useState(false);
  const [confirm, setConfirm] = useState<DecisionConfirm | null>(null);
  const [generalError, setGeneralError] = useState<string | null>(null);
  const [approverError, setApproverError] = useState<string | null>(null);
  const [reasonError, setReasonError] = useState<string | null>(null);

  const submitGuard = useRef(false);

  const canSubmit =
    verb !== "" && approver.trim() !== "" && reason.trim() !== "" && !sending;

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!canSubmit) return;
    if (submitGuard.current) return;
    submitGuard.current = true;
    setSending(true);
    setGeneralError(null);
    setApproverError(null);
    setReasonError(null);

    try {
      const body = {
        req_id: result!.parsed.req_id,
        option_id: selectedOption,
        verb: verb as DecisionVerb,
        decided_by: approver,
        relaxed_mask: mask,
        reason,
      };
      const res = await postDecision(body);
      const typed = res as unknown as DecisionConfirm;
      setConfirm(typed);
      dispatch({
        type: "RECORD_DECISION",
        payload: {
          req_id: result!.parsed.req_id,
          option_id: selectedOption,
          verb: verb as DecisionVerb,
          decided_by: approver,
          relaxed_mask: mask,
          reason,
          recorded_at: new Date().toISOString(),
        },
      });
    } catch (err) {
      submitGuard.current = false;
      if (err instanceof ApiError) {
        const msg = err.message;
        if (err.fieldErrors && err.fieldErrors.length > 0) {
          for (const fe of err.fieldErrors) {
            const loc = fe.loc.join(".");
            if (loc.includes("reason")) {
              setReasonError(fe.msg);
            } else if (loc.includes("decided_by")) {
              setApproverError(fe.msg);
            } else {
              setGeneralError(fe.msg);
            }
          }
        } else if (msg.toLowerCase().includes("reason")) {
          setReasonError(msg);
        } else if (
          msg.toLowerCase().includes("approver") ||
          msg.toLowerCase().includes("decided_by")
        ) {
          setApproverError(msg);
        } else {
          setGeneralError(msg);
        }
      } else {
        setGeneralError("An unexpected error occurred.");
      }
    } finally {
      setSending(false);
    }
  }

  if (confirm) {
    const optName =
      scenarioOptions.find((o) => o.option_id === confirm.option_id)?.name ??
      confirm.option_id;
    const timestamp = new Date().toLocaleString();
    return (
      <div
        id="decision-form"
        role="region"
        aria-labelledby="decision-record-heading"
        className="space-y-3 rounded border border-hairline bg-surface p-4"
      >
        <h3
          id="decision-record-heading"
          className="font-serif text-base font-semibold"
        >
          Decision recorded
        </h3>
        <dl className="space-y-1 font-sans text-sm">
          <div className="flex gap-2">
            <dt className="font-medium">Verb:</dt>
            <dd>{confirm.verb}</dd>
          </div>
          <div className="flex gap-2">
            <dt className="font-medium">Option:</dt>
            <dd>{optName}</dd>
          </div>
          <div className="flex gap-2">
            <dt className="font-medium">Approver:</dt>
            <dd>{approver}</dd>
          </div>
          <div className="flex gap-2">
            <dt className="font-medium">Reason:</dt>
            <dd>{reason}</dd>
          </div>
          <div className="flex gap-2">
            <dt className="font-medium">Timestamp:</dt>
            <dd>{timestamp}</dd>
          </div>
          {confirm.inputs_hash && (
            <div className="flex gap-2">
              <dt className="font-medium">Inputs hash:</dt>
              <dd className="break-all font-mono text-xs">
                {confirm.inputs_hash}
              </dd>
            </div>
          )}
        </dl>
      </div>
    );
  }

  return (
    <form
      id="decision-form"
      onSubmit={handleSubmit}
      aria-labelledby="decision-form-heading"
      className="space-y-4 rounded border border-hairline bg-surface p-4"
      noValidate
    >
      <h3 id="decision-form-heading" className="font-serif text-base font-semibold">
        Record decision
      </h3>

      <p className="font-sans text-xs text-muted">
        Deciding for scenario: {assumeText}.
        {keptText ? ` Kept: ${keptText}.` : ""}
      </p>

      <div className="space-y-1">
        <label
          htmlFor="decision-option"
          className="block font-sans text-sm font-medium"
        >
          Option
        </label>
        <select
          id="decision-option"
          value={selectedOption}
          onChange={(e) => setSelectedOption(e.target.value)}
          className="w-full rounded border border-hairline bg-paper px-2 py-1.5 font-sans text-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
        >
          {scenarioOptions.map((opt) => (
            <option key={opt.option_id} value={opt.option_id}>
              {opt.name}
            </option>
          ))}
        </select>
      </div>

      <fieldset className="space-y-1">
        <legend className="font-sans text-sm font-medium">Decision</legend>
        {(["Approve", "Modify", "Reject"] as DecisionVerb[]).map((v) => (
          <label
            key={v}
            className="flex cursor-pointer items-center gap-2 font-sans text-sm"
          >
            <input
              type="radio"
              name="verb"
              value={v}
              checked={verb === v}
              onChange={() => setVerb(v)}
              className="focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
            />
            {v}
          </label>
        ))}
      </fieldset>

      <div className="space-y-1">
        <label
          htmlFor="decision-approver"
          className="block font-sans text-sm font-medium"
        >
          Approver{" "}
          <span className="text-red" aria-hidden="true">
            *
          </span>
        </label>
        <input
          id="decision-approver"
          type="text"
          value={approver}
          onChange={(e) => {
            setApprover(e.target.value);
            setApproverError(null);
          }}
          aria-required="true"
          aria-describedby={approverError ? "approver-error" : undefined}
          aria-invalid={approverError ? true : undefined}
          className="w-full rounded border border-hairline bg-paper px-2 py-1.5 font-sans text-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
        />
        {approverError && (
          <p
            id="approver-error"
            role="alert"
            className="font-sans text-xs text-red"
          >
            {approverError}
          </p>
        )}
      </div>

      <div className="space-y-1">
        <label
          htmlFor="decision-reason"
          className="block font-sans text-sm font-medium"
        >
          Reason{" "}
          <span className="text-red" aria-hidden="true">
            *
          </span>
        </label>
        <textarea
          id="decision-reason"
          value={reason}
          onChange={(e) => {
            setReason(e.target.value);
            setReasonError(null);
          }}
          rows={3}
          aria-required="true"
          aria-describedby={reasonError ? "reason-error" : undefined}
          aria-invalid={reasonError ? true : undefined}
          className="w-full rounded border border-hairline bg-paper px-2 py-1.5 font-sans text-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
        />
        {reasonError && (
          <p
            id="reason-error"
            role="alert"
            className="font-sans text-xs text-red"
          >
            {reasonError}
          </p>
        )}
      </div>

      {generalError && (
        <p role="alert" className="font-sans text-xs text-red">
          {generalError}
        </p>
      )}

      <Button type="submit" disabled={!canSubmit} aria-busy={sending}>
        {sending ? "Submitting…" : "Submit decision"}
      </Button>
    </form>
  );
}
