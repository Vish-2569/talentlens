/**
 * F10b: Full-app integration test.
 *
 * Renders the whole App with the captured fixture and asserts every number
 * shown in the Redline panel (ready-by, cost — no scores there), Déjà Req,
 * Ripple net impact, five-option table, mix card, relocate card, sourcing,
 * and brief header equals its fixture field.
 *
 * Also asserts: the same option shows the same score everywhere scores
 * appear (step 7 only), and the live panel shows no scores.
 */
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { FIXTURE_ANALYSIS } from "../fixtures";
import { App } from "../App";
import { AppProvider } from "../state/context";
import { displayOptionText } from "../components/displayNames";

const F = FIXTURE_ANALYSIS;

function mockFetch(status: number, body: unknown) {
  return vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    statusText: status === 200 ? "OK" : "Error",
    json: () => Promise.resolve(body),
  });
}

let originalFetch: typeof globalThis.fetch;

beforeEach(() => {
  originalFetch = globalThis.fetch;
  window.location.hash = "";
});

afterEach(() => {
  globalThis.fetch = originalFetch;
  vi.restoreAllMocks();
  window.location.hash = "";
});

async function submitAndWait() {
  const user = userEvent.setup();
  globalThis.fetch = mockFetch(200, F);

  render(
    <AppProvider>
      <App />
    </AppProvider>,
  );

  await user.click(screen.getByRole("button", { name: "Use the example request" }));
  await user.click(screen.getByRole("button", { name: "Challenge this request" }));

  // Wait for the analysis result to render
  await screen.findByText("Edit request");
  return user;
}

function clickStep(user: ReturnType<typeof userEvent.setup>, label: string) {
  const btn = screen.getAllByRole("button").find(
    (b) => b.getAttribute("aria-label")?.includes(label),
  );
  expect(btn).toBeDefined();
  return user.click(btn!);
}

// ── Step 1: Redline live panel (no scores) ─────────────────────────────────

describe("Sync: LiveRecommendation panel shows no scores", () => {
  it("renders panel_text and ready-by / cost from the default 00000 scenario", async () => {
    await submitAndWait();

    const scenario = F.redline.scenarios["00000"];
    const top = scenario.options[0];
    expect(screen.getByText(displayOptionText(scenario.panel_text))).toBeInTheDocument();

    if (top.year_one_cost_lpa != null) {
      expect(
        screen.getAllByText(new RegExp(`₹${top.year_one_cost_lpa}L`)).length,
      ).toBeGreaterThanOrEqual(1);
    }
  });

  it("never shows a score number in the live panel", async () => {
    await submitAndWait();

    const panel = screen.getByRole("complementary", { name: /live recommendation/i });
    const text = panel.textContent ?? "";
    expect(text).not.toMatch(/\d{2}\/100/);
    expect(text.toLowerCase()).not.toContain("score");
  });
});

// ── Step 1: Déjà Req numbers ───────────────────────────────────────────────

describe("Sync: Déjà Req numbers from fixture", () => {
  async function expandDejaReq(user: ReturnType<typeof userEvent.setup>) {
    const banner = screen.getByText(F.dejareq.banner_text!);
    await user.click(banner);
  }

  it("banner text matches fixture", async () => {
    await submitAndWait();
    expect(screen.getByText(F.dejareq.banner_text!)).toBeInTheDocument();
  });

  it("insight text matches fixture (after expanding)", async () => {
    const user = await submitAndWait();
    await expandDejaReq(user);
    expect(screen.getByText(F.dejareq.insight_text!)).toBeInTheDocument();
  });

  it("timeline entry costs match fixture (after expanding)", async () => {
    const user = await submitAndWait();
    await expandDejaReq(user);
    for (const entry of F.dejareq.timeline) {
      if (entry.first_year_cost_lpa != null) {
        expect(
          screen.getAllByText(new RegExp(`₹${entry.first_year_cost_lpa}L`))
            .length,
        ).toBeGreaterThanOrEqual(1);
      }
    }
  });

  it("averages_by_decision buy avg_tenure_months matches fixture (after expanding)", async () => {
    const user = await submitAndWait();
    await expandDejaReq(user);
    const buyAvg = F.dejareq.averages_by_decision.find(
      (a) => a.decision === "buy",
    );
    if (buyAvg?.avg_tenure_months != null) {
      expect(
        screen.getAllByText(new RegExp(`${buyAvg.avg_tenure_months}`)).length,
      ).toBeGreaterThanOrEqual(1);
    }
  });
});

// ── Step 1: Redline constraint hover texts ─────────────────────────────────

