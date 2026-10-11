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
});

afterEach(() => {
  globalThis.fetch = originalFetch;
  vi.restoreAllMocks();
});

// Inject fixture into the full App
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

// ── TC30: Accessibility — axe audit per tab ──────────────────────────────────

describe("TC30: Accessibility — axe audit", () => {
  it("Challenge tab has zero serious/critical axe violations", async () => {
    const { container } = renderApp();
    await screen.findByText(/Requisition Redline/);

    const results = await axe(container);
    const serious = results.violations.filter(
      (v) => v.impact === "serious" || v.impact === "critical",
    );
    expect(serious).toEqual([]);
  }, 15_000);

  it("Options tab has zero serious/critical axe violations", async () => {
    const user = userEvent.setup();
    const { container } = renderApp();
    await screen.findByText(/Requisition Redline/);

    await user.click(screen.getByRole("tab", { name: "Weigh the options" }));
    await screen.findByText(/Five options/);

    const results = await axe(container);
    const serious = results.violations.filter(
      (v) => v.impact === "serious" || v.impact === "critical",
    );
    expect(serious).toEqual([]);
  }, 15_000);

  it("Decide tab has zero serious/critical axe violations", async () => {
    const user = userEvent.setup();
    const { container } = renderApp();
    await screen.findByText(/Requisition Redline/);

    await user.click(screen.getByRole("tab", { name: "Decide" }));
    await screen.findByLabelText(/Approver/);

    const results = await axe(container);
    const serious = results.violations.filter(
      (v) => v.impact === "serious" || v.impact === "critical",
    );
    expect(serious).toEqual([]);
  }, 15_000);
});

// ── TC30: Structural accessibility ──────────────────────────────────────────

describe("TC30: skip link, landmarks, focus ring, tab order", () => {
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

  it("tab order: tabs are keyboard-navigable with arrow keys", async () => {
    const user = userEvent.setup();
    renderApp();

    const challengeTab = screen.getByRole("tab", { name: "Challenge the request" });
    challengeTab.focus();
    await user.keyboard("{ArrowRight}");

    expect(
      screen.getByRole("tab", { name: "Weigh the options" }),
    ).toHaveAttribute("data-state", "active");
  });
});
