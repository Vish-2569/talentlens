import { AlertTriangle, Check } from "lucide-react";
import type { components } from "../api/types";

type RippleNode = components["schemas"]["RippleNode"];

interface Props {
  node: RippleNode;
  depth?: number;
  onPersonClick: (personId: string, displayName: string) => void;
}

function statusConfig(status: string, reason: string) {
  if (status === "red") {
    const label = reason.toLowerCase().includes("bus factor")
      ? "Bus factor = 1"
      : "Hard to fill";
    return {
      borderClass: "border-2 border-redline",
      Icon: AlertTriangle,
      iconClass: "text-redline",
      label,
    };
  }
  return {
    borderClass: "border border-green",
    Icon: Check,
    iconClass: "text-green",
    label: "Can be filled",
  };
}

function formatSeat(seat: string): string {
  const [level, team] = seat.split("/");
  if (!team) return level;
  return `${level.charAt(0).toUpperCase() + level.slice(1)} · ${team}`;
}

function TreeNode({ node, depth = 0, onPersonClick }: Props) {
  const cfg = statusConfig(node.status, node.reason);
  const { Icon, iconClass, label, borderClass } = cfg;
  const indent = depth * 24;

  return (
    <li>
      <div
        className={`rounded-md bg-surface p-3 ${borderClass}`}
        style={{ marginLeft: indent }}
      >
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0 flex-1">
            <p className="font-sans text-sm font-medium text-ink">
              {formatSeat(node.seat)}
            </p>
            {node.person_id && node.display_name ? (
              <button
                type="button"
                onClick={() => onPersonClick(node.person_id!, node.display_name!)}
                className="mt-0.5 font-sans text-xs text-accent underline underline-offset-2 hover:text-ink focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent"
              >
                {node.display_name}
              </button>
            ) : (
              <p className="mt-0.5 font-sans text-xs text-muted italic">
                No internal backfill
              </p>
            )}
            <p className="mt-1 font-sans text-xs text-muted">{node.reason}</p>
          </div>
          <span className={`flex shrink-0 items-center gap-1 font-sans text-xs font-medium ${iconClass}`}>
            <Icon size={14} strokeWidth={1.5} aria-hidden="true" />
            {label}
          </span>
        </div>
      </div>

      {node.children && node.children.length > 0 && (
        <ul className="mt-2 space-y-2">
          {node.children.map((child, i) => (
            <TreeNode
              key={child.seat + i}
              node={child}
              depth={depth + 1}
              onPersonClick={onPersonClick}
            />
          ))}
        </ul>
      )}
    </li>
  );
}

export function RippleTree({ node, onPersonClick }: Omit<Props, "depth">) {
  return (
    <ul className="space-y-2" aria-label="Ripple chain">
      <TreeNode node={node} depth={0} onPersonClick={onPersonClick} />
    </ul>
  );
}
