import type { components } from "../api/types";

type TitleNormalization = components["schemas"]["TitleNormalization"];

interface Props {
  titleNormalization: TitleNormalization;
}

export function TitleNormPanel({ titleNormalization }: Props) {
  const { raw_titles_count, role, levels, mappings } = titleNormalization;

  return (
    <details className="rounded-md border border-hairline">
      <summary className="cursor-pointer px-4 py-3 font-sans text-sm font-medium text-ink hover:bg-paper focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent">
        {raw_titles_count} raw titles &rarr; 1 role ({role}),{" "}
        {levels.length} levels
      </summary>

      <div className="overflow-x-auto border-t border-hairline px-4 py-3">
        <table className="w-full text-left font-sans text-xs">
          <thead>
            <tr className="border-b border-hairline text-muted">
              <th className="pb-2 pr-4 font-medium">Raw title</th>
              <th className="pb-2 pr-4 font-medium">Source</th>
              <th className="pb-2 pr-4 font-medium">Level</th>
              <th className="pb-2 pr-4 font-medium">Method</th>
              <th className="pb-2 pr-4 font-medium">Confidence</th>
              <th className="pb-2 pr-4 font-medium">ESCO URI</th>
              <th className="pb-2 font-medium">O*NET</th>
            </tr>
          </thead>
          <tbody>
            {mappings.map((m) => (
              <tr key={m.raw_title} className="border-b border-hairline last:border-0">
                <td className="py-1.5 pr-4 text-ink">{m.raw_title}</td>
                <td className="py-1.5 pr-4 text-muted">{m.source_system}</td>
                <td className="py-1.5 pr-4 text-ink">{m.level ?? "—"}</td>
                <td className="py-1.5 pr-4 text-muted">{m.method}</td>
                <td className="py-1.5 pr-4 font-mono text-ink">
                  {m.confidence}
                </td>
                <td className="py-1.5 pr-4 break-all font-mono text-xs text-muted">
                  {m.esco_uri ?? "—"}
                </td>
                <td className="py-1.5 font-mono text-muted">
                  {m.onet_code ?? "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </details>
  );
}
