"""Market analysis — pure functions, no I/O.

Matching supply counting, TTF adjustment, and market card construction.
"""
from __future__ import annotations

import pandas as pd


def matching_supply(
    location: str,
    level: str,
    work_mode: str,
    required_skill_ids: list[str],
    candidates_df: pd.DataFrame,
    candidate_skills_dict: dict[str, set[str]],
) -> tuple[int, list[str]]:
    mask = (
        (candidates_df["location"] == location)
        & (candidates_df["level"] == level)
        & (candidates_df["work_mode"] == work_mode)
    )
    filtered = candidates_df[mask]

    req_set = set(required_skill_ids)
    matched_ids: list[str] = []
    for cid in filtered["candidate_id"]:
        cid_str = str(cid)
        cand_skills = candidate_skills_dict.get(cid_str, set())
        if req_set.issubset(cand_skills):
            matched_ids.append(cid_str)

    return len(matched_ids), matched_ids


def ttf_adjusted(
    ttf_base: float,
    supply: int,
    supply_ref: int,
    budget_lpa: float,
    sal_p50: float,
) -> float:
    if supply <= 0:
        scarcity = 2.5
    else:
        scarcity = (supply_ref / supply) ** 0.3
    scarcity = max(0.6, min(scarcity, 2.5))

    budget_gap = max(0.0, (sal_p50 - budget_lpa) / sal_p50)
    budget_mult = 1.0 + 2.0 * budget_gap

    return ttf_base * scarcity * budget_mult


def market_card(
    location: str,
    level: str,
    supply: int,
    market_stat_row: dict,
) -> dict:
    return {
        "location": location,
        "level": level,
        "supply": supply,
        "demand": market_stat_row["demand"],
        "sal_p25": market_stat_row["sal_p25"],
        "sal_p50": market_stat_row["sal_p50"],
        "sal_p75": market_stat_row["sal_p75"],
        "ttf_p50": market_stat_row["ttf_p50"],
        "ttf_p80": market_stat_row["ttf_p80"],
    }
