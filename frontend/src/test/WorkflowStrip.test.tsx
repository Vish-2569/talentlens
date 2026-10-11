import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { WorkflowStrip } from "../components/WorkflowStrip";
import { getStepStates, STEP_DEFS } from "../components/workflowSteps";
import { FIXTURE_ANALYSIS } from "../fixtures";

describe("TC37: Workflow strip — 9 data groups present in fixture", () => {
  it("fixture has all 9 data groups that light the 9 steps", () => {
    expect(FIXTURE_ANALYSIS.parsed).toBeTruthy(); // step 1
    expect(FIXTURE_ANALYSIS.redline).toBeTruthy(); // step 2
    expect(FIXTURE_ANALYSIS.ripple.candidates.length).toBeGreaterThan(0); // step 3
    expect(FIXTURE_ANALYSIS.options.contractor_cards.length).toBeGreaterThan(0); // step 4
    expect(FIXTURE_ANALYSIS.options.market_card).toBeTruthy(); // step 5
    expect(FIXTURE_ANALYSIS.options.relocate_card.length).toBeGreaterThan(0); // step 6
    expect(FIXTURE_ANALYSIS.options.five.length).toBeGreaterThan(0); // step 7
    // steps 8/9 require a decision (tested below)
    expect(FIXTURE_ANALYSIS.brief.sections.length).toBeGreaterThan(0); // step 9 data
  });

  it("steps 1-7 light when fixture is loaded; 8-9 light after decision", () => {
    const before = getStepStates(FIXTURE_ANALYSIS, false);
    for (let i = 0; i < 7; i++) {
      expect(before[i].lit, `step ${i + 1} lit`).toBe(true);
    }
    expect(before[7].lit).toBe(false);
    expect(before[8].lit).toBe(false);

    const after = getStepStates(FIXTURE_ANALYSIS, true);
    expect(after[7].lit).toBe(true);
    expect(after[8].lit).toBe(true);
  });
});

describe("getStepStates (pure function)", () => {
  it("all steps unlit when result is null", () => {
    const steps = getStepStates(null, false);
    expect(steps.every((s) => !s.lit)).toBe(true);
  });

  it("steps 2-9 disabled when result is null", () => {
    const steps = getStepStates(null, false);
    expect(steps[0].disabled).toBe(false);
    for (let i = 1; i < 9; i++) {
      expect(steps[i].disabled, `step ${i + 1} disabled`).toBe(true);
    }
  });

  it("no steps disabled when result exists", () => {
    const steps = getStepStates(FIXTURE_ANALYSIS, false);
    for (const s of steps) {
      expect(s.disabled, `step ${s.id} not disabled`).toBe(false);
    }
  });

  it("steps 1-7 lit and 8-9 unlit when analysis exists but no decision", () => {
    const steps = getStepStates(FIXTURE_ANALYSIS, false);
    for (let i = 1; i <= 7; i++) {
      expect(steps[i - 1].lit, `step ${i} should be lit`).toBe(true);
    }
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

  it("each step has a headingId", () => {
    const steps = getStepStates(null, false);
    for (const s of steps) {
      expect(s.headingId).toBe(`step-${s.id}-heading`);
    }
  });
});

describe("STEP_DEFS target mapping", () => {
  const expected: { id: number; headingId: string }[] = [
    { id: 1, headingId: "step-1-heading" },
    { id: 2, headingId: "step-2-heading" },
    { id: 3, headingId: "step-3-heading" },
    { id: 4, headingId: "step-4-heading" },
    { id: 5, headingId: "step-5-heading" },
    { id: 6, headingId: "step-6-heading" },
    { id: 7, headingId: "step-7-heading" },
    { id: 8, headingId: "step-8-heading" },
    { id: 9, headingId: "step-9-heading" },
  ];

  for (const { id, headingId } of expected) {
    it(`step ${id} targets heading "${headingId}"`, () => {
      const def = STEP_DEFS.find((d) => d.id === id);
      expect(def).toBeDefined();
      expect(def!.headingId).toBe(headingId);
    });
  }
});

describe("WorkflowStrip component", () => {
  it("renders 9 steps", () => {
    const steps = getStepStates(null, false);
    render(<WorkflowStrip steps={steps} activeStep={1} onStepClick={vi.fn()} />);
    const listItems = screen.getAllByRole("listitem");
    expect(listItems).toHaveLength(9);
  });

  it("active step has aria-current=step", () => {
    const steps = getStepStates(FIXTURE_ANALYSIS, false);
    render(<WorkflowStrip steps={steps} activeStep={3} onStepClick={vi.fn()} />);
    const buttons = screen.getAllByRole("button");
    const current = buttons.find(
      (b) => b.getAttribute("aria-current") === "step",
    );
    expect(current).toBeDefined();
    expect(current!.getAttribute("aria-label")).toContain("Internal talent");
  });

  it("disabled steps render as spans, not buttons", () => {
    const steps = getStepStates(null, false);
    render(<WorkflowStrip steps={steps} activeStep={1} onStepClick={vi.fn()} />);
    const buttons = screen.getAllByRole("button");
    // Only step 1 should be a button (step 1 is never disabled)
    expect(buttons).toHaveLength(1);
  });

  it("enabled steps render as buttons after analysis", () => {
    const steps = getStepStates(FIXTURE_ANALYSIS, false);
    render(<WorkflowStrip steps={steps} activeStep={1} onStepClick={vi.fn()} />);
    const buttons = screen.getAllByRole("button");
    expect(buttons).toHaveLength(9);
  });

  it("clicking a step calls onStepClick with the step", async () => {
    const user = userEvent.setup();
    const handler = vi.fn();
    const steps = getStepStates(FIXTURE_ANALYSIS, false);
    render(<WorkflowStrip steps={steps} activeStep={1} onStepClick={handler} />);

    const firstButton = screen.getAllByRole("button")[0];
    await user.click(firstButton);
    expect(handler).toHaveBeenCalledOnce();
    expect(handler.mock.calls[0][0].id).toBe(1);
  });

  it("uses short labels in visible text", () => {
    const steps = getStepStates(FIXTURE_ANALYSIS, false);
    render(<WorkflowStrip steps={steps} activeStep={1} onStepClick={vi.fn()} />);
    expect(screen.getByText("Need")).toBeDefined();
    expect(screen.getByText("Skills")).toBeDefined();
    expect(screen.getByText("Internal")).toBeDefined();
    expect(screen.getByText("Market")).toBeDefined();
    expect(screen.getByText("Options")).toBeDefined();
    expect(screen.getByText("Decision")).toBeDefined();
    expect(screen.getByText("Action")).toBeDefined();
  });
});
