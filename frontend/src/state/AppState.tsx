import { createContext, useContext, useReducer } from "react";
import type { Dispatch, ReactNode } from "react";
import type { components } from "../api/types";

type AnalysisResult = components["schemas"]["AnalysisResult"];
type DecisionRequest = components["schemas"]["DecisionRequest"];

// ── Decision record ───────────────────────────────────────────────────────────

export interface DecisionRecord {
  req_id: string;
  option_id: string;
  verb: DecisionRequest["verb"];
  decided_by: string;
  relaxed_mask: string;
  reason: string;
  recorded_at: string; // ISO timestamp
}

// ── State ─────────────────────────────────────────────────────────────────────

export type TabId = "challenge" | "options" | "decide";

export interface AppState {
  status: "idle" | "loading" | "ready" | "error";
  requestText: string;
  result: AnalysisResult | null;
  /** 5-bit string aligned with redline.constraint_order; "0" = keep, "1" = relax */
  mask: string;
  activeTab: TabId;
  selectedPersonId: string | null;
  decision: DecisionRecord | null;
  error: string | null;
}

// ── Actions ───────────────────────────────────────────────────────────────────

export type Action =
  | { type: "ANALYZE_START"; payload: { requestText: string } }
  | { type: "ANALYZE_SUCCESS"; payload: AnalysisResult }
  | { type: "ANALYZE_ERROR"; payload: string }
  | { type: "SET_TAB"; payload: TabId }
  | { type: "TOGGLE_CONSTRAINT"; payload: { index: number; relaxed: boolean } }
  | { type: "RESET_MASK" }
  | { type: "SELECT_PERSON"; payload: string | null }
  | { type: "RECORD_DECISION"; payload: DecisionRecord }
  | { type: "DISMISS_ERROR" };

// ── Initial state ─────────────────────────────────────────────────────────────

export const INITIAL_STATE: AppState = {
  status: "idle",
  requestText: "",
  result: null,
  mask: "00000",
  activeTab: "challenge",
  selectedPersonId: null,
  decision: null,
  error: null,
};

// ── Reducer ───────────────────────────────────────────────────────────────────

export function reducer(state: AppState, action: Action): AppState {
  switch (action.type) {
    case "ANALYZE_START":
      return {
        ...state,
        status: "loading",
        requestText: action.payload.requestText,
        error: null,
      };

    case "ANALYZE_SUCCESS": {
      const result = action.payload;
      const constraintCount = result.redline.constraint_order.length;
      return {
        ...state,
        status: "ready",
        result,
        mask: "0".repeat(constraintCount),
        decision: null,
        selectedPersonId: null,
        error: null,
      };
    }

    case "ANALYZE_ERROR":
      return { ...state, status: "error", error: action.payload };

    case "SET_TAB":
      return { ...state, activeTab: action.payload };

    case "TOGGLE_CONSTRAINT": {
      const chars = state.mask.split("");
      chars[action.payload.index] = action.payload.relaxed ? "1" : "0";
      return { ...state, mask: chars.join("") };
    }

    case "RESET_MASK":
      return {
        ...state,
        mask: "0".repeat(state.result?.redline.constraint_order.length ?? 5),
      };

    case "SELECT_PERSON":
      return { ...state, selectedPersonId: action.payload };

    case "RECORD_DECISION":
      return { ...state, decision: action.payload };

    case "DISMISS_ERROR":
      return { ...state, error: null };

    default:
      return state;
  }
}

// ── Selectors ─────────────────────────────────────────────────────────────────

export function currentScenario(state: AppState) {
  const scenarios = state.result?.redline.scenarios;
  if (!scenarios) return null;
  return scenarios[state.mask] ?? null;
}

// ── Context + Provider ────────────────────────────────────────────────────────

const StateCtx = createContext<AppState>(INITIAL_STATE);
const DispatchCtx = createContext<Dispatch<Action>>(() => undefined);

export function AppProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(reducer, INITIAL_STATE);
  return (
    <StateCtx.Provider value={state}>
      <DispatchCtx.Provider value={dispatch}>
        {children}
      </DispatchCtx.Provider>
    </StateCtx.Provider>
  );
}

export function useAppState() {
  return useContext(StateCtx);
}

export function useAppDispatch() {
  return useContext(DispatchCtx);
}
