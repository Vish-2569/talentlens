import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useEffect } from "react";
import { FIXTURE_ANALYSIS } from "../fixtures";
import { AppProvider, useAppDispatch, useAppState } from "../state/context";
import { Decide, parseActionItems } from "../screens/Decide";
import { WorkflowStrip } from "../components/WorkflowStrip";
import { getStepStates } from "../components/workflowSteps";

// ── Fixture helpers ───────────────────────────────────────────────────────────

const MASK = "00000";
const SCENARIO = FIXTURE_ANALYSIS.redline.scenarios[MASK];
const TOP_OPTION = SCENARIO.top_option_id;
const VALID_OPTION_IDS = SCENARIO.options.map((o) => o.option_id);
const REQ_ID = FIXTURE_ANALYSIS.parsed.req_id;

function makeOkFetch(body: unknown = {}) {
  return vi.fn().mockResolvedValue({
    ok: true,
    status: 201,
    statusText: "Created",
    json: () => Promise.resolve(body),
  });
}

function make400Fetch(detail: string) {
  return vi.fn().mockResolvedValue({
    ok: false,
    status: 400,
    statusText: "Bad Request",
    json: () => Promise.resolve({ detail }),
  });
}

// Inject fixture result before rendering Decide
function Injector({ children }: { children: React.ReactNode }) {
  const dispatch = useAppDispatch();
  useEffect(() => {
    dispatch({ type: "ANALYZE_SUCCESS", payload: FIXTURE_ANALYSIS });
  }, [dispatch]);
  return <>{children}</>;
}

function renderDecide(fetchMock?: ReturnType<typeof vi.fn>) {
  if (fetchMock) globalThis.fetch = fetchMock as unknown as typeof fetch;
  return render(
    <AppProvider>
      <Injector>
        <Decide />
      </Injector>
    </AppProvider>,
  );
}

// Wrapper that renders WorkflowStrip + Decide together for step-lighting tests
function AppWithDecide() {
  const state = useAppState();
  const steps = getStepStates(state.result, state.decision !== null);
  return (
    <>
      <WorkflowStrip steps={steps} onStepClick={vi.fn()} />
      <Decide />
    </>
  );
}

function renderDecideWithStrip(fetchMock?: ReturnType<typeof vi.fn>) {
  if (fetchMock) globalThis.fetch = fetchMock as unknown as typeof fetch;
  return render(
    <AppProvider>
      <Injector>
        <AppWithDecide />
      </Injector>
    </AppProvider>,
  );
}

// Fill and submit the form
async function fillAndSubmit(user: ReturnType<typeof userEvent.setup>) {
  const approverInput = await screen.findByLabelText(/Approver/);
  const reasonInput = await screen.findByLabelText(/Reason/);
  const approveRadio = await screen.findByRole("radio", { name: "Approve" });
  await user.click(approveRadio);
  await user.type(approverInput, "Test Manager");
  await user.type(reasonInput, "Budget approved and urgency confirmed.");
  const submitBtn = screen.getByRole("button", { name: "Submit decision" });
  await user.click(submitBtn);
}

// ── Saved state ───────────────────────────────────────────────────────────────

let originalFetch: typeof globalThis.fetch;

beforeEach(() => {
  originalFetch = globalThis.fetch;
});

afterEach(() => {
  globalThis.fetch = originalFetch;
  vi.restoreAllMocks();
});

// ── parseActionItems ──────────────────────────────────────────────────────────

describe("parseActionItems", () => {
  it("parses numbered markdown list", () => {
    const md = "1. First action.\n2. Second action.\n3. Third.";
    expect(parseActionItems(md)).toEqual([
      "First action.",
      "Second action.",
      "Third.",
    ]);
  });

  it("returns empty array for empty string", () => {
    expect(parseActionItems("")).toEqual([]);
  });
});

// ── TC22: DecisionPanel ───────────────────────────────────────────────────────

describe("TC22: DecisionPanel submit disabled without all required fields", () => {
  it("submit button disabled when verb is missing", async () => {
    renderDecide();
    const approverInput = await screen.findByLabelText(/Approver/);
    const reasonInput = await screen.findByLabelText(/Reason/);
    // Fill approver and reason but not verb
    await userEvent.type(approverInput, "Manager");
    await userEvent.type(reasonInput, "Some reason");
    expect(screen.getByRole("button", { name: "Submit decision" })).toBeDisabled();
  });

  it("submit button disabled when approver is empty", async () => {
    renderDecide();
    const reasonInput = await screen.findByLabelText(/Reason/);
    const approveRadio = await screen.findByRole("radio", { name: "Approve" });
    await userEvent.click(approveRadio);
    await userEvent.type(reasonInput, "Some reason");
    // approver left blank
    expect(screen.getByRole("button", { name: "Submit decision" })).toBeDisabled();
  });

  it("submit button disabled when reason is empty", async () => {
    renderDecide();
    const approverInput = await screen.findByLabelText(/Approver/);
    const approveRadio = await screen.findByRole("radio", { name: "Approve" });
    await userEvent.click(approveRadio);
    await userEvent.type(approverInput, "Manager");
    // reason left blank
    expect(screen.getByRole("button", { name: "Submit decision" })).toBeDisabled();
  });
});

