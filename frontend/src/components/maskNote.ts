import type { components } from "../api/types";

type ConstraintKind = components["schemas"]["ConstraintKind"];
type Constraint = components["schemas"]["Constraint"];

function relaxedPhrase(kind: ConstraintKind, constraint: Constraint): string {
  switch (kind) {
    case "location":
      return "any location (including Remote-India)";
    case "years":
      return "experience requirement relaxed";
    case "skill": {
      const skillName = constraint.value.replace(/^must know\s+/i, "").trim();
      return `${skillName} treated as nice-to-have`;
    }
    case "budget":
      return "budget at market rate";
    case "deadline":
      return `deadline relaxed (was: ${constraint.phrase})`;
    default:
      return kind;
  }
}

export function describeMaskNote(
  mask: string,
  constraintOrder: ConstraintKind[],
  constraints: Constraint[],
): { assumeText: string; keptText: string | null } {
  const byKind = new Map(constraints.map((c) => [c.kind, c]));
  const relaxed: string[] = [];
  const kept: string[] = [];

  for (let i = 0; i < mask.length; i++) {
    const kind = constraintOrder[i];
    const c = byKind.get(kind);
    if (!c) continue;
    if (mask[i] === "1") {
      relaxed.push(relaxedPhrase(kind, c));
    } else {
      kept.push(c.phrase);
    }
  }

  const assumeText =
    relaxed.length === 0
      ? "the request as written"
      : relaxed.join(", ");
  const keptText = kept.length > 0 ? kept.join(", ") : null;
  return { assumeText, keptText };
}
