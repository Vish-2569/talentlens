import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { FIXTURE_ANALYSIS } from "../fixtures";
import { FiveOptionTable } from "../components/FiveOptionTable";
import { RelocateCard } from "../components/RelocateCard";
import { SourcingPanel } from "../components/SourcingPanel";
import { RecommendedMix } from "../components/RecommendedMix";
import {
  reScore,
  normalizeWeights,
  rankOptions,
  rankMixes,
} from "../components/WeightSliders";
import { LiveRecommendation } from "../components/LiveRecommendation";
import type { components } from "../api/types";

type OptionCard = components["schemas"]["OptionCard"];
type MixOption = components["schemas"]["MixOption"];

const opts = FIXTURE_ANALYSIS.options;

// ── TC33: Five options render ────────────────────────────────────────────────

describe("TC33: Five-option table renders all options", () => {
  it("renders all 5 option names", () => {
    render(<FiveOptionTable options={opts.five as OptionCard[]} />);
    // Each option renders in both the desktop table and mobile cards — getAllByText is correct
    for (const opt of opts.five) {
      expect(screen.getAllByText(opt.name).length).toBeGreaterThanOrEqual(1);
    }
  });

  it("shows each option's cost from fixture", () => {
    render(<FiveOptionTable options={opts.five as OptionCard[]} />);
    for (const opt of opts.five) {
      if (opt.year_one_cost_lpa != null) {
        const matches = screen.queryAllByText(
          new RegExp(`₹${opt.year_one_cost_lpa}L`),
        );
        expect(matches.length).toBeGreaterThanOrEqual(1);
      }
    }
  });

  it("shows Automate as Add-on (score is null)", () => {
    render(<FiveOptionTable options={opts.five as OptionCard[]} />);
    // Appears in both desktop table and mobile card
    expect(screen.getAllByText(/Add-on/).length).toBeGreaterThanOrEqual(1);
  });

  it("table has id=five-option-table and is focusable", () => {
    render(<FiveOptionTable options={opts.five as OptionCard[]} />);
    const el = document.getElementById("five-option-table");
    expect(el).not.toBeNull();
    expect(el!.getAttribute("tabindex")).toBe("-1");
  });

  it("shows mix score from mixes[0]", () => {
    render(<RecommendedMix mixes={opts.mixes} />);
    expect(
      screen.getAllByText(String(opts.mixes[0].score)).length,
    ).toBeGreaterThanOrEqual(1);
  });
});

// ── TC34: Relocate card order ────────────────────────────────────────────────

describe("TC34: Relocate card order matches fixture", () => {
  it("renders locations in fixture order when table is shown", async () => {
    const user = userEvent.setup();
    render(<RelocateCard rows={opts.relocate_card} />);

    // Default view is chart; switch to table
    await user.click(screen.getByRole("button", { name: "Show as table" }));

    const rows = screen.getAllByRole("row").slice(1); // skip header
    const locations = rows.map((r) => {
      const cells = r.querySelectorAll("td");
      return cells[0]?.textContent ?? "";
    });
    const expected = opts.relocate_card.map((r) => r.location);
    expect(locations).toEqual(expected);
  });
});

// ── TC35: Past finalists count ───────────────────────────────────────────────

describe("TC35: Sourcing past finalists count", () => {
  it("displays correct count from fixture", () => {
    render(<SourcingPanel sourcing={opts.sourcing} />);
    const count = opts.sourcing.past_finalists.length;
    const remoteReady = opts.sourcing.past_finalists.filter(
      (f) => f.open_to_remote,
    ).length;
    expect(
      screen.getByText(
        new RegExp(`Past finalists: ${count}.*${remoteReady} remote-ready`),
      ),
    ).toBeInTheDocument();
  });
});

// ── TC-Weights: Dimensions reproduce scores ──────────────────────────────────

