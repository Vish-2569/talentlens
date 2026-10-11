import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { axe } from "vitest-axe";
import { FIXTURE_ANALYSIS } from "../fixtures";
import { App } from "../App";
import { AppProvider, useAppDispatch } from "../state/context";
import { useEffect } from "react";

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

function Injector({ children }: { children: React.ReactNode }) {
  const dispatch = useAppDispatch();
  useEffect(() => {
    dispatch({ type: "ANALYZE_SUCCESS", payload: FIXTURE_ANALYSIS });
  }, [dispatch]);
  return <>{children}</>;
}

function renderApp() {
  return render(
    <AppProvider>
      <Injector>
        <App />
      </Injector>
    </AppProvider>,
  );
}

// ── TC30: Accessibility — axe audit per step ──────────────────────────────────

describe("TC30: Accessibility — axe audit", () => {
  it("Step 1 (Need) has zero serious/critical axe violations", async () => {
    const { container } = renderApp();
    await screen.findByText(/Requisition Redline/);

    const results = await axe(container);
    const serious = results.violations.filter(
      (v) => v.impact === "serious" || v.impact === "critical",
    );
    expect(serious).toEqual([]);
  }, 15_000);

  it("Step 7 (Options) has zero serious/critical axe violations", async () => {
    const user = userEvent.setup();
    const { container } = renderApp();
    await screen.findByText(/Requisition Redline/);

    // Navigate to step 7
    const optionsBtn = screen.getAllByRole("button").find(
      (b) => b.getAttribute("aria-label")?.includes("Five options"),
    );
    await user.click(optionsBtn!);
    await screen.findAllByText(/Recommended mix/);

    const results = await axe(container);
    const serious = results.violations.filter(
      (v) => v.impact === "serious" || v.impact === "critical",
    );
    expect(serious).toEqual([]);
  }, 15_000);

  it("Step 8 (Decision) has zero serious/critical axe violations", async () => {
    const user = userEvent.setup();
    const { container } = renderApp();
    await screen.findByText(/Requisition Redline/);

    const decisionBtn = screen.getAllByRole("button").find(
      (b) => b.getAttribute("aria-label")?.includes("Human decision"),
    );
    await user.click(decisionBtn!);
    await screen.findByLabelText(/Approver/);

    const results = await axe(container);
    const serious = results.violations.filter(
      (v) => v.impact === "serious" || v.impact === "critical",
    );
    expect(serious).toEqual([]);
  }, 15_000);
});

// ── TC30: Structural accessibility ──────────────────────────────────────────

describe("TC30: skip link, landmarks, focus ring", () => {
  it("skip link targets #main-content", () => {
    renderApp();
    const skip = document.querySelector('a[href="#main-content"]');
    expect(skip).toBeTruthy();
    expect(skip!.textContent).toContain("Skip to main content");
  });

  it("landmarks: header (banner), nav, main, footer (contentinfo)", () => {
    renderApp();
    expect(screen.getByRole("banner")).toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: "Workflow progress" })).toBeInTheDocument();
    expect(screen.getByRole("main")).toBeInTheDocument();
    expect(screen.getByRole("contentinfo")).toBeInTheDocument();
  });

  it("main content is focusable (tabIndex=-1 for skip link target)", () => {
    renderApp();
    const main = document.getElementById("main-content");
    expect(main).toBeTruthy();
    expect(main!.getAttribute("tabindex")).toBe("-1");
  });

  it("live region exists for recommendation announcements", () => {
    renderApp();
    const live = document.getElementById("recommendation-live");
    expect(live).toBeTruthy();
    expect(live!.getAttribute("aria-live")).toBe("polite");
  });

  it("active step has aria-current=step", () => {
    renderApp();
    const nav = screen.getByRole("navigation", { name: "Workflow progress" });
    const current = nav.querySelector('[aria-current="step"]');
    expect(current).toBeTruthy();
  });
});