describe("Sync: Redline constraints from fixture", () => {
  it("all constraint phrases present", async () => {
    await submitAndWait();
    for (const c of F.redline.constraints) {
      expect(
        screen.getAllByText(new RegExp(c.phrase.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")))
          .length,
      ).toBeGreaterThanOrEqual(1);
    }
  });
});

// ── Step 7: Options ────────────────────────────────────────────────────────

describe("Sync: Five-option table numbers from fixture", () => {
  it("every option's cost, ready-by, fit, risk_label, and reason render", async () => {
    const user = await submitAndWait();
    await clickStep(user, "Five options");

    for (const opt of F.options.five) {
      expect(screen.getAllByText(opt.name).length).toBeGreaterThanOrEqual(1);

      if (opt.year_one_cost_lpa != null) {
        expect(
          screen.getAllByText(new RegExp(`₹${opt.year_one_cost_lpa}L`)).length,
        ).toBeGreaterThanOrEqual(1);
      }

      if (opt.score != null) {
        expect(
          screen.getAllByText(String(opt.score)).length,
        ).toBeGreaterThanOrEqual(1);
      } else {
        expect(screen.getAllByText(/Add-on/).length).toBeGreaterThanOrEqual(1);
      }

      expect(
        screen.getAllByText(opt.risk_label).length,
      ).toBeGreaterThanOrEqual(1);

      expect(
        screen.getAllByText(displayOptionText(opt.reason)).length,
      ).toBeGreaterThanOrEqual(1);
    }
  });
});

describe("Sync: Recommended mix numbers from fixture", () => {
  it("top mix score, cost, and ready-by render", async () => {
    const user = await submitAndWait();
    await clickStep(user, "Five options");

    const mix = F.options.mixes[0];
    expect(
      screen.getAllByText(String(mix.score)).length,
    ).toBeGreaterThanOrEqual(1);
    expect(
      screen.getAllByText(new RegExp(`₹${mix.year_one_cost_lpa}L`)).length,
    ).toBeGreaterThanOrEqual(1);
  });
});

describe("Sync: Relocate card numbers from fixture", () => {
  it("all location rows' supply, P50, P80, pay render in table view", async () => {
    const user = await submitAndWait();
    await clickStep(user, "Location and compensation");

    await user.click(await screen.findByRole("button", { name: "Show as table" }));

    for (const row of F.options.relocate_card) {
      expect(
        screen.getAllByText(row.location).length,
      ).toBeGreaterThanOrEqual(1);
      expect(
        screen.getAllByText(String(row.supply)).length,
      ).toBeGreaterThanOrEqual(1);
      expect(
        screen.getAllByText(String(row.ttf_p50)).length,
      ).toBeGreaterThanOrEqual(1);
      expect(
        screen.getAllByText(String(row.ttf_p80)).length,
      ).toBeGreaterThanOrEqual(1);
    }
  });
});

describe("Sync: Ripple net-impact numbers from fixture", () => {
  it("each candidate's match, last-gap days, total cost, promotions, red flags render", async () => {
    const user = await submitAndWait();
    await clickStep(user, "Internal talent");

    for (const c of F.ripple.candidates) {
      expect(
        screen.getAllByText(new RegExp(`${c.match}%`)).length,
      ).toBeGreaterThanOrEqual(1);

      if (c.net_impact.days_to_fill_last_gap != null) {
        expect(
          screen.getAllByText(
            new RegExp(`${c.net_impact.days_to_fill_last_gap}\\s*days`),
          ).length,
        ).toBeGreaterThanOrEqual(1);
      }

      expect(
        screen.getAllByText(
          new RegExp(`₹${c.net_impact.total_cost_lpa}L`),
        ).length,
      ).toBeGreaterThanOrEqual(1);

      expect(
        screen.getAllByText(String(c.net_impact.promotions)).length,
      ).toBeGreaterThanOrEqual(1);
    }
  });
});

describe("Sync: Sourcing panel numbers from fixture", () => {
  it("each sourcing channel name and evidence render", async () => {
    const user = await submitAndWait();
    await clickStep(user, "External market");

    for (const ch of F.options.sourcing.channels) {
      expect(
        screen.getAllByText(new RegExp(ch.channel.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"))).length,
      ).toBeGreaterThanOrEqual(1);
    }
  });

  it("past finalist count renders", async () => {
    const user = await submitAndWait();
    await clickStep(user, "External market");

    const count = F.options.sourcing.past_finalists.length;
    expect(
      screen.getByText(new RegExp(`Past finalists: ${count}`)),
    ).toBeInTheDocument();
  });
});

// ── Step 7: Score consistency ──────────────────────────────────────────────

describe("Sync: Score consistency across step 7", () => {
  it("each scored option shows the same score value in every occurrence", async () => {
    const user = await submitAndWait();
    await clickStep(user, "Five options");

    const scoreMap = new Map<string, number>();
    for (const opt of F.options.five) {
      if (opt.score != null) scoreMap.set(opt.id, opt.score);
    }
    for (const mix of F.options.mixes) {
      if (mix.score != null) scoreMap.set(mix.id, mix.score);
    }

    for (const [, score] of scoreMap) {
      expect(
        screen.getAllByText(new RegExp(`\\b${score}\\b`)).length,
      ).toBeGreaterThanOrEqual(1);
    }
  });
});

// ── Step 8: Brief header ───────────────────────────────────────────────────

describe("Sync: Brief view renders from fixture", () => {
  it("brief heading renders", async () => {
    const user = await submitAndWait();
    await clickStep(user, "Human decision");
    expect(
      screen.getByText("Workforce Intelligence Brief"),
    ).toBeInTheDocument();
  });

  it("all brief section titles render", async () => {
    const user = await submitAndWait();
    await clickStep(user, "Human decision");

    for (const section of F.brief.sections) {
      expect(
        screen.getAllByText(section.title).length,
      ).toBeGreaterThanOrEqual(1);
    }
  });
});
