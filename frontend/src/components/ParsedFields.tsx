import type { components } from "../api/types";
import { Badge, InfoTip } from "./ui";

type ParsedRequisition = components["schemas"]["ParsedRequisition"];
type ParsedField = components["schemas"]["ParsedField"];
type ConfidenceLabel = components["schemas"]["ConfidenceLabel"];

const FIELD_KEYS = [
  "level",
  "headcount",
  "location",
  "work_mode",
  "min_years",
  "budget_lpa",
  "need_by_days",
  "duration_months",
  "criticality",
] as const;

const FIELD_LABELS: Record<(typeof FIELD_KEYS)[number], string> = {
  level: "Level",
  headcount: "Headcount",
  location: "Location",
  work_mode: "Work mode",
  min_years: "Years",
  budget_lpa: "Budget",
  need_by_days: "Deadline",
  duration_months: "Duration",
  criticality: "Criticality",
};

const LABEL_ICON: Record<ConfidenceLabel, string> = {
  stated: "S",
  inferred: "?",
  computed: "Σ",
  simulated: "~",
};

const LABEL_BADGE_VARIANT: Record<
  ConfidenceLabel,
  "default" | "amber" | "muted"
> = {
  stated: "default",
  inferred: "amber",
  computed: "muted",
  simulated: "muted",
};

function formatValue(key: string, value: string | number): string {
  if (key === "budget_lpa") return `₹${value}L`;
  if (key === "need_by_days") return `${value} days`;
  if (key === "min_years") return `${value}+ years`;
  if (key === "duration_months") return `${value} months`;
  return String(value);
}

interface Props {
  parsed: ParsedRequisition;
}

export function ParsedFields({ parsed }: Props) {
  const nonNullFields: { key: string; field: ParsedField; label: string }[] =
    [];
  const nullFieldNames: string[] = [];

  for (const key of FIELD_KEYS) {
    const field = parsed[key];
    if (field.value != null) {
      nonNullFields.push({ key, field, label: FIELD_LABELS[key] });
    } else {
      nullFieldNames.push(FIELD_LABELS[key].toLowerCase());
    }
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-2" role="list" aria-label="Parsed fields">
        {nonNullFields.map(({ key, field, label }) => {
          const isInferred = field.label === "inferred";
          const chip = (
            <span
              role="listitem"
              className={[
                "inline-flex items-center gap-1.5 rounded-md border px-2 py-1 font-sans text-sm",
                isInferred ? "border-dashed border-amber" : "border-hairline",
              ].join(" ")}
            >
              <span className="font-medium text-muted">{label}</span>
              <span className="text-ink">
                {formatValue(key, field.value as string | number)}
              </span>
              <Badge
                variant={LABEL_BADGE_VARIANT[field.label]}
                className="ml-0.5"
              >
                {LABEL_ICON[field.label]} {field.label}
              </Badge>
              {isInferred && (
                <span className="text-xs text-amber">Please confirm</span>
              )}
            </span>
          );

          if (field.span) {
            return (
              <InfoTip
                key={key}
                content={
                  <span>
                    From request: &ldquo;{field.span}&rdquo;
                  </span>
                }
                aria-label={`${label} source`}
              >
                {chip}
              </InfoTip>
            );
          }

          return <span key={key}>{chip}</span>;
        })}

        {parsed.skills.map((skill) => (
          <span
            key={skill.skill_id}
            role="listitem"
            className="inline-flex items-center gap-1.5 rounded-md border border-hairline px-2 py-1 font-sans text-sm"
          >
            <span className="text-ink">{skill.skill_id}</span>
            <Badge variant={skill.importance === "must" ? "accent" : "muted"}>
              {skill.importance}
            </Badge>
          </span>
        ))}
      </div>

      {nullFieldNames.length > 0 && (
        <p className="font-sans text-xs text-muted">
          Not in the request: {nullFieldNames.join(", ")}
        </p>
      )}
    </div>
  );
}
