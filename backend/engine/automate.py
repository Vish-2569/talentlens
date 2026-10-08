"""Automation estimation — pure functions, no I/O.

hours_saved = Σ(time_share × potential × adoption)
"""
from __future__ import annotations


def estimate_automation(
    tasks: list[dict],
    headcount: int = 1,
    adoption: float = 0.42,
    uncertainty: float = 0.30,
) -> dict:
    total = 0.0
    breakdown: list[dict] = []
    evidence_ids: list[str] = []

    for t in tasks:
        ts = float(t.get("time_share", 0))
        pot = float(t.get("potential", 0))
        saved = ts * pot * adoption
        total += saved

        breakdown.append({
            "task_id": t.get("task_id", ""),
            "task": t.get("task", ""),
            "time_share": ts,
            "potential": pot,
            "hours_saved_pct": round(saved * 100, 2),
        })
        evidence_ids.append(str(t.get("task_id", "")))

    pct = round(total * 100, 2)
    range_low = round(pct * (1.0 - uncertainty), 2)
    range_high = round(pct * (1.0 + uncertainty), 2)

    return {
        "hours_saved_pct": pct,
        "range_low": range_low,
        "range_high": range_high,
        "replacement": headcount > 1,
        "task_breakdown": breakdown,
        "evidence_ids": evidence_ids,
    }
