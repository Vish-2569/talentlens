import type { ReactNode } from "react";

interface Props {
  children?: ReactNode;
  id?: string;
}

export function LiveRegion({ children, id }: Props) {
  return (
    <div
      role="status"
      aria-live="polite"
      aria-atomic="true"
      id={id}
      className="sr-only"
    >
      {children}
    </div>
  );
}
