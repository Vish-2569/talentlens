import { useAppState } from "../state/context";

export function parseActionItems(markdown: string): string[] {
  return markdown
    .split("\n")
    .map((line) => line.replace(/^\d+\.\s*/, "").trim())
    .filter(Boolean);
}

export function ActionsPanel() {
  const { result } = useAppState();
  const actionsSection = result!.brief.sections.find(
    (s) => s.key === "actions",
  );
  const items = actionsSection ? parseActionItems(actionsSection.markdown) : [];

  return (
    <section
      id="actions-section"
      aria-labelledby="actions-heading"
      className="space-y-3"
    >
      <h3
        id="actions-heading"
        className="font-serif font-semibold text-ink"
      >
        Next actions
      </h3>
      {items.length === 0 ? (
        <p className="font-sans text-sm text-muted">No actions generated.</p>
      ) : (
        <ul className="space-y-2" aria-label="Draft actions">
          {items.map((item, i) => (
            <li
              key={i}
              className="flex items-start justify-between gap-3 rounded border border-hairline bg-surface p-3"
            >
              <span className="font-sans text-sm">{item}</span>
              <span className="shrink-0 rounded border border-hairline px-1.5 py-0.5 font-sans text-[10px] text-muted">
                Draft, not sent
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