describe("TC-Weights: Weight slider re-ranking", () => {
  const defaultWeights = opts.weights;

  it("default weights × dimensions reproduce API scores exactly for all scored options", () => {
    for (const opt of opts.five) {
      if (opt.dimensions == null || opt.score == null) continue;
      const computed = reScore(
        opt.dimensions as Record<string, number>,
        defaultWeights,
      );
      expect(computed).toBe(opt.score);
    }
  });

  it("default weights × dimensions reproduce API scores exactly for all mixes", () => {
    for (const mix of opts.mixes) {
      const computed = reScore(
        mix.dimensions as Record<string, number>,
        defaultWeights,
      );
      expect(computed).toBe(mix.score);
    }
  });

  it("rankOptions keeps Automate last regardless of weights", () => {
    const heavyStrategic = normalizeWeights({
      speed: 0,
      cost: 0,
      fit: 0,
      risk: 0,
      strategic: 1,
    });
    const ranked = rankOptions(opts.five as OptionCard[], heavyStrategic);
    expect(ranked[ranked.length - 1].id).toBe("automate");
    expect(ranked[ranked.length - 1].score).toBeNull();
  });

  it("cost-heavy weights rank Build first (cheapest year-one cost)", () => {
    const costHeavy = normalizeWeights({
      speed: 0.05,
      cost: 0.8,
      fit: 0.05,
      risk: 0.05,
      strategic: 0.05,
    });
    const ranked = rankOptions(opts.five as OptionCard[], costHeavy);
    const scoredIds = ranked.filter((r) => r.score != null).map((r) => r.id);
    expect(scoredIds[0]).toBe("build");
  });

  it("rankMixes tie-breaks by cost then atom count", () => {
    const equal = normalizeWeights({
      speed: 0.2,
      cost: 0.2,
      fit: 0.2,
      risk: 0.2,
      strategic: 0.2,
    });
    const ranked = rankMixes(opts.mixes as MixOption[], equal);
    for (let i = 1; i < ranked.length; i++) {
      if (ranked[i].score === ranked[i - 1].score) {
        if (ranked[i].year_one_cost_lpa === ranked[i - 1].year_one_cost_lpa) {
          expect(ranked[i].atomCount).toBeGreaterThanOrEqual(
            ranked[i - 1].atomCount,
          );
        } else {
          expect(ranked[i].year_one_cost_lpa).toBeGreaterThanOrEqual(
            ranked[i - 1].year_one_cost_lpa,
          );
        }
      }
    }
  });
});

// ── LiveRecommendation: NO scores ────────────────────────────────────────────

describe("LiveRecommendation renders no score values", () => {
  const scenario =
    FIXTURE_ANALYSIS.redline.scenarios[
      Object.keys(FIXTURE_ANALYSIS.redline.scenarios)[0]
    ];

  it("does not render a score number followed by /100 for any option", () => {
    const { container } = render(
      <LiveRecommendation
        scenario={scenario}
        fiveOptions={opts.five as OptionCard[]}
        mask="00000"
        onReset={() => {}}
      />,
    );
    const text = container.textContent ?? "";
    // Scores are 2-digit numbers followed by /100 in some UIs — check none appear
    expect(text).not.toMatch(/\d{2}\/100/);
  });

  it("does not display the word 'score'", () => {
    const { container } = render(
      <LiveRecommendation
        scenario={scenario}
        fiveOptions={opts.five as OptionCard[]}
        mask="00000"
        onReset={() => {}}
      />,
    );
    expect(container.textContent?.toLowerCase()).not.toContain("score");
  });

  it("displays panel_text", () => {
    render(
      <LiveRecommendation
        scenario={scenario}
        fiveOptions={opts.five as OptionCard[]}
        mask="00000"
        onReset={() => {}}
      />,
    );
    expect(screen.getByText(scenario.panel_text)).toBeInTheDocument();
  });

  it("displays the top option name at least once", () => {
    render(
      <LiveRecommendation
        scenario={scenario}
        fiveOptions={opts.five as OptionCard[]}
        mask="00000"
        onReset={() => {}}
      />,
    );
    // Top option name appears as a Badge; getAllByText handles any duplicates in the list
    expect(
      screen.getAllByText(scenario.options[0].name).length,
    ).toBeGreaterThanOrEqual(1);
  });
});
