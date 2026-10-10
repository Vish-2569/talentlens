import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { App } from "../App";
import { AppProvider } from "../state/context";

function renderApp() {
  render(
    <AppProvider>
      <App />
    </AppProvider>,
  );
}

describe("Tab keyboard navigation", () => {
  it("renders three tab triggers", () => {
    renderApp();
    expect(screen.getByRole("tab", { name: "Challenge the request" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Weigh the options" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Decide" })).toBeInTheDocument();
  });

  it("first tab is selected by default", () => {
    renderApp();
    expect(screen.getByRole("tab", { name: "Challenge the request" })).toHaveAttribute(
      "data-state",
      "active",
    );
  });

  it("arrow key moves to next tab", async () => {
    const user = userEvent.setup();
    renderApp();

    const challengeTab = screen.getByRole("tab", { name: "Challenge the request" });
    challengeTab.focus();
    await user.keyboard("{ArrowRight}");

    expect(screen.getByRole("tab", { name: "Weigh the options" })).toHaveAttribute(
      "data-state",
      "active",
    );
  });

  it("arrow left wraps back to previous tab", async () => {
    const user = userEvent.setup();
    renderApp();

    const challengeTab = screen.getByRole("tab", { name: "Challenge the request" });
    challengeTab.focus();
    await user.keyboard("{ArrowRight}{ArrowRight}");

    expect(screen.getByRole("tab", { name: "Decide" })).toHaveAttribute(
      "data-state",
      "active",
    );

    await user.keyboard("{ArrowLeft}");
    expect(screen.getByRole("tab", { name: "Weigh the options" })).toHaveAttribute(
      "data-state",
      "active",
    );
  });

  it("tab panels are landmark regions", () => {
    renderApp();
    const tabpanels = screen.getAllByRole("tabpanel");
    expect(tabpanels.length).toBeGreaterThanOrEqual(1);
  });
});
