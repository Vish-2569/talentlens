import { LiveRegion } from "./ui";

const STAGES = [
  "Reading the request",
  "Matching titles and skills",
  "Checking hiring history",
  "Pricing each constraint",
  "Tracing backfill chains",
  "Comparing five options",
  "Writing the brief",
] as const;

export function LoadingStages() {
  return (
    <div className="py-4">
      <LiveRegion>Analysing request</LiveRegion>
      <ol className="space-y-2 font-sans text-sm text-ink motion-safe:animate-pulse">
        {STAGES.map((stage) => (
          <li key={stage} className="flex items-center gap-2">
            <span
              className="inline-block h-1.5 w-1.5 rounded-full bg-accent"
              aria-hidden="true"
            />
            {stage}
          </li>
        ))}
      </ol>
    </div>
  );
}
