import { Award, Briefcase, CheckCircle, User } from "lucide-react";
import { VisuallyHidden } from "./ui";

type Source = "assessment" | "certification" | "project" | "self";

interface Props {
  source: Source;
  observed_on: string;
  stale: boolean;
  conflict: boolean;
}

const SOURCE_CONFIG: Record<
  Source,
  {
    Icon: typeof CheckCircle;
    label: string;
    tagClass: string;
  }
> = {
  assessment: {
    Icon: CheckCircle,
    label: "Assessment",
    tagClass: "bg-accent/10 text-accent border border-accent/30",
  },
  certification: {
    Icon: Award,
    label: "Certification",
    tagClass: "bg-accent/10 text-accent border border-accent/30",
  },
  project: {
    Icon: Briefcase,
    label: "Project",
    tagClass:
      "bg-accent/5 text-accent border border-accent/30 border-dashed",
  },
  self: {
    Icon: User,
    label: "Self-report",
    tagClass: "bg-transparent text-muted border border-muted/40 border-dashed",
  },
};

function formatDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString("en-IN", { month: "short", year: "numeric" });
}

export function SourceTag({ source, observed_on, stale, conflict }: Props) {
  const cfg = SOURCE_CONFIG[source] ?? SOURCE_CONFIG.self;
  const { Icon, label, tagClass } = cfg;

  return (
    <span
      className={`inline-flex items-center gap-1 rounded px-1.5 py-0.5 font-sans text-xs ${tagClass}`}
      data-source={source}
    >
      <Icon size={12} strokeWidth={1.5} aria-hidden="true" />
      <span>{label}</span>
      <span className="text-muted">{formatDate(observed_on)}</span>
      {stale && <span className="font-medium text-amber">(stale)</span>}
      {conflict && (
        <>
          <span aria-hidden="true" className="text-amber">
            {"⚠"}
          </span>
          <VisuallyHidden>sources disagree</VisuallyHidden>
        </>
      )}
    </span>
  );
}
