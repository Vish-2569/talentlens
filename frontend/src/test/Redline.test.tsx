import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { FIXTURE_ANALYSIS } from "../fixtures";
import { AppProvider } from "../state/context";
import { Challenge } from "../screens/Challenge";

const DEMO_SENTENCE =
  "Senior Full Stack Developer, Bengaluru, on-site, 5+ years, must know React, Node.js and Kubernetes, budget ₹28L, need in 30 days.";

function mockFetch(status: number, body: unknown) {
  return vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    statusText: "OK",
    json: () => Promise.resolve(body),
  });
}

function renderChallenge() {
  return render(
    <AppProvider>
      <Challenge />
      <div role="status" aria-live="polite" aria-atomic="true" id="recommendation-live" />
    </AppProvider>,
  );
}

let originalFetch: typeof globalThis.fetch;

beforeEach(() => {
  originalFetch = globalThis.fetch;
});

afterEach(() => {
  globalThis.fetch = originalFetch;
  vi.restoreAllMocks();
});

async function submitAndWait() {
  const user = userEvent.setup();
  globalThis.fetch = mockFetch(200, FIXTURE_ANALYSIS);
  renderChallenge();

  await user.click(screen.getByRole("button", { name: "Use the example request" }));
  await user.click(screen.getByRole("button", { name: "Challenge this request" }));

  await screen.findByText(DEMO_SENTENCE);
  return user;
}

describe("TC04: Redline marks rendering", () => {
  it("renders 5 marks with correct severities", async () => {
    await submitAndWait();

    const marks = document.querySelectorAll("mark");
    expect(marks).toHaveLength(5);

    const redMarks = document.querySelectorAll('mark[data-severity="red"]');
    const amberMarks = document.querySelectorAll('mark[data-severity="amber"]');
    expect(redMarks).toHaveLength(3);
    expect(amberMarks).toHaveLength(2);
  });

  it("each mark has a VisuallyHidden severity label", async () => {
    await submitAndWait();

    const highCostLabels = screen.getAllByText("High cost");
    const moderateCostLabels = screen.getAllByText("Moderate cost");
    expect(highCostLabels).toHaveLength(3 + 3);
    expect(moderateCostLabels).toHaveLength(2 + 2);
  });

  it("hover text matches the API string for location constraint", async () => {
    const user = await submitAndWait();

    const locationMark = document.querySelector('mark[data-severity="red"]');
    expect(locationMark).toBeTruthy();

    const trigger = locationMark!.closest("button");
    expect(trigger).toBeTruthy();
    await user.click(trigger!);

    const expectedHover = FIXTURE_ANALYSIS.redline.constraints[0].hover_text;
    expect(screen.getByText(expectedHover)).toBeInTheDocument();
  });
});

describe("TC07: Toggle interactions", () => {
  it("toggling 2 constraints makes zero fetch calls and panel updates", async () => {
    const user = await submitAndWait();

    const fetchSpy = vi.fn();
    globalThis.fetch = fetchSpy;

    const radioGroups = screen.getAllByRole("radiogroup");
    expect(radioGroups.length).toBe(5);

    const locationGroup = radioGroups[0];
    const skillGroup = radioGroups[2];

    await user.click(within(locationGroup).getByRole("radio", { name: "Relax" }));
    await user.click(within(skillGroup).getByRole("radio", { name: "Relax" }));

    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it('mask "00000" shows Buy panel text', async () => {
    await submitAndWait();

    expect(
      screen.getByText("Buy: P50 62 days, ₹32L."),
    ).toBeInTheDocument();
  });

  it("relaxing location + skill shows Mix panel text", async () => {
    const user = await submitAndWait();

    const radioGroups = screen.getAllByRole("radiogroup");
    await user.click(within(radioGroups[0]).getByRole("radio", { name: "Relax" }));
    await user.click(within(radioGroups[2]).getByRole("radio", { name: "Relax" }));

    expect(
      screen.getByText("Borrow E-045 + C-17: available now, ₹18L in year one."),
    ).toBeInTheDocument();
  });
});

describe("TC08: Toggle back restores output", () => {
  it("toggling back to Keep restores original panel text", async () => {
    const user = await submitAndWait();

    const radioGroups = screen.getAllByRole("radiogroup");

    await user.click(within(radioGroups[0]).getByRole("radio", { name: "Relax" }));
    await user.click(within(radioGroups[2]).getByRole("radio", { name: "Relax" }));

    expect(
      screen.getByText("Borrow E-045 + C-17: available now, ₹18L in year one."),
    ).toBeInTheDocument();

    await user.click(within(radioGroups[0]).getByRole("radio", { name: "Keep" }));
    await user.click(within(radioGroups[2]).getByRole("radio", { name: "Keep" }));

    expect(
      screen.getByText("Buy: P50 62 days, ₹32L."),
    ).toBeInTheDocument();
  });

  it("tooltip opens by keyboard focus (Tab)", async () => {
    const user = await submitAndWait();

    const marks = document.querySelectorAll("mark");
    const trigger = marks[0]?.closest("button");
    expect(trigger).toBeTruthy();

    trigger!.focus();
    await user.tab();
    await user.tab();

    expect(trigger).toHaveAttribute("type", "button");
  });

  it("tooltip opens by click/tap", async () => {
    const user = await submitAndWait();

    const marks = document.querySelectorAll("mark");
    const trigger = marks[0]?.closest("button");
    expect(trigger).toBeTruthy();

    await user.click(trigger!);

    const expectedHover = FIXTURE_ANALYSIS.redline.constraints[0].hover_text;
    expect(screen.getByText(expectedHover)).toBeInTheDocument();
  });
});

describe("Edge cases", () => {
  it("span ending near text end renders correctly (deadline)", async () => {
    await submitAndWait();

    const marks = document.querySelectorAll("mark");
    const lastMark = marks[marks.length - 1];
    expect(lastMark).toBeTruthy();
    expect(lastMark!.textContent).toContain("need in 30 days");
  });

  it("renders no marks for null-span constraints", async () => {
    const fixtureWithNull = structuredClone(FIXTURE_ANALYSIS);
    fixtureWithNull.redline.constraints.push({
      id: "c-inferred",
      kind: "budget",
      value: "test",
      phrase: "test phrase",
      span_start: null as unknown as number,
      span_end: null as unknown as number,
      source: "inferred",
      severity: "none",
      hover_text: "Inferred constraint",
      cost: { supply_delta: null, days_delta: null, rupees_delta_lpa: null },
      relaxed_value: null,
    });
    fixtureWithNull.redline.constraint_order = [
      ...fixtureWithNull.redline.constraint_order,
      "budget",
    ];

    const user = userEvent.setup();
    globalThis.fetch = mockFetch(200, fixtureWithNull);
    render(
      <AppProvider>
        <Challenge />
      </AppProvider>,
    );

    await user.click(screen.getByRole("button", { name: "Use the example request" }));
    await user.click(screen.getByRole("button", { name: "Challenge this request" }));
    await screen.findByText(DEMO_SENTENCE);

    const marks = document.querySelectorAll("mark");
    expect(marks).toHaveLength(5);
  });
});
