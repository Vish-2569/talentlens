import type { ReactNode } from "react";

interface Props {
  as?: "h1" | "h2" | "h3" | "h4";
  children: ReactNode;
  className?: string;
}

export function SectionHeader({ as: Tag = "h2", children, className = "" }: Props) {
  return (
    <Tag
      className={`font-serif font-semibold text-ink ${className}`}
    >
      {children}
    </Tag>
  );
}
