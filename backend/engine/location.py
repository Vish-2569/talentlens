"""Location comparison — pure functions, no I/O.

score = w_supply·supply_mm + w_speed·speed_mm + w_cost·cost_mm + w_remote·remote_mm − penalty

All four dimensions min–max normalised: (x − min)/(max − min) across the candidate set.
cost raw = 1 / (P50_pay × col_index).
penalty = (reloc_package_lpa / max_reloc_in_set) × PENALTY_WEIGHT (see DECISIONS.md §M6).
"""
from __future__ import annotations

import pandas as pd

DEFAULT_WEIGHTS = {
    "supply": 0.35,
    "speed": 0.30,
    "cost": 0.25,
    "remote": 0.10,
}

# Fraction of score range a max-package relocation costs (see DECISIONS.md).
PENALTY_WEIGHT = 0.05


def _minmax(values: list[float]) -> list[float]:
    mn, mx = min(values), max(values)
    rng = mx - mn
    if rng == 0.0:
        return [0.0] * len(values)
    return [(v - mn) / rng for v in values]


def compare_locations(
    locations: list[str],
    supplies: dict[str, int],
    market_stats_df: pd.DataFrame,
    weights: dict[str, float] | None = None,
) -> list[dict]:
    w = weights or DEFAULT_WEIGHTS

    rows: list[dict] = []
    for loc in locations:
        stat = market_stats_df[market_stats_df["location"] == loc]
        if stat.empty:
            continue
        stat = stat.iloc[0]

        supply = supplies.get(loc, 0)
        speed = 1.0 / stat["ttf_p50"] if stat["ttf_p50"] > 0 else 0.0
        cost = (1.0 / (stat["sal_p50"] * stat["col_index"])
                if stat["sal_p50"] > 0 and stat["col_index"] > 0 else 0.0)
        remote = float(stat["remote_share"])
        reloc = float(stat["reloc_package_lpa"]) if "reloc_package_lpa" in stat.index else 0.0

        rows.append({
            "location": loc,
            "supply": supply,
            "ttf_p50": int(stat["ttf_p50"]),
            "ttf_p80": int(stat["ttf_p80"]),
            "pay_p50_lpa": float(stat["sal_p50"]),
            "_supply_raw": float(supply),
            "_speed_raw": speed,
            "_cost_raw": cost,
            "_remote_raw": remote,
            "_reloc_raw": reloc,
        })

    if not rows:
        return []

    supply_mm = _minmax([r["_supply_raw"] for r in rows])
    speed_mm  = _minmax([r["_speed_raw"]  for r in rows])
    cost_mm   = _minmax([r["_cost_raw"]   for r in rows])
    remote_mm = _minmax([r["_remote_raw"] for r in rows])

    reloc_vals = [r["_reloc_raw"] for r in rows]
    max_reloc = max(reloc_vals) if max(reloc_vals) > 0 else 1.0

    for i, r in enumerate(rows):
        raw = (w["supply"] * supply_mm[i]
               + w["speed"]  * speed_mm[i]
               + w["cost"]   * cost_mm[i]
               + w["remote"] * remote_mm[i])
        penalty = (reloc_vals[i] / max_reloc) * PENALTY_WEIGHT
        r["score"] = round(max(0.0, raw - penalty), 2)

        for k in ("_supply_raw", "_speed_raw", "_cost_raw", "_remote_raw", "_reloc_raw"):
            del r[k]

    rows.sort(key=lambda r: r["score"], reverse=True)
    return rows
