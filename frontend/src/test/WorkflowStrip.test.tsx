import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { WorkflowStrip } from "../components/WorkflowStrip";
import { getStepStates } from "../components/workflowSteps";
import { FIXTURE_ANALYSIS } from "../fixtures";

describe("getStepStates (pure function)", () => {
  it("all steps unlit when result is null", () => {
    const steps = getStepStates(null, false);
    expect(steps.every((s) => !s.lit)).toBe(true);
  });

  it("steps 1-7 lit and 8-9 unlit when analysis exists but no decision", () => {
    const steps = getStepStates(FIXTURE_ANALYSIS, false);
    // Steps 1–7 should be lit
    for (let i = 1; i <= 7; i++) {
      expect(steps[i - 1].lit, `step ${i} should be lit`).toBe(true);
    }
    // Steps 8 and 9 require a decision
    expect(steps[7].lit).toBe(false); // step 8
    expect(steps[8].lit).toBe(false); // step 9
  });

  it("step 8 lights only after decisionRecorded=true", () => {
    const stepsAfter = getStepStates(FIXTURE_ANALYSIS, true);
    expect(stepsAfter[7].lit).toBe(true);
  });

  it("step 9 lights only after decisionRecorded=true and brief.sections non-empty", () => {
    const stepsAfter = getStepStates(FIXTURE_ANALYSIS, true);
    expect(stepsAfter[8].lit).toBe(true);
  });

  it("step 9 does not light when brief has no sections", () => {
    const resultNoBrief = {
      ...FIXTURE_ANALYSIS,
      brief: { ...FIXTURE_ANALYSIS.brief, sections: [] },
    };
    const steps = getStepStates(resultNoBrief, true);
    expect(steps[8].lit).toBe(false);
  });

  it("step 4 lights only when contractor_cards is non-empty", () => {
    const withContractors = getStepStates(FIXTURE_ANALYSIS, false);
    expect(withContractors[3].lit).toBe(true);

    const noContractors = {
      ...FIXTURE_ANALYSIS,
      options: { ...FIXTURE_ANALYSIS.options, contractor_cards: [] },
    };
    const withoutContractors = getStepStates(noContractors, false);
    expect(withoutContractors[3].lit).toBe(false);
  });

  it("returns exactly 9 steps with correct ids", () => {
    const steps = getStepStates(null, false);
    expect(steps).toHaveLength(9);
    expect(steps.map((s) => s.id)).toEqual([1, 2, 3, 4, 5, 6, 7, 8, 9]);
  });

  it("lit steps have challenge tab for steps 1-2, options for steps 3-7, decide for steps 8-9", () => {
    const steps = getStepStates(FIXTURE_ANALYSIS, true);
    expect(steps[0].tab).toBe("challenge");
    expect(steps[1].tab).toBe("challenge");
    for (let i = 2; i <= 6; i++) expect(steps[i].tab).toBe("options");
    expect(steps[7].tab).toBe("decide");
    expect(steps[8].tab).toBe("decide");
  });
});

describe("WorkflowStrip component", () => {
  it("renders 9 steps", () => {
    const steps = getStepStates(null, false);
    render(<WorkflowStrip steps={steps} onStepClick={vi.fn()} />);
    const listItems = screen.getAllByRole("listitem");
    expect(listItems).toHaveLength(9);
  });

  it("lit steps render as buttons, unlit steps render as spans", () => {
    const steps = getStepStates(FIXTURE_ANALYSIS, false);
    render(<WorkflowStrip steps={steps} onStepClick={vi.fn()} />);
    // Steps 1-7 are lit → buttons
    const buttons = screen.getAllByRole("button");
    expect(buttons.length).toBeGreaterThanOrEqual(7);
  });

  it("unlit steps include '(pending)' visually hidden text", () => {
    const steps = getStepStates(null, false);
    render(<WorkflowStrip steps={steps} onStepClick={vi.fn()} />);
    const pendingTexts = screen.getAllByText("(pending)");
    expect(pendingTexts).toHaveLength(9);
  });

  it("clicking a lit step calls onStepClick with the step", async () => {
    const user = userEvent.setup();
    const handler = vi.fn();
    const steps = getStepStates(FIXTURE_ANALYSIS, false);
    render(<WorkflowStrip steps={steps} onStepClick={handler} />);

    const firstButton = screen.getAllByRole("button")[0];
    await user.click(firstButton);
    expect(handler).toHaveBeenCalledOnce();
    expect(handler.mock.calls[0][0].id).toBe(1);
  });
});
