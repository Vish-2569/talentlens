type Status = "red" | "amber" | "green";

interface Props {
  status: Status;
  className?: string;
}

const config: Record<Status, { icon: string; label: string; classes: string }> = {
  red: {
    icon: "▲",
    label: "High cost",
    classes: "text-redline border-b-2 border-redline",
  },
  amber: {
    icon: "◆",
    label: "Moderate cost",
    classes: "text-amber border-b border-dashed border-amber",
  },
  green: {
    icon: "●",
    label: "Clear",
    classes: "text-green",
  },
};

export function StatusMark({ status, className = "" }: Props) {
  const { icon, label, classes } = config[status];

  return (
    <span
      className={`inline-flex items-center gap-1 font-sans text-xs font-medium ${classes} ${className}`}
      data-status={status}
    >
      <span aria-hidden="true">{icon}</span>
      <span>{label}</span>
    </span>
  );
}
