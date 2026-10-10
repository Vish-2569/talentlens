import type { ReactNode } from "react";

type Variant = "default" | "accent" | "red" | "amber" | "green" | "muted";

interface Props {
  children: ReactNode;
  variant?: Variant;
  className?: string;
}

const variantClasses: Record<Variant, string> = {
  default: "bg-paper text-ink border-hairline border",
  accent: "bg-accent text-white",
  red: "bg-[#FEF2F2] text-redline border border-[#FECACA]",
  amber: "bg-[#FFFBEB] text-amber border border-[#FDE68A]",
  green: "bg-[#F0FDF4] text-green border border-[#BBF7D0]",
  muted: "bg-paper text-muted border border-hairline",
};

export function Badge({ children, variant = "default", className = "" }: Props) {
  return (
    <span
      className={[
        "inline-flex items-center rounded px-1.5 py-0.5 font-mono text-xs",
        variantClasses[variant],
        className,
      ].join(" ")}
    >
      {children}
    </span>
  );
}
