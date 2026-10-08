"""Location comparison — pure functions, no I/O.

score = w_supply·supply_norm + w_speed·speed_norm + w_cost·cost_norm + w_remote·remote_norm
Each dimension ratio-to-max normalized.
"""
from __future__ import annotations

import pandas as pd

DEFAULT_WEIGHTS = {
    "supply": 0.34,
    "speed": 0.21,
    "cost": 0.30,
    "remote": 0.15,
}


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
        cost = 1.0 / (stat["sal_p50"] * stat["col_index"]) if stat["sal_p50"] > 0 and stat["col_index"] > 0 else 0.0
        remote = float(stat["remote_share"])

        rows.append({
            "location": loc,
            "supply": supply,
            "ttf_p50": int(stat["ttf_p50"]),
            "ttf_p80": int(stat["ttf_p80"]),
            "pay_p50_lpa": float(stat["sal_p50"]),
            "_supply_raw": supply,
            "_speed_raw": speed,
            "_cost_raw": cost,
            "_remote_raw": remote,
        })

    if not rows:
        return []

    max_supply = max(r["_supply_raw"] for r in rows) or 1
    max_speed = max(r["_speed_raw"] for r in rows) or 1
    max_cost = max(r["_cost_raw"] for r in rows) or 1
    max_remote = max(r["_remote_raw"] for r in rows) or 1

    for r in rows:
        supply_n = r["_supply_raw"] / max_supply
        speed_n = r["_speed_raw"] / max_speed
        cost_n = r["_cost_raw"] / max_cost
        remote_n = r["_remote_raw"] / max_remote

        raw = (w["supply"] * supply_n
               + w["speed"] * speed_n
               + w["cost"] * cost_n
               + w["remote"] * remote_n)
        r["score"] = round(raw, 2)

        del r["_supply_raw"]
        del r["_speed_raw"]
        del r["_cost_raw"]
        del r["_remote_raw"]

    rows.sort(key=lambda r: r["score"], reverse=True)
    return rows
