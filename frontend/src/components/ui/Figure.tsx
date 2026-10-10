interface Props {
  value: string;
  unit?: string;
  caption: string;
  size?: "lg" | "md";
}

export function Figure({ value, unit, caption, size = "lg" }: Props) {
  const numClass = size === "lg" ? "text-figure-lg" : "text-figure-md";

  return (
    <div className="flex flex-col gap-0.5">
      <div className={`font-mono ${numClass} text-ink`}>
        <span>{value}</span>
        {unit && (
          <span className="ml-0.5 text-base font-normal text-muted">{unit}</span>
        )}
      </div>
      <p className="text-xs font-sans text-muted leading-tight">{caption}</p>
    </div>
  );
}
