interface Props {
  message: string;
  onDismiss?: () => void;
}

export function ErrorBanner({ message, onDismiss }: Props) {
  return (
    <div
      role="alert"
      className="flex items-start justify-between gap-4 rounded-md border border-[#FECACA] bg-[#FEF2F2] px-4 py-3 text-sm font-sans text-redline"
    >
      <span>{message}</span>
      {onDismiss && (
        <button
          onClick={onDismiss}
          aria-label="Dismiss error"
          className="shrink-0 rounded text-redline hover:text-ink focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent"
        >
          ✕
        </button>
      )}
    </div>
  );
}
