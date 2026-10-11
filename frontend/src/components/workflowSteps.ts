import type { components } from "../api/types";

type AnalysisResult = components["schemas"]["AnalysisResult"];

export interface StepDef {
  id: number;
  label: string;
  shortLabel: string;
  headingId: string;
}

export interface StepState extends StepDef {
  lit: boolean;
  disabled: boolean;
}

export const STEP_DEFS: StepDef[] = [
  { id: 1, label: "Workforce need",            shortLabel: "Need",        headingId: "step-1-heading" },
  { id: 2, label: "Role / skill analysis",     shortLabel: "Skills",      headingId: "step-2-heading" },
  { id: 3, label: "Internal talent",           shortLabel: "Internal",    headingId: "step-3-heading" },
  { id: 4, label: "Contractor talent",         shortLabel: "Contractors", headingId: "step-4-heading" },
  { id: 5, label: "External market",           shortLabel: "Market",      headingId: "step-5-heading" },
  { id: 6, label: "Location and compensation", shortLabel: "Location",    headingId: "step-6-heading" },
  { id: 7, label: "Five options",              shortLabel: "Options",     headingId: "step-7-heading" },
  { id: 8, label: "Human decision",            shortLabel: "Decision",    headingId: "step-8-heading" },
  { id: 9, label: "Recruiting action",         shortLabel: "Action",      headingId: "step-9-heading" },
];

export function getStepStates(
  result: AnalysisResult | null,
  decisionRecorded: boolean,
): StepState[] {
  const r = result;
  const hasResult = r !== null && r !== undefined;

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
    disabled: def.id >= 2 && !hasResult,
  }));
}