describe("TC22: 400 error message shown near the right field", () => {
  it("shows 'Reason must not be empty' near reason field on 400", async () => {
    const user = userEvent.setup();
    const fetchMock = make400Fetch("Reason must not be empty");
    renderDecide(fetchMock);

    await fillAndSubmit(user);

    const reasonError = await screen.findByRole("alert");
    expect(reasonError.textContent).toMatch(/Reason must not be empty/i);
    // Confirm the error is within the reason field area
    const reasonContainer = screen.getByLabelText(/Reason/).closest("div");
    expect(reasonContainer).toBeTruthy();
    expect(within(reasonContainer!).getByRole("alert")).toBeTruthy();
  });

  it("shows approver error near approver field on 400 with 'Approver'", async () => {
    const user = userEvent.setup();
    const fetchMock = make400Fetch("Approver name must not be empty");
    renderDecide(fetchMock);

    await fillAndSubmit(user);

    const approverError = await screen.findByRole("alert");
    expect(approverError.textContent).toMatch(/Approver name must not be empty/i);
    const approverContainer = screen.getByLabelText(/Approver/).closest("div");
    expect(within(approverContainer!).getByRole("alert")).toBeTruthy();
  });
});

describe("TC22: POST body correctness", () => {
  it("POST body contains parsed.req_id, exact state.mask, chosen verb", async () => {
    const user = userEvent.setup();
    const okResponse = {
      status: "recorded",
      req_id: REQ_ID,
      option_id: TOP_OPTION,
      verb: "Approve",
      inputs_hash: "abc123",
    };
    const fetchMock = makeOkFetch(okResponse);
    renderDecide(fetchMock);

    await fillAndSubmit(user);

    await screen.findByText("Decision recorded");

    expect(fetchMock).toHaveBeenCalledOnce();
    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    const body = JSON.parse(init.body as string);
    expect(body.req_id).toBe(REQ_ID);
    expect(body.relaxed_mask).toBe(MASK);
    expect(body.verb).toBe("Approve");
    expect(body.decided_by).toBe("Test Manager");
    expect(body.reason).toBe("Budget approved and urgency confirmed.");
  });

  it("option_id in POST body is one of scenarios[mask] options", async () => {
    const user = userEvent.setup();
    const okResponse = {
      status: "recorded",
      req_id: REQ_ID,
      option_id: TOP_OPTION,
      verb: "Approve",
    };
    const fetchMock = makeOkFetch(okResponse);
    renderDecide(fetchMock);

    await fillAndSubmit(user);
    await screen.findByText("Decision recorded");

    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    const body = JSON.parse(init.body as string);
    expect(VALID_OPTION_IDS).toContain(body.option_id);
  });
});

describe("TC22: No double POST on fast double-click", () => {
  it("only one fetch call despite two rapid submit attempts", async () => {
    const user = userEvent.setup();
    // Slow mock so button stays in sending state for both clicks
    const fetchMock = vi.fn().mockReturnValue(
      new Promise((resolve) =>
        setTimeout(
          () =>
            resolve({
              ok: true,
              status: 201,
              statusText: "Created",
              json: () =>
                Promise.resolve({
                  status: "recorded",
                  req_id: REQ_ID,
                  option_id: TOP_OPTION,
                  verb: "Approve",
                }),
            }),
          100,
        ),
      ),
    );
    renderDecide(fetchMock);

    const approverInput = await screen.findByLabelText(/Approver/);
    const reasonInput = await screen.findByLabelText(/Reason/);
    const approveRadio = await screen.findByRole("radio", { name: "Approve" });
    await user.click(approveRadio);
    await user.type(approverInput, "Manager");
    await user.type(reasonInput, "Reason for decision");

    const submitBtn = screen.getByRole("button", { name: "Submit decision" });
    // Click twice in rapid succession
    await user.click(submitBtn);
    await user.click(submitBtn);

    await screen.findByText("Decision recorded");
    // Despite two clicks, only one fetch call
    expect(fetchMock).toHaveBeenCalledOnce();
  });
});

describe("TC22: Steps 8 and 9 light after decision", () => {
  it("step 8 and 9 become lit (button) after successful submit", async () => {
    const user = userEvent.setup();
    const okResponse = {
      status: "recorded",
      req_id: REQ_ID,
      option_id: TOP_OPTION,
      verb: "Approve",
    };
    const fetchMock = makeOkFetch(okResponse);
    renderDecideWithStrip(fetchMock);

    // Before decision: step 8 is a button but shows "pending" in aria-label
    const stripBefore = screen.getByRole("navigation", {
      name: "Workflow progress",
    });
    const step8Before = within(stripBefore).getByRole("button", {
      name: /Human decision/,
    });
    expect(step8Before.getAttribute("aria-label")).toContain("pending");

    await fillAndSubmit(user);
    await screen.findByText("Decision recorded");

    // After decision: step 8 and 9 are lit buttons (no "pending" in aria-label)
    const strip = screen.getByRole("navigation", {
      name: "Workflow progress",
    });
    const step8 = within(strip).getByRole("button", { name: /Human decision/ });
    expect(step8.getAttribute("aria-label")).not.toContain("pending");

    const step9 = within(strip).getByRole("button", {
      name: /Recruiting action/,
    });
    expect(step9).toBeTruthy();
  });
});

describe("ActionsPanel", () => {
  it("renders action items from brief.actions section", async () => {
    renderDecide();
    const actionsSection = FIXTURE_ANALYSIS.brief.sections.find(
      (s) => s.key === "actions",
    );
    const items = parseActionItems(actionsSection?.markdown ?? "");

    await screen.findByLabelText(/Approver/);
    const panel = document.getElementById("actions-section")!;
    for (const item of items) {
      expect(within(panel).getByText(item)).toBeTruthy();
    }
  });

  it("labels each action card 'Draft, not sent'", async () => {
    renderDecide();
    await screen.findByLabelText(/Approver/);
    const panel = document.getElementById("actions-section")!;
    const labels = within(panel).getAllByText("Draft, not sent");
    const actionsSection = FIXTURE_ANALYSIS.brief.sections.find(
      (s) => s.key === "actions",
    );
    const items = parseActionItems(actionsSection?.markdown ?? "");
    expect(labels).toHaveLength(items.length);
  });
});
