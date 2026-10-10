import type { components } from "../api/types";
import { Badge, Card } from "./ui";

type ContractorCard = components["schemas"]["ContractorCard"];

interface Props {
  cards: ContractorCard[];
  onSelectPerson: (id: string) => void;
}

export function ContractorCards({ cards, onSelectPerson }: Props) {
  if (cards.length === 0) return null;
  const top = cards[0];
  const rest = cards.slice(1);

  return (
    <Card header={{ title: "Contractors", meaning: `${cards.length} analysed` }}>
      <button
        type="button"
        onClick={() => onSelectPerson(top.person_id)}
        className="w-full rounded border border-hairline bg-paper p-3 text-left hover:border-accent focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
      >
        <div className="flex items-center justify-between">
          <span className="font-sans text-sm font-semibold text-ink">
            {top.display_name}
          </span>
          <Badge variant="accent">{top.fit}% fit</Badge>
        </div>
        <p className="mt-1 font-sans text-xs text-muted">{top.availability}</p>
        <div className="mt-2 flex flex-wrap gap-2 font-mono text-xs text-muted">
          <span>₹{top.extend_cost_lpa}L/yr</span>
          {top.conversion_signal && <Badge variant="green">Convert</Badge>}
          {top.compliance_flag && <Badge variant="red">Compliance</Badge>}
        </div>
      </button>

      {rest.length > 0 && (
        <ul className="mt-3 flex flex-col gap-1">
          {rest.map((c) => (
            <li key={c.person_id}>
              <button
                type="button"
                onClick={() => onSelectPerson(c.person_id)}
                className="flex w-full items-center justify-between rounded px-2 py-1 font-sans text-xs text-muted hover:bg-paper focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
              >
                <span>{c.display_name}</span>
                <span className="font-mono">{c.fit}% · ₹{c.extend_cost_lpa}L</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
