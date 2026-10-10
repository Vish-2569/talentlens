import { useEffect, useSyncExternalStore } from "react";
import type { components } from "../api/types";
import { getPersonSkills } from "../api/client";
import { Drawer } from "./ui";
import { SkillBar } from "./SkillBar";

type SkillScore = components["schemas"]["SkillScore"];

interface Props {
  personId: string | null;
  onClose: () => void;
  displayName?: string;
  subtitle?: string;
}

// ── Module-level cache with subscription support ─────────────────────────

type CacheEntry = { skills: SkillScore[] } | { error: string } | { loading: true };

const store = new Map<string, CacheEntry>();
const listeners = new Set<() => void>();
let version = 0;

function notify() {
  version++;
  for (const fn of listeners) fn();
}

function subscribe(fn: () => void) {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

function getSnapshot() {
  return version;
}

function ensureEntry(id: string) {
  if (store.has(id)) return;
  store.set(id, { loading: true });
  notify();

  getPersonSkills(id).then(
    (skills) => {
      store.set(id, { skills });
      notify();
    },
    (e) => {
      store.set(id, { error: e instanceof Error ? e.message : "Failed to load skills" });
      notify();
    },
  );
}

export function clearPersonCache() {
  store.clear();
  notify();
}

// ── Component ────────────────────────────────────────────────────────────

export function PersonDrawer({ personId, onClose, displayName, subtitle }: Props) {
  useSyncExternalStore(subscribe, getSnapshot);

  useEffect(() => {
    if (personId) ensureEntry(personId);
  }, [personId]);

  const entry = personId ? store.get(personId) ?? null : null;
  const loading = entry !== null && "loading" in entry;
  const error = entry !== null && "error" in entry ? entry.error : null;
  const skills = entry !== null && "skills" in entry ? entry.skills : null;

  const ignored = skills?.flatMap((s) =>
    s.ignored.map((ig) => ({
      skill: s.skill,
      ...ig,
    })),
  );

  return (
    <Drawer
      open={personId !== null}
      onOpenChange={(open) => {
        if (!open) onClose();
      }}
      title={displayName ?? personId ?? "Person"}
      description={subtitle}
    >
      {loading && (
        <p className="py-8 text-center font-sans text-sm text-muted">
          Loading skills…
        </p>
      )}

      {error && (
        <p className="rounded border border-redline/20 bg-redline/5 px-3 py-2 font-sans text-sm text-redline">
          {error}
        </p>
      )}

      {skills && (
        <div className="space-y-1">
          {skills.map((s) => (
            <SkillBar key={s.skill} skill={s} />
          ))}
        </div>
      )}

      {ignored && ignored.length > 0 && (
        <div className="mt-6 border-t border-hairline pt-4">
          <h4 className="mb-2 font-sans text-xs font-medium text-muted">
            Ignored sources
          </h4>
          <ul className="space-y-1 font-sans text-xs text-muted">
            {ignored.map((ig, i) => (
              <li key={`${ig.skill}-${ig.source}-${i}`}>
                <span className="font-medium text-ink">
                  {ig.skill.replace(/_/g, " ")}
                </span>{" "}
                — {ig.source} ({ig.value}): {ig.reason}
              </li>
            ))}
          </ul>
        </div>
      )}
    </Drawer>
  );
}
