import type { components } from "../api/types";
import { InfoTip } from "./ui";
import { SourceTag } from "./SourceTag";
import { Info } from "lucide-react";

type SkillScore = components["schemas"]["SkillScore"];

interface Props {
  skill: SkillScore;
}

function formatSkillName(id: string): string {
  return id
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export function SkillBar({ skill }: Props) {
  const pct = Math.max(0, Math.min(100, skill.value));
  const accessibleName = `${formatSkillName(skill.skill)}: ${pct}%`;

  return (
    <div className="flex items-center gap-3 py-1.5">
      <span className="w-28 shrink-0 truncate font-sans text-xs text-ink">
        {formatSkillName(skill.skill)}
      </span>

      <div className="flex flex-1 items-center gap-2">
        <div
          role="meter"
          aria-valuenow={pct}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label={accessibleName}
          className="relative h-2 flex-1 rounded-full bg-hairline"
        >
          <div
            className="absolute inset-y-0 left-0 rounded-full bg-accent transition-[width] duration-150"
            style={{ width: `${pct}%` }}
          />
        </div>

        <span className="w-8 shrink-0 text-right font-mono text-xs text-ink">
          {pct}
        </span>
      </div>

      <SourceTag
        source={skill.source as "assessment" | "certification" | "project" | "self"}
        observed_on={skill.observed_on}
        stale={skill.stale}
        conflict={skill.conflict}
      />

      <InfoTip content={skill.tooltip} aria-label={`Details for ${formatSkillName(skill.skill)}`}>
        <Info size={14} strokeWidth={1.5} className="text-muted" aria-hidden="true" />
      </InfoTip>
    </div>
  );
}
