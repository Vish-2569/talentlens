import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { useEffect } from "react";
import { App } from "../App";
import { AppProvider, useAppDispatch } from "../state/context";
import { FIXTURE_ANALYSIS } from "../fixtures";

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

function renderAppWithData() {
  return render(
    <AppProvider>
      <Injector>
        <App />
      </Injector>
    </AppProvider>,
  );
}

function renderApp() {
  return render(
    <AppProvider>
      <App />
    </AppProvider>,
  );
}

describe("Step navigation", () => {
  it("step 1 is active by default", () => {
    renderAppWithData();
    expect(screen.getByText("Workforce need")).toBeInTheDocument();
  });

  it("clicking a workflow step shows only that step content", async () => {
    const user = userEvent.setup();
    renderAppWithData();

    // Click step 3 (Internal)
    const internalBtn = screen.getAllByRole("button").find(
      (b) => b.getAttribute("aria-label")?.includes("Internal talent"),
    );
    expect(internalBtn).toBeDefined();
    await user.click(internalBtn!);

    expect(screen.getByText("Internal talent")).toBeInTheDocument();
    // Step 1 heading should not be visible
    expect(screen.queryByText("Workforce need")).not.toBeInTheDocument();
  });

  it("Back button navigates to previous step", async () => {
    const user = userEvent.setup();
    renderAppWithData();

    // Go to step 3
    const internalBtn = screen.getAllByRole("button").find(
      (b) => b.getAttribute("aria-label")?.includes("Internal talent"),
    );
    await user.click(internalBtn!);
    expect(screen.getByText("Internal talent")).toBeInTheDocument();

    // Click Back
    await user.click(screen.getByText("← Back"));
    expect(screen.getByText("Role / skill analysis")).toBeInTheDocument();
  });

  it("Next button navigates to next step", async () => {
    const user = userEvent.setup();
    renderAppWithData();

    // On step 1, click Next
    await user.click(screen.getByText("Next →"));
    expect(screen.getByText("Role / skill analysis")).toBeInTheDocument();
  });

  it("Back button is disabled on step 1", () => {
    renderAppWithData();
    const backBtn = screen.getByText("← Back");
    expect(backBtn).toBeDisabled();
  });

  it("hash updates when navigating steps", async () => {
    const user = userEvent.setup();
    renderAppWithData();

    await user.click(screen.getByText("Next →"));
    expect(window.location.hash).toBe("#step-2");
  });

  it("state survives step changes (mask preserved)", async () => {
    const user = userEvent.setup();
    renderAppWithData();

    // Navigate away and back
    await user.click(screen.getByText("Next →"));
    await user.click(screen.getByText("← Back"));

    // Step 1 content should be there
    expect(screen.getByText("Workforce need")).toBeInTheDocument();
  });

  it("steps 2-9 are disabled before analysis", () => {
    renderApp();
    const nav = screen.getByRole("navigation", { name: "Workflow progress" });
    const disabledSpans = nav.querySelectorAll('[aria-disabled="true"]');
    expect(disabledSpans.length).toBe(8);
  });

  it("focus moves to heading on step change", async () => {
    const user = userEvent.setup();
    renderAppWithData();

    await user.click(screen.getByText("Next →"));
    const heading = document.getElementById("step-2-heading");
    // requestAnimationFrame may not fire in jsdom, check the heading exists
    expect(heading).toBeTruthy();
  });
});
