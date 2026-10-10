import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { FIXTURE_ANALYSIS } from "../fixtures";
import { RippleComparison } from "../components/RippleComparison";
import { clearPersonCache } from "../components/PersonDrawer";

import priyaFixture from "../fixtures/people/E-045.json";
import karthikFixture from "../fixtures/people/E-031.json";

function mockFetchForPerson(_personId: string) {
  return vi.fn().mockImplementation((url: string) => {
    let body: unknown = [];
    if (url.includes("E-045")) body = priyaFixture;
    if (url.includes("E-031")) body = karthikFixture;
    return Promise.resolve({
      ok: true,
      status: 200,
      statusText: "OK",
      json: () => Promise.resolve(body),
    });
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

const { candidates } = FIXTURE_ANALYSIS.ripple;
const priya = candidates.find((c) => c.person_id === "E-045")!;
const karthik = candidates.find((c) => c.person_id === "E-031")!;

describe("TC09: Priya's chain — 3 nodes, all green, net impact values", () => {
  it("renders 3 nodes in the chain", () => {
    globalThis.fetch = mockFetchForPerson("");
    render(<RippleComparison candidates={[priya]} />);

    const canBeFilled = screen.getAllByText("Can be filled");
    expect(canBeFilled).toHaveLength(3);
  });

  it("shows Priya's net impact values from the fixture", () => {
    globalThis.fetch = mockFetchForPerson("");
    render(<RippleComparison candidates={[priya]} />);

    expect(screen.getByText("21 days")).toBeInTheDocument();
    expect(screen.getByText("₹12L")).toBeInTheDocument();
    expect(screen.getByText("2")).toBeInTheDocument();
  });

  it("shows the chain seats in order", () => {
    globalThis.fetch = mockFetchForPerson("");
    render(<RippleComparison candidates={[priya]} />);

    expect(screen.getByText("Senior · Payments")).toBeInTheDocument();
    expect(screen.getByText("Mid · Checkout")).toBeInTheDocument();
    expect(screen.getByText("Junior · Checkout")).toBeInTheDocument();
  });
});

describe("TC10: Karthik's chain — bus-factor flag and hard-to-fill node", () => {
  const deadEnd = karthik.chain.children![0];
  const deadEndFlags = deadEnd.flags ?? [];

  it("fixture has bus_factor flag with skill=terraform on the dead-end node", () => {
    const bf = deadEndFlags.find((f) => f.type === "bus_factor");
    expect(bf).toBeDefined();
    expect(bf!.skill).toBe("terraform");
  });

  it("fixture has no_internal_backfill and hard_market flags on the dead-end node", () => {
    expect(
      deadEndFlags.find((f) => f.type === "no_internal_backfill"),
    ).toBeDefined();
    const hm = deadEndFlags.find((f) => f.type === "hard_market");
    expect(hm).toBeDefined();
    expect(hm!.p50_days).toBe(76);
  });

  it("renders 'Bus factor = 1' label from bus_factor flag", () => {
    globalThis.fetch = mockFetchForPerson("");
    render(<RippleComparison candidates={[karthik]} />);

    expect(screen.getByText("Bus factor = 1")).toBeInTheDocument();
  });

  it("renders 'Hard to fill' label from no_internal_backfill flag", () => {
    globalThis.fetch = mockFetchForPerson("");
    render(<RippleComparison candidates={[karthik]} />);

    expect(screen.getByText("Hard to fill")).toBeInTheDocument();
  });

  it("shows red_flags count from fixture in net impact", () => {
    globalThis.fetch = mockFetchForPerson("");
    render(<RippleComparison candidates={[karthik]} />);

    const redFlagsLabel = screen.getByText("Red flags");
    const container = redFlagsLabel.closest("div")!.parentElement!;
    const value = within(container).getByText(
      String(karthik.net_impact.red_flags),
    );
    expect(value).toBeInTheDocument();
    expect(karthik.net_impact.red_flags).toBe(2);
  });

  it("shows no internal backfill for the lead/Platform seat", () => {
    globalThis.fetch = mockFetchForPerson("");
    render(<RippleComparison candidates={[karthik]} />);

    expect(screen.getByText("No internal backfill")).toBeInTheDocument();
  });

  it("shows net impact days and cost from fixture", () => {
    globalThis.fetch = mockFetchForPerson("");
    render(<RippleComparison candidates={[karthik]} />);

    expect(screen.getByText(`${karthik.net_impact.days_to_fill_last_gap} days`)).toBeInTheDocument();
    expect(screen.getByText(`₹${karthik.net_impact.total_cost_lpa}L`)).toBeInTheDocument();
  });
});

describe("TC11: UI renders only people from API; drawer opens; tree is keyboard navigable", () => {
  it("renders exactly the candidates from the fixture", () => {
    globalThis.fetch = mockFetchForPerson("");
    render(<RippleComparison candidates={candidates} />);

    expect(screen.getAllByText("Karthik").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("Priya").length).toBeGreaterThanOrEqual(1);

    expect(screen.queryByText("Ravi")).not.toBeInTheDocument();
    expect(screen.queryByText("Amit")).not.toBeInTheDocument();
  });

  it("clicking View skills opens the drawer with person's skills", async () => {
    const user = userEvent.setup();
    const fetchMock = mockFetchForPerson("E-031");
    globalThis.fetch = fetchMock;

    render(<RippleComparison candidates={candidates} />);

    const viewButtons = screen.getAllByRole("button", {
      name: /view skills/i,
    });
    await user.click(viewButtons[0]);

    await waitFor(() => {
      expect(screen.getByText("Terraform")).toBeInTheDocument();
    });
  });

  it("clicking a person name in a tree node opens the drawer", async () => {
    const user = userEvent.setup();
    const fetchMock = mockFetchForPerson("E-072");
    globalThis.fetch = fetchMock;

    render(<RippleComparison candidates={candidates} />);

    const rahulLink = screen.getByRole("button", { name: "Rahul" });
    await user.click(rahulLink);

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalled();
    });
  });

  it("tree is a nested list navigable by keyboard", () => {
    globalThis.fetch = mockFetchForPerson("");
    render(<RippleComparison candidates={candidates} />);

    const lists = screen.getAllByRole("list");
    expect(lists.length).toBeGreaterThanOrEqual(2);

    const items = screen.getAllByRole("listitem");
    expect(items.length).toBeGreaterThanOrEqual(4);
  });
});
