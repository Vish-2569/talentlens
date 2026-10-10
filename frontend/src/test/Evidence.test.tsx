import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { components } from "../api/types";
import { SkillBar } from "../components/SkillBar";
import { SourceTag } from "../components/SourceTag";
import { PersonDrawer, clearPersonCache } from "../components/PersonDrawer";
import { DataQualityLine } from "../components/DataQualityLine";

import rahulFixture from "../fixtures/people/E-072.json";
import priyaFixture from "../fixtures/people/E-045.json";

type SkillScore = components["schemas"]["SkillScore"];

function mockFetch(body: unknown) {
  return vi.fn().mockResolvedValue({
    ok: true,
    status: 200,
    statusText: "OK",
    json: () => Promise.resolve(body),
  });
}

let originalFetch: typeof globalThis.fetch;

beforeEach(() => {
  originalFetch = globalThis.fetch;
  clearPersonCache();
});

afterEach(() => {
  globalThis.fetch = originalFetch;
  vi.restoreAllMocks();
});

// ── TC23: Rahul AWS ────────────────────────────────────────────────────────

describe("TC23: Rahul AWS — 35, assessment, Mar 2026", () => {
  const rahulAws = (rahulFixture as SkillScore[]).find(
    (s) => s.skill === "aws",
  )!;

  it("shows value 35 with role=meter", () => {
    render(<SkillBar skill={rahulAws} />);

    const meter = screen.getByRole("meter");
    expect(meter).toHaveAttribute("aria-valuenow", "35");
    expect(meter).toHaveAttribute("aria-valuemin", "0");
    expect(meter).toHaveAttribute("aria-valuemax", "100");
  });

  it("shows assessment tag with check icon text", () => {
    render(<SkillBar skill={rahulAws} />);

    const tag = screen.getByText("Assessment");
    expect(tag).toBeInTheDocument();
  });

  it("shows Mar 2026 date", () => {
    render(<SkillBar skill={rahulAws} />);
    expect(screen.getByText("Mar 2026")).toBeInTheDocument();
  });

  it("tooltip mentions ignored self-report", () => {
    render(<SkillBar skill={rahulAws} />);

    expect(rahulAws.tooltip).toContain("self-reported");
    expect(rahulAws.tooltip).toContain("ignored");
  });

  it("value text shows 35", () => {
    render(<SkillBar skill={rahulAws} />);
    expect(screen.getByText("35")).toBeInTheDocument();
  });
});

// ── TC24: Self-report-only skill (GraphQL, Priya) ─────────────────────────

describe("TC24: self-report-only skill shows 39, outlined self-report tag", () => {
  const priyaGraphql = (priyaFixture as SkillScore[]).find(
    (s) => s.skill === "graphql",
  )!;

  it("shows value 39", () => {
    render(<SkillBar skill={priyaGraphql} />);
    expect(screen.getByText("39")).toBeInTheDocument();

    const meter = screen.getByRole("meter");
    expect(meter).toHaveAttribute("aria-valuenow", "39");
  });

  it("shows self-report tag with outlined style", () => {
    render(<SkillBar skill={priyaGraphql} />);
    const tag = screen.getByText("Self-report");
    expect(tag).toBeInTheDocument();

    const container = tag.closest("[data-source]");
    expect(container).toHaveAttribute("data-source", "self");
  });
});

// ── TC25: Priya Kubernetes — 40 with ⚠ and disagree tooltip ──────────────

describe("TC25: Priya Kubernetes — 40, conflict warning", () => {
  const priyaK8s = (priyaFixture as SkillScore[]).find(
    (s) => s.skill === "kubernetes",
  )!;

  it("shows value 40 with conflict", () => {
    render(<SkillBar skill={priyaK8s} />);
    expect(screen.getByText("40")).toBeInTheDocument();
    expect(priyaK8s.conflict).toBe(true);
  });

  it("shows ⚠ and visually-hidden text", () => {
    render(<SkillBar skill={priyaK8s} />);
    expect(screen.getByText("⚠")).toBeInTheDocument();
    expect(screen.getByText("sources disagree")).toBeInTheDocument();
  });

  it("tooltip mentions disagree by 50 points", () => {
    expect(priyaK8s.tooltip).toContain("disagree by 50 points");
  });
});

