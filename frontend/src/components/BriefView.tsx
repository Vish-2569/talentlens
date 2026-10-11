import { useState, useCallback } from "react";
import { ChevronDown, ChevronRight, Download, ExternalLink } from "lucide-react";
import { Button } from "./ui";
import { SafeMarkdown } from "./SafeMarkdown";
import { DataQualityLine } from "./DataQualityLine";
import type { components } from "../api/types";

type BriefSection = components["schemas"]["BriefSection"];
type Brief = components["schemas"]["Brief"];
type DataQuality = components["schemas"]["DataQuality"];

interface Props {
  brief: Brief;
  dataQuality: DataQuality;
  reqId: string;
}

function sectionId(key: string) {
  return `brief-section-${key}`;
}

function CollapsibleSection({
  section,
  open,
  onToggle,
  isEvidenceSection,
}: {
  section: BriefSection;
  open: boolean;
  onToggle: () => void;
  isEvidenceSection: boolean;
}) {
  const Icon = open ? ChevronDown : ChevronRight;
  const contentId = `brief-content-${section.key}`;
  const headingId = sectionId(section.key);

  return (
    <div className="border-b border-hairline last:border-b-0">
      <button
        id={headingId}
        type="button"
        onClick={onToggle}
        aria-expanded={open}
        aria-controls={contentId}
        className="flex w-full items-center gap-2 px-1 py-2 text-left font-serif text-sm font-semibold text-ink focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
      >
        <Icon size={16} strokeWidth={1.5} aria-hidden="true" />
        {section.title}
      </button>
      {open && (
        <div
          id={contentId}
          role="region"
          aria-labelledby={headingId}
          className="pb-3 pl-6 pr-1"
        >
          <SafeMarkdown markdown={section.markdown} />
          {isEvidenceSection && (
            <p className="mt-2 rounded border border-amber/20 bg-amber/5 px-2 py-1 font-sans text-xs text-amber">
              All data in this brief is simulated for demonstration purposes.
            </p>
          )}
        </div>
      )}
    </div>
  );
}

export function BriefView({ brief, dataQuality, reqId }: Props) {
  const [openKeys, setOpenKeys] = useState<Set<string>>(
    () => new Set(brief.sections.map((s) => s.key)),
  );

  const toggle = useCallback((key: string) => {
    setOpenKeys((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }, []);

  const downloadMarkdown = useCallback(() => {
    const blob = new Blob([brief.markdown], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${reqId}-brief.md`;
    a.click();
    URL.revokeObjectURL(url);
  }, [brief.markdown, reqId]);

  const downloadHtml = useCallback(() => {
    const blob = new Blob([brief.html], { type: "text/html" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${reqId}-brief.html`;
    a.click();
    URL.revokeObjectURL(url);
  }, [brief.html, reqId]);

  const openPrintable = useCallback(() => {
    const blob = new Blob([brief.html], { type: "text/html" });
    const url = URL.createObjectURL(blob);
    window.open(url, "_blank");
  }, [brief.html]);

  return (
    <section aria-labelledby="brief-heading" className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h3 id="brief-heading" className="font-serif text-base font-semibold">
          Workforce Intelligence Brief
        </h3>
        <div className="flex flex-wrap gap-2">
          <Button
            variant="secondary"
            onClick={downloadMarkdown}
            aria-label="Download brief as Markdown"
          >
            <Download size={14} strokeWidth={1.5} aria-hidden="true" />
            Markdown
          </Button>
          <Button
            variant="secondary"
            onClick={downloadHtml}
            aria-label="Download brief as HTML"
          >
            <Download size={14} strokeWidth={1.5} aria-hidden="true" />
            HTML
          </Button>
          <Button
            variant="secondary"
            onClick={openPrintable}
            aria-label="Open printable version"
          >
            <ExternalLink size={14} strokeWidth={1.5} aria-hidden="true" />
            Print
          </Button>
        </div>
      </div>

      {/* Jump list */}
      <nav aria-label="Brief sections" className="rounded border border-hairline bg-surface p-3">
        <ol className="columns-2 gap-x-6 font-sans text-xs">
          {brief.sections.map((s, i) => (
            <li key={s.key}>
              <a
                href={`#${sectionId(s.key)}`}
                className="text-accent underline-offset-2 hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
              >
                {i + 1}. {s.title}
              </a>
            </li>
          ))}
        </ol>
      </nav>

      {/* Data quality line */}
      <DataQualityLine line={dataQuality.line} />

      {/* Sections */}
      <div className="rounded border border-hairline bg-paper">
        {brief.sections.map((s) => (
          <CollapsibleSection
            key={s.key}
            section={s}
            open={openKeys.has(s.key)}
            onToggle={() => toggle(s.key)}
            isEvidenceSection={s.key === "data_quality"}
          />
        ))}
      </div>
    </section>
  );
}
