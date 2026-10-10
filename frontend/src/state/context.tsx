import { createContext, useContext, useReducer } from "react";
import type { Dispatch, ReactNode } from "react";
import type { components } from "../api/types";

type AnalysisResult = components["schemas"]["AnalysisResult"];

export interface AppState {
  analysis: AnalysisResult | null;
  activeTab: 0 | 1 | 2;
  relaxedMask: string; // 5-bit string "00000"–"11111"
  decisionRecorded: boolean;
  loading: boolean;
  error: string | null;
}

export type Action =
  | { type: "ANALYZE_START" }
  | { type: "ANALYZE_SUCCESS"; payload: AnalysisResult }
  | { type: "ANALYZE_ERROR"; payload: string }
  | { type: "SET_TAB"; payload: 0 | 1 | 2 }
  | { type: "TOGGLE_CONSTRAINT"; payload: { index: number; relaxed: boolean } }
  | { type: "DECISION_RECORDED" }
  | { type: "DISMISS_ERROR" };

const initial: AppState = {
  analysis: null,
  activeTab: 0,
  relaxedMask: "00000",
  decisionRecorded: false,
  loading: false,
  error: null,
};

function reducer(state: AppState, action: Action): AppState {
  switch (action.type) {
    case "ANALYZE_START":
      return { ...state, loading: true, error: null };
    case "ANALYZE_SUCCESS":
      return {
        ...state,
        loading: false,
        analysis: action.payload,
        relaxedMask: "00000",
        decisionRecorded: false,
      };
    case "ANALYZE_ERROR":
      return { ...state, loading: false, error: action.payload };
    case "SET_TAB":
      return { ...state, activeTab: action.payload };
    case "TOGGLE_CONSTRAINT": {
      const chars = state.relaxedMask.split("");
      chars[action.payload.index] = action.payload.relaxed ? "1" : "0";
      return { ...state, relaxedMask: chars.join("") };
    }
    case "DECISION_RECORDED":
      return { ...state, decisionRecorded: true };
    case "DISMISS_ERROR":
      return { ...state, error: null };
    default:
      return state;
  }
}

const StateCtx = createContext<AppState>(initial);
const DispatchCtx = createContext<Dispatch<Action>>(() => undefined);

export function AppProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(reducer, initial);
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
