import type { ReactNode } from "react";

type Line = string;

function parseInline(text: string): ReactNode[] {
  const parts: ReactNode[] = [];
  let remaining = text;
  let key = 0;

  while (remaining.length > 0) {
    const boldIdx = remaining.indexOf("**");
    if (boldIdx === -1) {
      parts.push(remaining);
      break;
    }
    if (boldIdx > 0) {
      parts.push(remaining.slice(0, boldIdx));
    }
    const endIdx = remaining.indexOf("**", boldIdx + 2);
    if (endIdx === -1) {
      parts.push(remaining);
      break;
    }
    parts.push(
      <strong key={key++}>{remaining.slice(boldIdx + 2, endIdx)}</strong>,
    );
    remaining = remaining.slice(endIdx + 2);
  }
  return parts;
}

function parseTable(lines: Line[]): ReactNode {
  const rows = lines
    .filter((l) => l.trim().length > 0)
    .filter((l) => !/^\|[\s-:|]+\|$/.test(l.trim()));

  if (rows.length === 0) return null;

  const parseRow = (row: string) =>
    row
      .split("|")
      .slice(1, -1)
      .map((cell) => cell.trim());

  const headerCells = parseRow(rows[0]);
  const bodyRows = rows.slice(1).map(parseRow);

  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse font-sans text-sm">
        <thead>
          <tr>
            {headerCells.map((cell, i) => (
              <th
                key={i}
                className="border border-hairline bg-surface px-2 py-1 text-left font-medium"
              >
                {parseInline(cell)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {bodyRows.map((row, ri) => (
            <tr key={ri}>
              {row.map((cell, ci) => (
                <td key={ci} className="border border-hairline px-2 py-1">
                  {parseInline(cell)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function SafeMarkdown({ markdown }: { markdown: string }) {
  const lines = markdown.split("\n");
  const elements: ReactNode[] = [];
  let i = 0;
  let key = 0;

  while (i < lines.length) {
    const line = lines[i];

    if (line.trim() === "") {
      i++;
      continue;
    }

    if (line.trim().startsWith("|")) {
      const tableLines: string[] = [];
      while (i < lines.length && lines[i].trim().startsWith("|")) {
        tableLines.push(lines[i]);
        i++;
      }
      elements.push(<div key={key++}>{parseTable(tableLines)}</div>);
      continue;
    }

    if (/^[-*]\s/.test(line.trim())) {
      const items: string[] = [];
      while (i < lines.length && /^[-*]\s/.test(lines[i].trim())) {
        items.push(lines[i].trim().replace(/^[-*]\s+/, ""));
        i++;
      }
      elements.push(
        <ul key={key++} className="list-disc space-y-1 pl-5 font-sans text-sm">
          {items.map((item, j) => (
            <li key={j}>{parseInline(item)}</li>
          ))}
        </ul>,
      );
      continue;
    }

    if (/^\d+\.\s/.test(line.trim())) {
      const items: string[] = [];
      while (i < lines.length && /^\d+\.\s/.test(lines[i].trim())) {
        items.push(lines[i].trim().replace(/^\d+\.\s+/, ""));
        i++;
      }
      elements.push(
        <ol key={key++} className="list-decimal space-y-1 pl-5 font-sans text-sm">
          {items.map((item, j) => (
            <li key={j}>{parseInline(item)}</li>
          ))}
        </ol>,
      );
      continue;
    }

    elements.push(
      <p key={key++} className="font-sans text-sm">
        {parseInline(line)}
      </p>,
    );
    i++;
  }

  return <div className="space-y-2">{elements}</div>;
}
