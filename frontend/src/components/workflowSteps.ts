import type { components } from "../api/types";
import type { TabId } from "../state/AppState";

type AnalysisResult = components["schemas"]["AnalysisResult"];

export interface StepDef {
  id: number;
  label: string;
  tab: TabId;
  scrollTarget: string;
}

export interface StepState extends StepDef {
  lit: boolean;
}

export const STEP_DEFS: StepDef[] = [
  { id: 1, label: "Workforce need",            tab: "challenge", scrollTarget: "challenge-input" },
  { id: 2, label: "Role / skill analysis",     tab: "challenge", scrollTarget: "redline-section" },
  { id: 3, label: "Internal talent",           tab: "options",   scrollTarget: "ripple-section" },
  { id: 4, label: "Contractor talent",         tab: "options",   scrollTarget: "contractor-section" },
  { id: 5, label: "External market",           tab: "options",   scrollTarget: "market-section" },
  { id: 6, label: "Location and compensation", tab: "options",   scrollTarget: "relocate-section" },
  { id: 7, label: "Five options",              tab: "options",   scrollTarget: "options-section" },
  { id: 8, label: "Human decision",            tab: "decide",    scrollTarget: "decision-form" },
  { id: 9, label: "Recruiting action",         tab: "decide",    scrollTarget: "actions-section" },
];

export function getStepStates(
  result: AnalysisResult | null,
  decisionRecorded: boolean,
): StepState[] {
  const r = result;

  const litMap: Record<number, boolean> = {
    1: r?.parsed !== undefined,
    2: (r?.redline.constraints.length ?? 0) > 0,
    3: (r?.ripple.candidates.length ?? 0) > 0,
    4: (r?.options.contractor_cards.length ?? 0) > 0,
    5: r?.options.market_card !== undefined,
    6: (r?.options.relocate_card.length ?? 0) > 0,
    7: (r?.options.five.length ?? 0) > 0,
    8: decisionRecorded,
    9: decisionRecorded && (r?.brief.sections.length ?? 0) > 0,
  };

  return STEP_DEFS.map((def) => ({
    ...def,
    lit: litMap[def.id] ?? false,
  }));
}
