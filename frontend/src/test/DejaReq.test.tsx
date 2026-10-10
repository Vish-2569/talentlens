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

describe("TC01: DejaReq banner and timeline", () => {
  it("banner shows the exact banner_text from the fixture", async () => {
    await submitAndWait();

    expect(
      screen.getByText(FIXTURE_ANALYSIS.dejareq.banner_text!),
    ).toBeInTheDocument();
  });

  it("timeline has 4 rows, newest first", async () => {
    await submitAndWait();

    const user = userEvent.setup();
    const banner = screen.getByRole("button", { name: /hired a Senior/i });
    await user.click(banner);

    const timeline = screen.getByRole("list", { name: "Requisition history" });
    const rows = within(timeline).getAllByRole("listitem");
    expect(rows).toHaveLength(4);

    const dates = rows.map(
      (r) => within(r).getByTestId("timeline-date").textContent,
    );
    expect(dates).toEqual(["Jun 2026", "Mar 2026", "Oct 2025", "Nov 2024"]);
  });

  it("timeline rows show decision type and outcome text", async () => {
    await submitAndWait();

    const user = userEvent.setup();
    const banner = screen.getByRole("button", { name: /hired a Senior/i });
    await user.click(banner);

    const timeline = screen.getByRole("list", { name: "Requisition history" });
    const rows = within(timeline).getAllByRole("listitem");

    expect(within(rows[0]).getByText("Build")).toBeInTheDocument();
    expect(within(rows[0]).getByText("Still in role, rated Exceeds")).toBeInTheDocument();

    expect(within(rows[1]).getByText("Borrow")).toBeInTheDocument();
    expect(within(rows[1]).getByText("Contract ended, knowledge lost")).toBeInTheDocument();

    expect(within(rows[2]).getByText("Buy")).toBeInTheDocument();
    expect(within(rows[2]).getByText("Left after 7 months (counter offer)")).toBeInTheDocument();

    expect(within(rows[3]).getByText("Buy")).toBeInTheDocument();
    expect(within(rows[3]).getByText("Left after 9 months (role mismatch)")).toBeInTheDocument();
  });
});

describe("TC02: match_count variants", () => {
  it("match_count=1 shows chip, not banner", async () => {
    const oneMatch = structuredClone(FIXTURE_ANALYSIS);
    oneMatch.dejareq.match_count = 1;
    oneMatch.dejareq.banner_text = null;
    oneMatch.dejareq.chip = "Seen once before";
    oneMatch.dejareq.timeline = [oneMatch.dejareq.timeline[0]];
    oneMatch.dejareq.patterns = [];
    oneMatch.dejareq.insight_text = null;

    const user = userEvent.setup();
    globalThis.fetch = mockFetch(200, oneMatch);
    renderChallenge();

    await user.click(screen.getByRole("button", { name: "Use the example request" }));
    await user.click(screen.getByRole("button", { name: "Challenge this request" }));
    await screen.findByText(DEMO_SENTENCE);

    expect(screen.getByText("Seen once before")).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /hired a Senior/i }),
    ).not.toBeInTheDocument();
  });

  it("match_count=0 shows nothing", async () => {
    const noMatch = structuredClone(FIXTURE_ANALYSIS);
    noMatch.dejareq.match_count = 0;
    noMatch.dejareq.banner_text = null;
    noMatch.dejareq.chip = null;
    noMatch.dejareq.timeline = [];
    noMatch.dejareq.patterns = [];
    noMatch.dejareq.insight_text = null;

    const user = userEvent.setup();
    globalThis.fetch = mockFetch(200, noMatch);
    renderChallenge();

    await user.click(screen.getByRole("button", { name: "Use the example request" }));
    await user.click(screen.getByRole("button", { name: "Challenge this request" }));
    await screen.findByText(DEMO_SENTENCE);

    expect(screen.queryByTestId("dejareq-section")).not.toBeInTheDocument();
  });
});

describe("TC03: Patterns and risk effects", () => {
  it("churn pattern shows risk effect text", async () => {
    await submitAndWait();

    const user = userEvent.setup();
    const banner = screen.getByRole("button", { name: /hired a Senior/i });
    await user.click(banner);

    expect(screen.getByText("Buy risk +0.20")).toBeInTheDocument();
    expect(
      screen.getByText("churn pattern: 2 external hires left in avg 8 months"),
    ).toBeInTheDocument();
  });

  it("timeline rows are readable without colour (outcome text present)", async () => {
    await submitAndWait();

    const user = userEvent.setup();
    const banner = screen.getByRole("button", { name: /hired a Senior/i });
    await user.click(banner);

    const timeline = screen.getByRole("list", { name: "Requisition history" });
    const rows = within(timeline).getAllByRole("listitem");

    for (const row of rows) {
      const outcomeEl = within(row).getByTestId("timeline-outcome");
      expect(outcomeEl.textContent).toBeTruthy();
    }
  });
});
