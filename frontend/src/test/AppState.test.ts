import { describe, expect, it } from "vitest";
import { FIXTURE_ANALYSIS } from "../fixtures";
import { INITIAL_STATE, currentScenario, reducer } from "../state/AppState";

describe("reducer — ANALYZE_START", () => {
  it("sets status loading and stores requestText", () => {
    const s = reducer(INITIAL_STATE, {
      type: "ANALYZE_START",
      payload: { requestText: "hello" },
    });
    expect(s.status).toBe("loading");
    expect(s.requestText).toBe("hello");
    expect(s.error).toBeNull();
  });

  it("clears previous result, decision, mask, and resets step on new analysis", () => {
    const stateWithResult = reducer(INITIAL_STATE, {
      type: "ANALYZE_SUCCESS",
      payload: FIXTURE_ANALYSIS,
    });
    const withDecision = {
      ...stateWithResult,
      activeStep: 5,
      decision: {
        req_id: "R1",
        option_id: "buy",
        verb: "Approve" as const,
        decided_by: "Alice",
        relaxed_mask: "00000",
        reason: "ok",
        recorded_at: "2026-01-01T00:00:00Z",
      },
      selectedPersonId: "E-031",
    };
    const s = reducer(withDecision, {
      type: "ANALYZE_START",
      payload: { requestText: "new req" },
    });
    expect(s.result).toBeNull();
    expect(s.decision).toBeNull();
    expect(s.selectedPersonId).toBeNull();
    expect(s.mask).toBe("00000");
    expect(s.activeStep).toBe(1);
  });
});

describe("reducer — ANALYZE_SUCCESS", () => {
  it("sets status ready and resets mask to all-zeros", () => {
    const s = reducer(INITIAL_STATE, {
      type: "ANALYZE_SUCCESS",
      payload: FIXTURE_ANALYSIS,
    });
    expect(s.status).toBe("ready");
    expect(s.result).toBe(FIXTURE_ANALYSIS);
    const expectedLen = FIXTURE_ANALYSIS.redline.constraint_order.length;
    expect(s.mask).toBe("0".repeat(expectedLen));
  });

  it("clears decision and selectedPersonId on new analysis", () => {
    const withDecision = {
      ...INITIAL_STATE,
      decision: {
        req_id: "R1",
        option_id: "buy",
        verb: "Approve" as const,
        decided_by: "Alice",
        relaxed_mask: "00000",
        reason: "ok",
        recorded_at: "2026-01-01T00:00:00Z",
      },
      selectedPersonId: "E-031",
    };
    const s = reducer(withDecision, {
      type: "ANALYZE_SUCCESS",
      payload: FIXTURE_ANALYSIS,
    });
    expect(s.decision).toBeNull();
    expect(s.selectedPersonId).toBeNull();
  });

  it("resets activeStep to 1 on success", () => {
    let s = reducer(INITIAL_STATE, { type: "SET_STEP", payload: 5 });
    s = reducer(s, { type: "ANALYZE_SUCCESS", payload: FIXTURE_ANALYSIS });
    expect(s.activeStep).toBe(1);
  });
});

describe("reducer — ANALYZE_ERROR", () => {
  it("sets status error and stores message", () => {
    const s = reducer(INITIAL_STATE, {
      type: "ANALYZE_ERROR",
      payload: "Something went wrong",
    });
    expect(s.status).toBe("error");
    expect(s.error).toBe("Something went wrong");
  });
});

describe("reducer — SET_STEP", () => {
  it("switches activeStep", () => {
    const s = reducer(INITIAL_STATE, { type: "SET_STEP", payload: 5 });
    expect(s.activeStep).toBe(5);
  });
});

describe("reducer — TOGGLE_CONSTRAINT", () => {
  const base = reducer(INITIAL_STATE, {
    type: "ANALYZE_SUCCESS",
    payload: FIXTURE_ANALYSIS,
  });

  it("flips a single bit in the mask", () => {
    const s = reducer(base, {
      type: "TOGGLE_CONSTRAINT",
      payload: { index: 2, relaxed: true },
    });
    expect(s.mask[2]).toBe("1");
    expect(s.mask[0]).toBe("0");
  });

  it("restores a bit when relaxed=false", () => {
    let s = reducer(base, {
      type: "TOGGLE_CONSTRAINT",
      payload: { index: 2, relaxed: true },
    });
    s = reducer(s, {
      type: "TOGGLE_CONSTRAINT",
      payload: { index: 2, relaxed: false },
    });
    expect(s.mask[2]).toBe("0");
  });
});

describe("reducer — SELECT_PERSON", () => {
  it("stores selectedPersonId", () => {
    const s = reducer(INITIAL_STATE, { type: "SELECT_PERSON", payload: "E-031" });
    expect(s.selectedPersonId).toBe("E-031");
  });

  it("clears selectedPersonId when null", () => {
    let s = reducer(INITIAL_STATE, { type: "SELECT_PERSON", payload: "E-031" });
    s = reducer(s, { type: "SELECT_PERSON", payload: null });
    expect(s.selectedPersonId).toBeNull();
  });
});

describe("reducer — RECORD_DECISION", () => {
  it("stores the decision record", () => {
    const rec = {
      req_id: "R1",
      option_id: "mix",
      verb: "Approve" as const,
      decided_by: "Bob",
      relaxed_mask: "00000",
      reason: "Makes sense",
      recorded_at: "2026-10-10T12:00:00Z",
    };
    const s = reducer(INITIAL_STATE, { type: "RECORD_DECISION", payload: rec });
    expect(s.decision).toEqual(rec);
  });
});

describe("reducer — DISMISS_ERROR", () => {
  it("clears error", () => {
    const errState = reducer(INITIAL_STATE, {
      type: "ANALYZE_ERROR",
      payload: "oops",
    });
    const s = reducer(errState, { type: "DISMISS_ERROR" });
    expect(s.error).toBeNull();
  });
});

describe("currentScenario selector", () => {
  it("returns null when result is null", () => {
    expect(currentScenario(INITIAL_STATE)).toBeNull();
  });

  it("returns the scenario matching the current mask", () => {
    const s = reducer(INITIAL_STATE, {
      type: "ANALYZE_SUCCESS",
      payload: FIXTURE_ANALYSIS,
    });
    const scenario = currentScenario(s);
    expect(scenario).not.toBeNull();
    expect(typeof scenario).toBe("object");
  });
});