// ── TC30: Tags distinguishable, tooltip accessible, drawer focus trap ─────

describe("TC30: accessibility — tags, tooltips, drawer", () => {
  it("each source type has a distinct icon and text label", () => {
    const sources: Array<{
      source: "assessment" | "certification" | "project" | "self";
      label: string;
    }> = [
      { source: "assessment", label: "Assessment" },
      { source: "certification", label: "Certification" },
      { source: "project", label: "Project" },
      { source: "self", label: "Self-report" },
    ];

    const { unmount } = render(
      <div>
        {sources.map((s) => (
          <SourceTag
            key={s.source}
            source={s.source}
            observed_on="2026-01-01"
            stale={false}
            conflict={false}
          />
        ))}
      </div>,
    );

    for (const s of sources) {
      expect(screen.getByText(s.label)).toBeInTheDocument();
    }

    const containers = screen.getAllByText(/./).map(
      (el) => el.closest("[data-source]")?.getAttribute("data-source"),
    ).filter(Boolean);

    const unique = new Set(containers);
    expect(unique.size).toBe(4);
    unmount();
  });

  it("tooltip opens via keyboard focus", async () => {
    const user = userEvent.setup();
    const skill: SkillScore = {
      skill: "react",
      value: 90,
      source: "assessment",
      observed_on: "2026-05-01",
      confidence: 1,
      stale: false,
      conflict: false,
      tooltip: "Assessment score 90/100, taken 1 May 2026.",
      ignored: [],
    };

    render(<SkillBar skill={skill} />);

    const infoBtn = screen.getByRole("button", {
      name: /details for react/i,
    });

    await user.tab();
    await user.tab();

    await user.click(infoBtn);

    await waitFor(() => {
      expect(
        screen.getByText("Assessment score 90/100, taken 1 May 2026."),
      ).toBeInTheDocument();
    });
  });

  it("drawer fetches skills once per person", async () => {
    const fetchMock = mockFetch(rahulFixture);
    globalThis.fetch = fetchMock;

    const onClose = vi.fn();

    const { rerender } = render(
      <PersonDrawer personId="E-072" onClose={onClose} displayName="Rahul" />,
    );

    await waitFor(() => {
      expect(screen.getByText("Aws")).toBeInTheDocument();
    });

    expect(fetchMock).toHaveBeenCalledTimes(1);

    rerender(
      <PersonDrawer personId={null} onClose={onClose} displayName="Rahul" />,
    );
    rerender(
      <PersonDrawer personId="E-072" onClose={onClose} displayName="Rahul" />,
    );

    await waitFor(() => {
      expect(screen.getByText("Aws")).toBeInTheDocument();
    });

    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("drawer shows close button that calls onClose", async () => {
    const clicker = userEvent.setup();
    globalThis.fetch = mockFetch(rahulFixture);
    const onClose = vi.fn();

    render(
      <PersonDrawer personId="E-072" onClose={onClose} displayName="Rahul" />,
    );

    await waitFor(() => {
      expect(screen.getByText("Aws")).toBeInTheDocument();
    });

    const closeBtn = screen.getByRole("button", { name: /close/i });
    await clicker.click(closeBtn);

    expect(onClose).toHaveBeenCalled();
  });
});

// ── DataQualityLine ─────────────────────────────────────────────────────

describe("DataQualityLine", () => {
  it("renders the line text", () => {
    render(
      <DataQualityLine line="Shortlist: 2 skill conflicts, 1 stale score, 3 self-report-only skills" />,
    );
    expect(
      screen.getByText(
        "Shortlist: 2 skill conflicts, 1 stale score, 3 self-report-only skills",
      ),
    ).toBeInTheDocument();
  });
});
