import * as Popover from "@radix-ui/react-popover";
import * as Tooltip from "@radix-ui/react-tooltip";
import type { ReactNode } from "react";

interface Props {
  content: ReactNode;
  children: ReactNode;
  "aria-label"?: string;
}

const contentClass =
  "z-50 max-w-xs rounded-md border border-hairline bg-surface px-3 py-2 text-xs font-sans text-ink shadow-sm";

export function InfoTip({ content, children, "aria-label": ariaLabel }: Props) {
  return (
    <Tooltip.Provider delayDuration={0}>
      <Popover.Root>
        <Tooltip.Root>
          <Tooltip.Trigger asChild>
            <Popover.Trigger asChild>
              <button
                type="button"
                aria-label={ariaLabel}
                className="inline-flex cursor-help items-center rounded focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
              >
                {children}
              </button>
            </Popover.Trigger>
          </Tooltip.Trigger>

          <Tooltip.Portal>
            <Tooltip.Content side="top" sideOffset={4} className={contentClass}>
              {content}
              <Tooltip.Arrow className="fill-hairline" />
            </Tooltip.Content>
          </Tooltip.Portal>
        </Tooltip.Root>

        <Popover.Portal>
          <Popover.Content side="top" sideOffset={4} className={contentClass}>
            {content}
            <Popover.Arrow className="fill-hairline" />
          </Popover.Content>
        </Popover.Portal>
      </Popover.Root>
    </Tooltip.Provider>
  );
}
