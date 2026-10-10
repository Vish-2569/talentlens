"""Sourcing channels engine (M9) — pure functions, no I/O.

Ranks sourcing channels by fill rate then median days to hire.
Past finalists filtered by stage, outcome, recency, and consent.
Staffing suppliers ranked by fill rate then days to first submission.

AI reads language; Python does arithmetic; a human decides.
"""
from __future__ import annotations

from datetime import date, timedelta

import pandas as pd


def _applicable(channel_row: pd.Series, level: str) -> bool:
    raw = str(channel_row.get("applicable_levels", "all"))
    if raw.strip().lower() == "all":
        return True
    levels = {s.strip().lower() for s in raw.split(",")}
    return level.lower() in levels


def analyze_sourcing(
    *,
    sourcing_df: pd.DataFrame,
    past_finalists_df: pd.DataFrame,
    suppliers_df: pd.DataFrame,
    level: str,
    today: date = date(2026, 10, 8),
) -> dict:
    cutoff = today - timedelta(days=365)

    # ── Past finalists ──────────────────────────────────────────────────
    pf = past_finalists_df[
        (past_finalists_df["stage_reached"] == "final")
        & (past_finalists_df["outcome"].isin(["declined", "closed"]))
        & (pd.to_datetime(past_finalists_df["decided_on"]).dt.date >= cutoff)
        & (past_finalists_df["opted_in_pool"] == True)  # noqa: E712
    ].copy()

    finalist_count = len(pf)
    remote_ready = int(pf["open_to_remote"].sum()) if not pf.empty else 0
    finalist_ids = pf["candidate_id"].tolist()

    # ── Channel ranking ─────────────────────────────────────────────────
    applicable = sourcing_df[
        sourcing_df.apply(lambda r: _applicable(r, level), axis=1)
    ].copy()

    channels: list[dict] = []

    # Past finalists channel (no fill_rate/median_days in CSV — ranked first
    # when finalists exist, per Section 7B).
    pf_row = applicable[applicable["channel"] == "past_finalists"]
    if not pf_row.empty and finalist_count > 0:
        channels.append({
            "rank": 1,
            "channel": "Past finalists (ATS rediscovery)",
            "evidence": (
                f"{finalist_count} candidates reached the final round for this "
                f"role in the last 12 months and were not hired "
                f"(offer declined or headcount closed); "
                f"{remote_ready} open to remote; all opted in to the talent pool"
            ),
            "use_for": "Buy / Relocate",
            "fill_rate": None,
            "median_days": None,
        })

    # Other channels: ranked by fill_rate desc, then median_days asc,
    # with Buy-oriented channels (referral, job_board) before Borrow-oriented
    # (supplier) at equal priority tiers.
    others = applicable[
        (applicable["channel"] != "past_finalists")
    ].copy()
    if level != "junior":
        others = others[others["channel"] != "campus"]

    _USE_TIER = {"referral": 0, "supplier": 1, "job_board": 2, "campus": 3}
    others = others.copy()
    others["_tier"] = others["channel"].map(_USE_TIER).fillna(2).astype(int)
    sorted_others = others.sort_values(
        ["_tier", "fill_rate", "median_days"],
        ascending=[True, False, True],
        na_position="last",
    )

    use_for_map = {
        "referral": "Buy / Relocate",
        "supplier": "Borrow",
        "job_board": "Buy",
        "campus": "Buy",
    }

    channel_label_map = {
        "referral": "Employee referral",
        "supplier": "Staffing supplier A (via MSP)",
        "job_board": "Job board",
        "campus": "Campus",
    }

    base_rank = 2 if finalist_count > 0 else 1
    for i, (_, row) in enumerate(sorted_others.iterrows()):
        ch = str(row["channel"])
        fr = float(row["fill_rate"]) if pd.notna(row["fill_rate"]) else None
        md = int(row["median_days"]) if pd.notna(row["median_days"]) else None

        if ch == "supplier":
            evidence = (
                f"Fill rate {int(fr * 100)}%, median {md} days to first submission, "
                f"bill rate within budget"
            ) if fr is not None and md is not None else ""
        else:
            evidence = (
                f"Fill rate {int(fr * 100)}%, median {md} days to hire"
            ) if fr is not None and md is not None else ""

        channels.append({
            "rank": base_rank + i,
            "channel": channel_label_map.get(ch, ch),
            "evidence": evidence,
            "use_for": use_for_map.get(ch, ""),
            "fill_rate": fr,
            "median_days": md,
        })

    # Campus: mark not applicable if level != junior
    if level != "junior":
        campus_row = sourcing_df[sourcing_df["channel"] == "campus"]
        if not campus_row.empty:
            channels.append({
                "rank": None,
                "channel": "Campus",
                "evidence": f"Not applicable for {level.title()} level",
                "use_for": "--",
                "fill_rate": None,
                "median_days": None,
            })

    # ── Suppliers ───────────────────────────────────────────────────────
    sup_sorted = suppliers_df.sort_values(
        ["fill_rate", "median_days_to_submit"],
        ascending=[False, True],
    )
    suppliers_out: list[dict] = []
    for _, row in sup_sorted.iterrows():
        suppliers_out.append({
            "supplier_id": str(row["supplier_id"]),
            "name": str(row["name"]),
            "fill_rate": float(row["fill_rate"]),
            "median_days_to_submit": int(row["median_days_to_submit"]),
            "avg_bill_rate_lpa": float(row["avg_bill_rate_lpa"]),
        })

    return {
        "channels": channels,
        "past_finalists": {
            "count": finalist_count,
            "remote_ready": remote_ready,
            "ids": finalist_ids,
        },
        "suppliers": suppliers_out,
    }
