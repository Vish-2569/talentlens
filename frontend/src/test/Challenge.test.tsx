import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { FIXTURE_ANALYSIS } from "../fixtures";
import { AppProvider } from "../state/context";
import { Challenge } from "../screens/Challenge";

const DEMO_SENTENCE =
  "Senior Full Stack Developer, Bengaluru, on-site, 5+ years, must know React, Node.js and Kubernetes, budget ₹28L, need in 30 days.";

function mockFetch(status: number, body: unknown) {
  return vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    statusText: status === 200 ? "OK" : "Unprocessable Entity",
    json: () => Promise.resolve(body),
  });
}

function renderChallenge() {
  return render(
    <AppProvider>
      <Challenge />
    </AppProvider>,
  );
}

let originalFetch: typeof globalThis.fetch;

beforeEach(() => {
  originalFetch = globalThis.fetch;
});

afterEach(() => {
  globalThis.fetch = originalFetch;
  vi.restoreAllMocks();
});

describe("RequestComposer", () => {
  it("example button fills the exact demo sentence", async () => {
    const user = userEvent.setup();
    renderChallenge();

    await user.click(screen.getByRole("button", { name: "Use the example request" }));
    const textarea = screen.getByRole("textbox");
    expect(textarea).toHaveValue(DEMO_SENTENCE);
  });

  it("disables submit when textarea is empty", () => {
    renderChallenge();
    expect(
      screen.getByRole("button", { name: "Challenge this request" }),
    ).toBeDisabled();
  });

  it("disables submit and shows explanation for > 1000 characters", async () => {
    const user = userEvent.setup();
    renderChallenge();

    const textarea = screen.getByRole("textbox");
    const longText = "x".repeat(1001);
    await user.click(textarea);
    await user.paste(longText);

    expect(
      screen.getByRole("button", { name: "Challenge this request" }),
    ).toBeDisabled();
    expect(screen.getByText(/over 1,000 characters/i)).toBeInTheDocument();
  });

  it("submits with Ctrl+Enter", async () => {
    const user = userEvent.setup();
    globalThis.fetch = mockFetch(200, FIXTURE_ANALYSIS);
    renderChallenge();

    const textarea = screen.getByRole("textbox");
    await user.click(textarea);
    await user.paste(DEMO_SENTENCE);
    await user.keyboard("{Control>}{Enter}{/Control}");

    expect(globalThis.fetch).toHaveBeenCalled();
  });
});

describe("Loading state", () => {
  it("announces 'Analysing request' via live region", async () => {
    const user = userEvent.setup();
    let resolveFetch!: (value: unknown) => void;
    globalThis.fetch = vi.fn().mockReturnValue(
      new Promise((resolve) => {
        resolveFetch = resolve;
      }),
    );

    renderChallenge();
    await user.click(screen.getByRole("button", { name: "Use the example request" }));
    await user.click(screen.getByRole("button", { name: "Challenge this request" }));

    const liveRegion = screen.getByRole("status");
    expect(liveRegion).toHaveTextContent("Analysing request");

    resolveFetch({
      ok: true,
      status: 200,
      json: () => Promise.resolve(FIXTURE_ANALYSIS),
    });
  });
});

describe("Post-success view", () => {
  async function submitAndWait() {
    const user = userEvent.setup();
    globalThis.fetch = mockFetch(200, FIXTURE_ANALYSIS);
    renderChallenge();

    await user.click(screen.getByRole("button", { name: "Use the example request" }));
    await user.click(screen.getByRole("button", { name: "Challenge this request" }));

    await screen.findByText(DEMO_SENTENCE);
    return user;
  }

  it("collapses to summary with Edit request button", async () => {
    await submitAndWait();
    expect(screen.getByText("Edit request")).toBeInTheDocument();
    expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
  });

  it("inferred fields show 'Please confirm'", async () => {
    await submitAndWait();
    expect(screen.getByText("Please confirm")).toBeInTheDocument();
  });

  it("null fields listed in muted line", async () => {
    await submitAndWait();
    expect(screen.getByText(/not in the request/i)).toBeInTheDocument();
  });

  it("title normalization panel is collapsed by default", async () => {
    await submitAndWait();
    const details = screen.getByText(/12 raw titles/);
    expect(details).toBeInTheDocument();
  });

  it("XSS: script tag in request text renders as literal text", async () => {
    const user = userEvent.setup();
    globalThis.fetch = mockFetch(200, FIXTURE_ANALYSIS);
    renderChallenge();

    const xssText = '<script>alert(1)</script>';
    const textarea = screen.getByRole("textbox");
    await user.click(textarea);
    await user.paste(xssText);
    await user.click(screen.getByRole("button", { name: "Challenge this request" }));

    const matches = await screen.findAllByText(xssText);
    expect(matches.length).toBeGreaterThanOrEqual(1);

    const scriptElements = document.querySelectorAll("script");
    const injectedScripts = Array.from(scriptElements).filter((el) =>
      el.textContent?.includes("alert(1)"),
    );
    expect(injectedScripts).toHaveLength(0);
  });

  it("XSS: script tag in chip values renders as text", async () => {
    const xssFixture = structuredClone(FIXTURE_ANALYSIS);
    (xssFixture.parsed.location.value as string) =
      '<script>alert(1)</script>';
    (xssFixture.parsed.location.span as string) =
      '<script>alert(1)</script>';

    const user = userEvent.setup();
    globalThis.fetch = mockFetch(200, xssFixture);
    renderChallenge();

    await user.click(screen.getByRole("button", { name: "Use the example request" }));
    await user.click(screen.getByRole("button", { name: "Challenge this request" }));

    const fieldList = await screen.findByRole("list", {
      name: "Parsed fields",
    });
    expect(
      within(fieldList).getByText('<script>alert(1)</script>'),
    ).toBeInTheDocument();

    const injected = Array.from(document.querySelectorAll("script")).filter(
      (el) => el.textContent?.includes("alert(1)"),
    );
    expect(injected).toHaveLength(0);
  });
});

describe("Error handling", () => {
  it("422 shows field error message next to textarea", async () => {
    const user = userEvent.setup();
    const detail = [
      { loc: ["body", "text"], msg: "ensure this value has at most 1000 characters", type: "value_error" },
    ];
    globalThis.fetch = mockFetch(422, { detail });

    renderChallenge();
    const textarea = screen.getByRole("textbox");
    await user.click(textarea);
    await user.paste("test request");
    await user.click(screen.getByRole("button", { name: "Challenge this request" }));

    await screen.findByText(/ensure this value has at most 1000 characters/);
    expect(textarea).toHaveValue("test request");
  });

  it("network error shows ErrorBanner", async () => {
    const user = userEvent.setup();
    globalThis.fetch = vi.fn().mockRejectedValue(new TypeError("Failed to fetch"));

    renderChallenge();
    await user.click(screen.getByRole("button", { name: "Use the example request" }));
    await user.click(screen.getByRole("button", { name: "Challenge this request" }));

    await screen.findByRole("alert");
  });
});
