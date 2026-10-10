import { AlertTriangle } from "lucide-react";

interface Props {
  line: string;
  className?: string;
}

export function DataQualityLine({ line, className = "" }: Props) {
  return (
    <p
      className={`inline-flex items-center gap-1.5 rounded border border-amber/20 bg-amber/5 px-3 py-1.5 font-sans text-xs text-amber ${className}`}
      role="status"
    >
      <AlertTriangle size={14} strokeWidth={1.5} aria-hidden="true" />
      {line}
    </p>
  );
}
