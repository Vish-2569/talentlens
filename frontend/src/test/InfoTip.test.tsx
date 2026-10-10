import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { InfoTip } from "../components/ui/InfoTip";

function setup() {
  const user = userEvent.setup();
  render(
    <InfoTip content="Tip content" aria-label="Show tip">
      <span>Trigger</span>
    </InfoTip>,
  );
  return { user, trigger: screen.getByRole("button", { name: "Show tip" }) };
}

describe("InfoTip", () => {
  it("renders the trigger", () => {
    const { trigger } = setup();
    expect(trigger).toBeInTheDocument();
  });

  it("opens popover content on click", async () => {
    const { user, trigger } = setup();
    await user.click(trigger);
    // Popover content should appear
    expect(await screen.findByText("Tip content")).toBeInTheDocument();
  });

  it("opens tooltip content on keyboard focus (tab)", async () => {
    const { user } = setup();
    await user.tab();
    // After tabbing to the trigger, tooltip should appear
    const tips = await screen.findAllByText("Tip content");
    expect(tips.length).toBeGreaterThanOrEqual(1);
  });

  it("closes popover on second click", async () => {
    const { user, trigger } = setup();
    await user.click(trigger);
    await screen.findByText("Tip content");
    await user.click(trigger);
    // Wait for the popover to close
    await new Promise((r) => setTimeout(r, 50));
    const items = screen.queryAllByText("Tip content");
    expect(items.length).toBe(0);
  });

  it("trigger has accessible button role", () => {
    const { trigger } = setup();
    expect(trigger.tagName).toBe("BUTTON");
  });
});
