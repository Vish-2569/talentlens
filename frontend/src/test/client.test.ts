import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, analyze, getHealth, getPersonSkills, postDecision } from "../api/client";

function mockFetch(status: number, body: unknown) {
  return vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    statusText: status === 200 ? "OK" : status === 400 ? "Bad Request" : "Unprocessable Entity",
    json: () => Promise.resolve(body),
    text: () => Promise.resolve(JSON.stringify(body)),
  });
}

describe("ApiError", () => {
  it("is instanceof Error", () => {
    const e = new ApiError(422, "bad");
    expect(e).toBeInstanceOf(Error);
    expect(e).toBeInstanceOf(ApiError);
    expect(e.status).toBe(422);
    expect(e.message).toBe("bad");
  });

  it("carries fieldErrors", () => {
    const fe = [{ loc: ["body", "text"], msg: "too short", type: "value_error" }];
    const e = new ApiError(422, "msg", fe);
    expect(e.fieldErrors).toEqual(fe);
  });
});

describe("analyze", () => {
  let original: typeof globalThis.fetch;

  beforeEach(() => {
    original = globalThis.fetch;
  });
  afterEach(() => {
    globalThis.fetch = original;
  });

  it("returns AnalysisResult on 200", async () => {
    const stub = { parsed: { req_id: "R1" } };
    globalThis.fetch = mockFetch(200, stub);
    const result = await analyze({ text: "hello" });
    expect(result).toEqual(stub);
  });

  it("throws ApiError with message on 400 string detail", async () => {
    globalThis.fetch = mockFetch(400, { detail: "Text too short." });
    await expect(analyze({ text: "x" })).rejects.toMatchObject({
      status: 400,
      message: "Text too short.",
    });
  });

  it("throws ApiError with fieldErrors on 422 array detail", async () => {
    const detail = [{ loc: ["body", "text"], msg: "field required", type: "missing" }];
    globalThis.fetch = mockFetch(422, { detail });
    const err = await analyze({ text: "" }).catch((e: unknown) => e);
    expect(err).toBeInstanceOf(ApiError);
    if (err instanceof ApiError) {
      expect(err.status).toBe(422);
      expect(err.fieldErrors).toHaveLength(1);
      expect(err.fieldErrors![0].msg).toBe("field required");
    }
  });
});

describe("getHealth", () => {
  let original: typeof globalThis.fetch;

  beforeEach(() => {
    original = globalThis.fetch;
  });
  afterEach(() => {
    globalThis.fetch = original;
  });

  it("returns Health on 200", async () => {
    const stub = { ok: true, cache_loaded: true, llm_configured: true };
    globalThis.fetch = mockFetch(200, stub);
    const h = await getHealth();
    expect(h.ok).toBe(true);
  });

  it("throws ApiError on non-200", async () => {
    globalThis.fetch = mockFetch(503, { detail: "Service unavailable" });
    await expect(getHealth()).rejects.toBeInstanceOf(ApiError);
  });
});

describe("getPersonSkills", () => {
  let original: typeof globalThis.fetch;

  beforeEach(() => {
    original = globalThis.fetch;
  });
  afterEach(() => {
    globalThis.fetch = original;
  });

  it("encodes the person ID in the URL", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve([]),
    });
    await getPersonSkills("E-031");
    expect((globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0][0]).toContain("E-031");
  });
});

describe("postDecision — no retry guarantee", () => {
  let original: typeof globalThis.fetch;

  beforeEach(() => {
    original = globalThis.fetch;
  });
  afterEach(() => {
    globalThis.fetch = original;
  });

  it("calls fetch exactly once on success", async () => {
    const fetcher = mockFetch(201, {});
    globalThis.fetch = fetcher;
    await postDecision({
      req_id: "R1",
      option_id: "buy",
      verb: "Approve",
      relaxed_mask: "00000",
      decided_by: "Alice",
      reason: "Makes sense",
    });
    expect(fetcher).toHaveBeenCalledTimes(1);
  });

  it("throws ApiError on 422 without retrying", async () => {
    const detail = [{ loc: ["body", "reason"], msg: "field required", type: "missing" }];
    const fetcher = mockFetch(422, { detail });
    globalThis.fetch = fetcher;
    await expect(
      postDecision({
        req_id: "R1",
        option_id: "buy",
        verb: "Approve",
        relaxed_mask: "00000",
        decided_by: "Alice",
        reason: "",
      }),
    ).rejects.toBeInstanceOf(ApiError);
    expect(fetcher).toHaveBeenCalledTimes(1);
  });
});
