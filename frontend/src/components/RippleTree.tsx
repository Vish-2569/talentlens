import { AlertTriangle, Check } from "lucide-react";
import type { components } from "../api/types";

type RippleNode = components["schemas"]["RippleNode"];
type RippleFlag = components["schemas"]["RippleFlag"];

interface Props {
  node: RippleNode;
  depth?: number;
  onPersonClick: (personId: string, displayName: string) => void;
}

function hasFlag(flags: RippleFlag[], type: string): boolean {
  return flags.some((f) => f.type === type);
}

function statusLabels(node: RippleNode): {
  borderClass: string;
  Icon: typeof AlertTriangle;
  iconClass: string;
  labels: string[];
} {
  const flags = node.flags ?? [];
  if (node.status === "red") {
    const labels: string[] = [];
    if (hasFlag(flags, "bus_factor")) labels.push("Bus factor = 1");
    if (
      hasFlag(flags, "no_internal_backfill") ||
      hasFlag(flags, "hard_market")
    )
      labels.push("Hard to fill");
    if (labels.length === 0) labels.push("Hard to fill");
    return {
      borderClass: "border-2 border-redline",
      Icon: AlertTriangle,
      iconClass: "text-redline",
      labels,
    };
  }
  return {
    borderClass: "border border-green",
    Icon: Check,
    iconClass: "text-green",
    labels: ["Can be filled"],
  };
}

function formatSeat(seat: string): string {
  const [level, team] = seat.split("/");
  if (!team) return level;
  return `${level.charAt(0).toUpperCase() + level.slice(1)} · ${team}`;
}

function TreeNode({ node, depth = 0, onPersonClick }: Props) {
  const cfg = statusLabels(node);
  const { Icon, iconClass, labels, borderClass } = cfg;
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
          <div className="flex shrink-0 flex-col items-end gap-1">
            {labels.map((lbl) => (
              <span key={lbl} className={`flex items-center gap-1 font-sans text-xs font-medium ${iconClass}`}>
                <Icon size={14} strokeWidth={1.5} aria-hidden="true" />
                {lbl}
              </span>
            ))}
          </div>
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
