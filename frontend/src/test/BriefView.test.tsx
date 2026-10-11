import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { BriefView } from "../components/BriefView";
import { FIXTURE_ANALYSIS } from "../fixtures";
import type { components } from "../api/types";

type Brief = components["schemas"]["Brief"];
type DataQuality = components["schemas"]["DataQuality"];

const BRIEF: Brief = FIXTURE_ANALYSIS.brief;
const DQ: DataQuality = FIXTURE_ANALYSIS.data_quality;
const REQ_ID = FIXTURE_ANALYSIS.parsed.req_id;

function renderBrief(briefOverride?: Partial<Brief>) {
  const brief = { ...BRIEF, ...briefOverride };
  return render(
    <BriefView brief={brief} dataQuality={DQ} reqId={REQ_ID} />,
  );
}

// ── TC36: 12 sections in API order, none empty ──────────────────────────────

describe("TC36: BriefView sections", () => {
  it("renders exactly 12 sections in API order", () => {
    renderBrief();
    const buttons = screen.getAllByRole("button", { expanded: true });
    expect(buttons).toHaveLength(12);

    const expectedTitles = BRIEF.sections.map((s) => s.title);
    const rendered = buttons.map((b) => b.textContent?.trim());
    expect(rendered).toEqual(expectedTitles);
  });

  it("every section has non-empty content when expanded", () => {
    renderBrief();
    for (const section of BRIEF.sections) {
      const region = screen.getByRole("region", {
        name: section.title,
      });
      expect(region.textContent!.trim().length).toBeGreaterThan(0);
    }
  });
});

// ── TC36: Jump list ─────────────────────────────────────────────────────────

describe("TC36: Jump list", () => {
  it("renders numbered links for all 12 sections", () => {
    renderBrief();
    const nav = screen.getByRole("navigation", { name: "Brief sections" });
    const links = within(nav).getAllByRole("link");
    expect(links).toHaveLength(12);
    expect(links[0].textContent).toContain("1.");
    expect(links[11].textContent).toContain("12.");
  });
});

// ── TC36: Blob exports ──────────────────────────────────────────────────────

describe("TC36: Blob exports", () => {
  let createObjectURL: ReturnType<typeof vi.fn>;
  let revokeObjectURL: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    createObjectURL = vi.fn().mockReturnValue("blob:test-url");
    revokeObjectURL = vi.fn();
    globalThis.URL.createObjectURL = createObjectURL as unknown as typeof URL.createObjectURL;
    globalThis.URL.revokeObjectURL = revokeObjectURL as unknown as typeof URL.revokeObjectURL;
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("Download Markdown creates a text/markdown blob with req_id filename", async () => {
    const user = userEvent.setup();
    const clickedAnchors: { href: string; download: string }[] = [];
    const origCreate = document.createElement.bind(document);
    vi.spyOn(document, "createElement").mockImplementation((tag: string) => {
      const el = origCreate(tag);
      if (tag === "a") {
        const origClick = el.click.bind(el);
        el.click = () => {
          clickedAnchors.push({
            href: (el as HTMLAnchorElement).href,
            download: (el as HTMLAnchorElement).download,
          });
          origClick();
        };
      }
      return el;
    });

    renderBrief();
    const btn = screen.getByRole("button", { name: /Download brief as Markdown/ });
    await user.click(btn);

    expect(createObjectURL).toHaveBeenCalledOnce();
    const blob = createObjectURL.mock.calls[0][0] as Blob;
    expect(blob.type).toBe("text/markdown");
    expect(clickedAnchors[0].download).toBe(`${REQ_ID}-brief.md`);
    expect(revokeObjectURL).toHaveBeenCalledOnce();
  });

  it("Download HTML creates a text/html blob with req_id filename", async () => {
    const user = userEvent.setup();
    const clickedAnchors: { href: string; download: string }[] = [];
    const origCreate = document.createElement.bind(document);
    vi.spyOn(document, "createElement").mockImplementation((tag: string) => {
      const el = origCreate(tag);
      if (tag === "a") {
        const origClick = el.click.bind(el);
        el.click = () => {
          clickedAnchors.push({
            href: (el as HTMLAnchorElement).href,
            download: (el as HTMLAnchorElement).download,
          });
          origClick();
        };
      }
      return el;
    });

    renderBrief();
    const btn = screen.getByRole("button", { name: /Download brief as HTML/ });
    await user.click(btn);

    expect(createObjectURL).toHaveBeenCalledOnce();
    const blob = createObjectURL.mock.calls[0][0] as Blob;
    expect(blob.type).toBe("text/html");
    expect(clickedAnchors[0].download).toBe(`${REQ_ID}-brief.html`);
  });

  it("Print opens a new tab with a blob URL", async () => {
    const user = userEvent.setup();
    const openSpy = vi.spyOn(window, "open").mockImplementation(() => null);
    renderBrief();
    const btn = screen.getByRole("button", { name: /Open printable version/ });
    await user.click(btn);

    expect(createObjectURL).toHaveBeenCalledOnce();
    expect(openSpy).toHaveBeenCalledWith("blob:test-url", "_blank");
  });
});

// ── TC36: <script> in section renders as text ───────────────────────────────

describe("TC36: XSS safety", () => {
  it("<script> in a section renders as text, not executed", () => {
    const malicious: Brief = {
      ...BRIEF,
      sections: [
        {
          key: "xss",
          title: "XSS Test",
          markdown: '<script>alert("xss")</script> normal text',
        },
      ],
    };
    renderBrief(malicious);

    const region = screen.getByRole("region", { name: "XSS Test" });
    expect(region.textContent).toContain('<script>alert("xss")</script>');
    expect(region.innerHTML).not.toContain("<script>");
  });
});

// ── TC36: DataQualityLine present ───────────────────────────────────────────

describe("TC36: DataQualityLine", () => {
  it("renders the data quality line from the API", () => {
    renderBrief();
    expect(screen.getByText(DQ.line)).toBeTruthy();
  });
});

// ── TC36: Simulated data note in evidence section ───────────────────────────

describe("TC36: Simulated data note", () => {
  it("evidence section shows simulated data warning", () => {
    renderBrief();
    expect(
      screen.getByText(/All data in this brief is simulated/),
    ).toBeTruthy();
  });
});

// ── DecisionPanel tests still work (import check) ──────────────────────────

describe("TC36: Decide tab integration", () => {
  it("BriefView renders without crashing alongside fixture data", () => {
    renderBrief();
    expect(screen.getByText("Workforce Intelligence Brief")).toBeTruthy();
  });
});
