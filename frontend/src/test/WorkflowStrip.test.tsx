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

  it("lit steps have challenge tab for steps 1-2, options for steps 3-7, decide for steps 8-9", () => {
    const steps = getStepStates(FIXTURE_ANALYSIS, true);
    expect(steps[0].tab).toBe("challenge");
    expect(steps[1].tab).toBe("challenge");
    for (let i = 2; i <= 6; i++) expect(steps[i].tab).toBe("options");
    expect(steps[7].tab).toBe("decide");
    expect(steps[8].tab).toBe("decide");
  });
});

describe("STEP_DEFS target mapping", () => {
  const expected: { id: number; tab: string; scrollTarget: string }[] = [
    { id: 1, tab: "challenge", scrollTarget: "challenge-input" },
    { id: 2, tab: "challenge", scrollTarget: "redline-section" },
    { id: 3, tab: "options", scrollTarget: "ripple-section" },
    { id: 4, tab: "options", scrollTarget: "contractor-section" },
    { id: 5, tab: "options", scrollTarget: "market-section" },
    { id: 6, tab: "options", scrollTarget: "relocate-section" },
    { id: 7, tab: "options", scrollTarget: "options-section" },
    { id: 8, tab: "decide", scrollTarget: "decision-form" },
    { id: 9, tab: "decide", scrollTarget: "actions-section" },
  ];

  for (const { id, tab, scrollTarget } of expected) {
    it(`step ${id} targets tab "${tab}" and scrolls to "${scrollTarget}"`, () => {
      const def = STEP_DEFS.find((d) => d.id === id);
      expect(def).toBeDefined();
      expect(def!.tab).toBe(tab);
      expect(def!.scrollTarget).toBe(scrollTarget);
    });
  }
});

describe("WorkflowStrip component", () => {
  it("renders 9 steps", () => {
    const steps = getStepStates(null, false);
    render(<WorkflowStrip steps={steps} onStepClick={vi.fn()} />);
    const listItems = screen.getAllByRole("listitem");
    expect(listItems).toHaveLength(9);
  });

  it("lit steps render as buttons", () => {
    const steps = getStepStates(FIXTURE_ANALYSIS, false);
    render(<WorkflowStrip steps={steps} onStepClick={vi.fn()} />);
    const buttons = screen.getAllByRole("button");
    // Steps 1-7 lit + steps 8-9 always clickable = 9
    expect(buttons.length).toBe(9);
  });

  it("steps 8-9 are always buttons even when unlit", () => {
    const steps = getStepStates(FIXTURE_ANALYSIS, false);
    // steps 8 and 9 are unlit but still buttons
    expect(steps[7].lit).toBe(false);
    expect(steps[8].lit).toBe(false);
    render(<WorkflowStrip steps={steps} onStepClick={vi.fn()} />);
    const buttons = screen.getAllByRole("button");
    const labels = buttons.map((b) => b.getAttribute("aria-label") ?? "");
    expect(labels.some((l) => l.includes("pending: approve on Decide"))).toBe(
      true,
    );
  });

  it("unlit non-decide steps include '(pending)' visually hidden text", () => {
    const steps = getStepStates(null, false);
    render(<WorkflowStrip steps={steps} onStepClick={vi.fn()} />);
    // Steps 1-7 are unlit non-decide → show (pending)
    const pendingTexts = screen.getAllByText("(pending)");
    expect(pendingTexts.length).toBe(7);
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

  it("clicking unlit step 8 calls onStepClick with decide tab", async () => {
    const user = userEvent.setup();
    const handler = vi.fn();
    const steps = getStepStates(FIXTURE_ANALYSIS, false);
    render(<WorkflowStrip steps={steps} onStepClick={handler} />);

    const buttons = screen.getAllByRole("button");
    // Step 8 should be at index 7 (0-based)
    const step8 = buttons.find((b) =>
      b.getAttribute("aria-label")?.includes("Human decision"),
    );
    expect(step8).toBeDefined();
    await user.click(step8!);
    expect(handler).toHaveBeenCalledOnce();
    const clickedStep = handler.mock.calls[0][0];
    expect(clickedStep.id).toBe(8);
    expect(clickedStep.tab).toBe("decide");
    expect(clickedStep.scrollTarget).toBe("decision-form");
  });

  it("clicking unlit step 9 calls onStepClick targeting actions-section", async () => {
    const user = userEvent.setup();
    const handler = vi.fn();
    const steps = getStepStates(FIXTURE_ANALYSIS, false);
    render(<WorkflowStrip steps={steps} onStepClick={handler} />);

    const buttons = screen.getAllByRole("button");
    const step9 = buttons.find((b) =>
      b.getAttribute("aria-label")?.includes("Recruiting action"),
    );
    expect(step9).toBeDefined();
    await user.click(step9!);
    expect(handler).toHaveBeenCalledOnce();
    const clickedStep = handler.mock.calls[0][0];
    expect(clickedStep.id).toBe(9);
    expect(clickedStep.tab).toBe("decide");
    expect(clickedStep.scrollTarget).toBe("actions-section");
  });

  it("uses short labels in visible text", () => {
    const steps = getStepStates(FIXTURE_ANALYSIS, false);
    render(<WorkflowStrip steps={steps} onStepClick={vi.fn()} />);
    // Short labels should be visible
    expect(screen.getByText("Need")).toBeDefined();
    expect(screen.getByText("Skills")).toBeDefined();
    expect(screen.getByText("Internal")).toBeDefined();
    expect(screen.getByText("Market")).toBeDefined();
    expect(screen.getByText("Options")).toBeDefined();
    expect(screen.getByText("Decision")).toBeDefined();
    expect(screen.getByText("Action")).toBeDefined();
  });
});
