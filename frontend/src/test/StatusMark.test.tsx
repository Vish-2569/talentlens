import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { StatusMark } from "../components/ui/StatusMark";

describe("StatusMark", () => {
  it("renders icon and text for red status", () => {
    render(<StatusMark status="red" />);
    expect(screen.getByText("▲")).toBeInTheDocument();
    expect(screen.getByText("High cost")).toBeInTheDocument();
  });

  it("renders icon and text for amber status", () => {
    render(<StatusMark status="amber" />);
    expect(screen.getByText("◆")).toBeInTheDocument();
    expect(screen.getByText("Moderate cost")).toBeInTheDocument();
  });

  it("renders icon and text for green status", () => {
    render(<StatusMark status="green" />);
    expect(screen.getByText("●")).toBeInTheDocument();
    expect(screen.getByText("Clear")).toBeInTheDocument();
  });

  it("never conveys meaning by colour alone: text label always present", () => {
    const { rerender } = render(<StatusMark status="red" />);
    expect(screen.getByText("High cost")).toBeInTheDocument();

    rerender(<StatusMark status="amber" />);
    expect(screen.getByText("Moderate cost")).toBeInTheDocument();

    rerender(<StatusMark status="green" />);
    expect(screen.getByText("Clear")).toBeInTheDocument();
  });

  it("exposes a data-status attribute for each status", () => {
    const { container } = render(<StatusMark status="amber" />);
    expect(container.firstChild).toHaveAttribute("data-status", "amber");
  });
});
