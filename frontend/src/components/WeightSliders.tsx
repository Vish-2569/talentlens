import { useCallback, useMemo, useState } from "react";
import * as Slider from "@radix-ui/react-slider";
import type { components } from "../api/types";

type OptionCard = components["schemas"]["OptionCard"];
type MixOption = components["schemas"]["MixOption"];
type OptionWeights = components["schemas"]["OptionWeights"];

const DIMENSION_KEYS = ["speed", "cost", "fit", "risk", "strategic"] as const;
type DimKey = (typeof DIMENSION_KEYS)[number];

const LABELS: Record<DimKey, string> = {
  speed: "Speed",
  cost: "Cost",
  fit: "Fit",
  risk: "Risk",
  strategic: "Strategic",
};

function reScore(
  dims: Record<DimKey, number>,
  weights: Record<DimKey, number>,
): number {
  let raw = 0;
  for (const k of DIMENSION_KEYS) {
    raw += weights[k] * dims[k];
  }
  return Math.round(raw * 100);
}

function normalizeWeights(w: Record<DimKey, number>): Record<DimKey, number> {
  const total = DIMENSION_KEYS.reduce((s, k) => s + w[k], 0);
  if (total === 0) return w;
  const out = {} as Record<DimKey, number>;
  for (const k of DIMENSION_KEYS) out[k] = w[k] / total;
  return out;
}

export interface RankedOption {
  id: string;
  name: string;
  score: number | null;
  year_one_cost_lpa: number | null;
  atomCount?: number;
}

export interface RankedMix {
  id: string;
  name: string;
  score: number;
  year_one_cost_lpa: number;
  atomCount: number;
}

function rankOptions(
  options: OptionCard[],
  weights: Record<DimKey, number>,
): RankedOption[] {
  const scored: RankedOption[] = [];
  const unscored: RankedOption[] = [];

  for (const opt of options) {
    if (opt.dimensions == null || opt.score == null) {
      unscored.push({
        id: opt.id,
        name: opt.name,
        score: null,
        year_one_cost_lpa: opt.year_one_cost_lpa ?? null,
      });
      continue;
    }
    scored.push({
      id: opt.id,
      name: opt.name,
      score: reScore(opt.dimensions as Record<DimKey, number>, weights),
      year_one_cost_lpa: opt.year_one_cost_lpa ?? null,
    });
  }

  scored.sort((a, b) => {
    if (b.score! !== a.score!) return b.score! - a.score!;
    return (a.year_one_cost_lpa ?? 0) - (b.year_one_cost_lpa ?? 0);
  });

  return [...scored, ...unscored];
}

function rankMixes(
  mixes: MixOption[],
  weights: Record<DimKey, number>,
): RankedMix[] {
  const ranked = mixes.map((m) => ({
    id: m.id,
    name: m.name,
    score: reScore(m.dimensions as Record<DimKey, number>, weights),
    year_one_cost_lpa: m.year_one_cost_lpa,
    atomCount: m.atoms.length,
  }));

  ranked.sort((a, b) => {
    if (b.score !== a.score) return b.score - a.score;
    if (a.year_one_cost_lpa !== b.year_one_cost_lpa) {
      return a.year_one_cost_lpa - b.year_one_cost_lpa;
    }
    return a.atomCount - b.atomCount;
  });

  return ranked;
}

interface Props {
  defaultWeights: OptionWeights;
  options: OptionCard[];
  mixes: MixOption[];
  onRerank: (options: RankedOption[], mixes: RankedMix[]) => void;
}

export function WeightSliders({
  defaultWeights,
  options,
  mixes,
  onRerank,
}: Props) {
  const initial = useMemo(
    () => ({ ...defaultWeights }) as Record<DimKey, number>,
    [defaultWeights],
  );
  const [weights, setWeights] = useState<Record<DimKey, number>>(initial);

  const handleChange = useCallback(
    (key: DimKey, value: number) => {
      const next = { ...weights, [key]: value };
      const norm = normalizeWeights(next);
      setWeights(norm);
      onRerank(rankOptions(options, norm), rankMixes(mixes, norm));
    },
    [weights, options, mixes, onRerank],
  );

  const handleReset = useCallback(() => {
    setWeights(initial);
    const norm = normalizeWeights(initial);
    onRerank(rankOptions(options, norm), rankMixes(mixes, norm));
  }, [initial, options, mixes, onRerank]);

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <p className="font-sans text-xs font-semibold text-ink">
          Adjust weights
        </p>
        <button
          type="button"
          onClick={handleReset}
          className="font-sans text-xs font-medium text-accent hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
        >
          Reset weights
        </button>
      </div>

      {DIMENSION_KEYS.map((key) => (
        <div key={key} className="flex items-center gap-3">
          <label
            htmlFor={`weight-${key}`}
            className="w-20 shrink-0 font-sans text-xs text-muted"
          >
            {LABELS[key]}
          </label>
          <Slider.Root
            id={`weight-${key}`}
            className="relative flex h-5 w-full items-center"
            value={[weights[key]]}
            min={0}
            max={1}
            step={0.01}
            onValueChange={([v]) => handleChange(key, v)}
          >
            <Slider.Track className="relative h-1 w-full rounded-full bg-hairline">
              <Slider.Range className="absolute h-full rounded-full bg-accent" />
            </Slider.Track>
            <Slider.Thumb className="block h-4 w-4 rounded-full border-2 border-accent bg-white shadow focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent" />
          </Slider.Root>
          <span className="w-10 text-right font-mono text-xs text-muted">
            {(weights[key] * 100).toFixed(0)}%
          </span>
        </div>
      ))}
    </div>
  );
}

export { reScore, normalizeWeights, rankOptions, rankMixes };
