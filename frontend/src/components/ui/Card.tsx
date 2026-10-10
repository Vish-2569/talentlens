import type { ReactNode } from "react";

interface Props {
  children: ReactNode;
  header?: { title: string; meaning?: string };
  className?: string;
  id?: string;
}

export function Card({ children, header, className = "", id }: Props) {
  return (
    <div
      id={id}
      className={[
        "rounded-md border border-hairline bg-surface p-4",
        className,
      ].join(" ")}
    >
      {header && (
        <div className="mb-3 border-b border-hairline pb-2">
          <h3 className="font-serif text-base font-semibold text-ink">
            {header.title}
          </h3>
          {header.meaning && (
            <p className="mt-0.5 text-xs font-sans text-muted">
              {header.meaning}
            </p>
          )}
        </div>
      )}
      {children}
    </div>
  );
}
