"""Requisition Redline engine — pure functions, no I/O.

Underlines each hiring constraint, computes cost in supply/days/rupees,
assigns red/amber severity, and pre-computes all 2^5 = 32 Keep/Relax
scenarios.  score_options_fn is injected so the module can be tested
before M8 (options.py) is implemented.
"""
from __future__ import annotations

from datetime import date
from typing import Callable

import pandas as pd

from backend.engine.location import compare_locations
from backend.engine.market import matching_supply, ttf_adjusted

CONSTRAINT_ORDER: list[str] = ["location", "years", "skill", "budget", "deadline"]

# Lambdas that return a new context dict with one constraint relaxed.
_RELAX: dict[str, Callable[[dict], dict]] = {
    "location": lambda ctx: {**ctx, "location": "remote_india", "work_mode": "remote"},
    "years": lambda ctx: {**ctx, "min_years": max(0, ctx["min_years"] - 2)},
    "skill": lambda ctx: {
        **ctx,
        "must_skill_ids": [s for s in ctx["must_skill_ids"] if s != ctx["key_skill_id"]],
    },
    "budget": lambda ctx: {**ctx, "budget_lpa": ctx["market_p50"]},
    "deadline": lambda ctx: {**ctx, "deadline": ctx["buy_p80"]},
}


# ── Helpers ──────────────────────────────────────────────────────────────────


def _stat(market_stats_df: pd.DataFrame, location: str, level: str) -> dict:
    mask = (market_stats_df["location"] == location) & (market_stats_df["level"] == level)
    row = market_stats_df[mask]
    if row.empty:
        raise KeyError(f"No market stat for {location!r}/{level!r}")
    return row.iloc[0].to_dict()


def _extend_span_start(raw_text: str, from_pos: int, keyword: str) -> int:
    """Search backwards in raw_text for keyword; return its start position."""
    idx = raw_text.rfind(keyword, 0, from_pos)
    return idx if idx != -1 else from_pos


def _find_key_skill(
    must_ids: list[str],
    location: str,
    level: str,
    work_mode: str,
    cands: pd.DataFrame,
    candidate_skills: dict[str, set[str]],
) -> tuple[str, int]:
    """Return (skill_id, supply_without_that_skill) for the must-skill that
    removes the most external supply when treated as must-have."""
    supply_all, _ = matching_supply(location, level, work_mode, must_ids, cands, candidate_skills)
    best_id, best_without = must_ids[0], supply_all
    for sid in must_ids:
        remaining = [s for s in must_ids if s != sid]
        s, _ = matching_supply(location, level, work_mode, remaining, cands, candidate_skills)
        if s > best_without:
            best_id, best_without = sid, s
    return best_id, best_without


def _count_internal_build(
    employees_df: pd.DataFrame,
    emp_skills: dict[str, set[str]],
    must_ids: list[str],
    min_years_thresh: int,
) -> tuple[int, str | None, str | None, str | None]:
    """Count active, open-to-move employees with >= min_years_thresh experience
    and >= 80% must-skill coverage.  Returns (count, top_id, level, team)."""
    eligible = employees_df[
        (employees_df["years_exp"] >= min_years_thresh)
        & (employees_df["open_to_move"] == True)  # noqa: E712
        & (employees_df["is_active"] == True)  # noqa: E712
    ]
    count = 0
    top_id: str | None = None
    top_level: str | None = None
    top_team: str | None = None
    for _, row in eligible.iterrows():
        skills = emp_skills.get(str(row["employee_id"]), set())
        coverage = len(set(must_ids) & skills) / len(must_ids) if must_ids else 1.0
        if coverage >= 0.80:
            if top_id is None:
                top_id = str(row["employee_id"])
                top_level = str(row["level"])
                top_team = str(row["team"])
            count += 1
    return count, top_id, top_level, top_team


def _contractor_with_skill(
    skill_id: str,
    contractors_df: pd.DataFrame,
    ctr_skills: dict[str, set[str]],
    today: date,
) -> dict | None:
    """Find the active contractor with skill_id whose contract ends soonest."""
    matching = [cid for cid, skills in ctr_skills.items() if skill_id in skills]
    if not matching:
        return None
    end_dates = pd.to_datetime(contractors_df["end_date"])
    active = contractors_df[
        (contractors_df["contractor_id"].isin(matching))
        & (end_dates >= pd.Timestamp(today))
    ]
    if active.empty:
        return None
    row = active.sort_values("end_date").iloc[0]
    weeks = max(0, (pd.to_datetime(row["end_date"]) - pd.Timestamp(today)).days // 7)
    return {"contractor_id": str(row["contractor_id"]), "weeks_remaining": int(weeks)}


def _severity(
    supply_base: int,
    supply_relaxed: int,
    ttf_adj_base: float,
    ttf_adj_relaxed: float,
    pay_base: float,
    pay_relaxed: float,
    option_feas_change: str,
) -> str:
    """Classify constraint severity per CLAUDE.md erratum.

    RED  : supply doubles, OR P50 TTF cut >= 40%, OR infeasible→feasible.
    AMBER: any of supply/TTF/pay moves >= 15%, OR option feasibility improves.
    None : otherwise.

    Severity is measured on EXTERNAL supply, P50 days, rupees and option
    feasibility.  Internal candidate count changes go in hover text only.
    """
    if supply_base > 0 and supply_relaxed >= 2 * supply_base:
        return "red"
    if ttf_adj_base > 0 and (ttf_adj_base - ttf_adj_relaxed) / ttf_adj_base >= 0.40:
        return "red"
    if option_feas_change == "infeasible_to_feasible":
        return "red"
    if supply_base > 0 and (supply_relaxed - supply_base) / supply_base >= 0.15:
        return "amber"
    if ttf_adj_base > 0 and abs(ttf_adj_base - ttf_adj_relaxed) / ttf_adj_base >= 0.15:
        return "amber"
    if pay_base > 0 and abs(pay_base - pay_relaxed) / pay_base >= 0.15:
        return "amber"
    if option_feas_change == "feasibility_improved":
        return "amber"
    return "none"


def _decision_boundaries(scenarios: dict[str, dict]) -> list[str]:
    base_top = scenarios["00000"]["top_option_id"]
    boundaries: list[str] = []
    seen: set[str] = set()
    for i in range(1, 32):
        mask = format(i, "05b")
        top = scenarios[mask]["top_option_id"]
        if top != base_top and top not in seen:
            seen.add(top)
            relaxed = [CONSTRAINT_ORDER[j] for j, b in enumerate(mask) if b == "1"]
            boundaries.append(
                f"Relaxing {' + '.join(relaxed)} changes top option from {base_top} to {top}."
            )
    return boundaries[:5]


def _compute_scenarios(
    base_ctx: dict,
    candidates_df: pd.DataFrame,
    candidate_skills: dict[str, set[str]],
    market_stats_df: pd.DataFrame,
    score_options_fn: Callable[[dict, dict], dict],
) -> dict[str, dict]:
    """Pre-compute all 2^5 = 32 Keep/Relax scenarios."""
    level = base_ctx["level"]
    scenarios: dict[str, dict] = {}
    for i in range(32):
        mask = format(i, "05b")
        ctx = dict(base_ctx)
        for j, kind in enumerate(CONSTRAINT_ORDER):
            if mask[j] == "1":
                ctx = _RELAX[kind](ctx)
        cands = candidates_df[candidates_df["years_exp"] >= ctx["min_years"]].copy()
        supply, _ = matching_supply(
            ctx["location"], level, ctx["work_mode"],
            ctx["must_skill_ids"], cands, candidate_skills,
        )
        # Use per-scenario supply_ref for correct TTF scarcity factor.
        supply_ref_scen, _ = matching_supply(
            ctx["location"], level, ctx["work_mode"], [], cands, candidate_skills,
        )
        mstat = _stat(market_stats_df, ctx["location"], level)
        ttf_p50 = int(mstat["ttf_p50"])
        ttf_adj = ttf_adjusted(
            ttf_p50, supply, supply_ref_scen, ctx["budget_lpa"], float(mstat["sal_p50"])
        )
        market_ctx = {
            "supply": supply,
            "ttf_p50": ttf_p50,
            "ttf_p80": int(mstat["ttf_p80"]),
            "pay_p50": float(mstat["sal_p50"]),
            "ttf_adj": ttf_adj,
        }
        result = score_options_fn(ctx, market_ctx)
        scenarios[mask] = {
            "top_option_id": result["top_option_id"],
            "panel_text": result["panel_text"],
            "options": result.get("options", []),
        }
    return scenarios


# ── Public entry point ────────────────────────────────────────────────────────


def analyze_redline(
    parsed_req: dict,
    raw_text: str,
    candidates_df: pd.DataFrame,
    candidate_skills: dict[str, set[str]],
    employees_df: pd.DataFrame,
    emp_skills: dict[str, set[str]],
    contractors_df: pd.DataFrame,
    ctr_skills: dict[str, set[str]],
    skill_edges_df: pd.DataFrame,
    market_stats_df: pd.DataFrame,
    dejareq_result: dict,
    score_options_fn: Callable[[dict, dict], dict],
    today: date,
) -> dict:
    """Pure redline analysis.

    Returns:
        {
          constraints:       list[dict]  — 5 dicts with Constraint schema fields
                                          plus hover_data (raw numbers/IDs for tests);
                                          hover_text uses person IDs, not names.
          constraint_order:  list[str]
          scenarios:         dict[str, dict]  — 32 keys "00000"…"11111"
          assumption_ledger: dict
        }
    The API layer substitutes display names and drops hover_data before Pydantic
    validation (Constraint has extra='forbid').
    """

    # ── 1. Field values ──────────────────────────────────────────────────
    level = str(parsed_req["level"]["value"])
    location_val = str(parsed_req["location"]["value"])
    work_mode = str(parsed_req["work_mode"]["value"])
    min_years = int(parsed_req["min_years"]["value"])
    budget_lpa = float(parsed_req["budget_lpa"]["value"])
    deadline = int(parsed_req["need_by_days"]["value"])

    # Skills from the internal regex_parse dict include span fields.
    must_skills = [s for s in parsed_req["skills"] if s["importance"] == "must"]
    must_ids = [s["skill_id"] for s in must_skills]

    # ── 2. Base query ────────────────────────────────────────────────────
    cands_base = candidates_df[candidates_df["years_exp"] >= min_years].copy()
    supply_base, _ = matching_supply(
        location_val, level, work_mode, must_ids, cands_base, candidate_skills
    )
    supply_ref, _ = matching_supply(
        location_val, level, work_mode, [], cands_base, candidate_skills
    )
    mstat_base = _stat(market_stats_df, location_val, level)
    ttf_adj_base = ttf_adjusted(
        float(mstat_base["ttf_p50"]), supply_base, supply_ref,
        budget_lpa, float(mstat_base["sal_p50"])
    )

    # ── 3. Key must-skill ────────────────────────────────────────────────
    if must_ids:
        key_skill_id, supply_no_key = _find_key_skill(
            must_ids, location_val, level, work_mode, cands_base, candidate_skills
        )
        key_skill_obj = next(s for s in must_skills if s["skill_id"] == key_skill_id)
        key_skill_span_text = key_skill_obj.get("span", key_skill_id.title())
    else:
        key_skill_id, supply_no_key = "", supply_base
        key_skill_span_text = ""

    # ── 4. Span derivation ───────────────────────────────────────────────
    loc_field = parsed_req["location"]
    wm_field = parsed_req["work_mode"]
    years_field = parsed_req["min_years"]
    budget_field = parsed_req["budget_lpa"]
    deadline_field = parsed_req["need_by_days"]

    # Location: combine location + work_mode spans (handle inferred/None spans)
    _ls = loc_field.get("span_start") or 0
    _we = wm_field.get("span_end") or loc_field.get("span_end") or 0
    if _ls == 0 and _we == 0:
        loc_span_start, loc_span_end = 0, 0
        loc_phrase = str(loc_field.get("value") or "")
    else:
        loc_span_start = int(_ls)
        loc_span_end = int(_we)
        loc_phrase = raw_text[loc_span_start:loc_span_end]

    # Years: exact from min_years field
    _ys = years_field.get("span_start")
    _ye = years_field.get("span_end")
    if _ys is None or _ye is None:
        years_span_start, years_span_end = 0, 0
        years_phrase = str(years_field.get("value") or "")
    else:
        years_span_start = int(_ys)
        years_span_end = int(_ye)
        years_phrase = raw_text[years_span_start:years_span_end]

    # Skill: from first "must" keyword before first must-skill to end of last
    if must_skills:
        first_skill_start = min(
            s.get("span_start", len(raw_text)) for s in must_skills
        )
        last_skill_end = max(s.get("span_end", 0) for s in must_skills)
        skill_span_start = _extend_span_start(raw_text, first_skill_start, "must")
        skill_span_end = last_skill_end
        skill_phrase = raw_text[skill_span_start:skill_span_end]
    else:
        skill_span_start = skill_span_end = 0
        skill_phrase = ""

    # Budget: extend backward to include "budget" keyword
    _bs = budget_field.get("span_start")
    _be = budget_field.get("span_end")
    if _bs is None or _be is None:
        budget_span_start, budget_span_end = 0, 0
        budget_phrase = str(budget_field.get("value") or "")
    else:
        budget_span_start = _extend_span_start(raw_text, int(_bs), "budget")
        budget_span_end = int(_be)
        budget_phrase = raw_text[budget_span_start:budget_span_end]

    # Deadline: extend backward to include "need" phrase
    _ds = deadline_field.get("span_start")
    _de = deadline_field.get("span_end")
    if _ds is None or _de is None:
        deadline_span_start, deadline_span_end = 0, 0
        deadline_phrase = str(deadline_field.get("value") or "")
    else:
        deadline_span_start = _extend_span_start(raw_text, int(_ds), "need")
        deadline_span_end = int(_de)
        deadline_phrase = raw_text[deadline_span_start:deadline_span_end]

    # ── 5. Relaxed queries ───────────────────────────────────────────────

    # Location → remote_india
    supply_remote, _ = matching_supply(
        "remote_india", level, "remote", must_ids, cands_base, candidate_skills
    )
    mstat_remote = _stat(market_stats_df, "remote_india", level)
    supply_ref_remote, _ = matching_supply(
        "remote_india", level, "remote", [], cands_base, candidate_skills
    )
    ttf_adj_remote = ttf_adjusted(
        float(mstat_remote["ttf_p50"]), supply_remote, supply_ref_remote,
        budget_lpa, float(mstat_remote["sal_p50"])
    )

    # Compare all 4 locations for the Pune pay-delta hover number
    all_locs = ["remote_india", "hyderabad", "pune", location_val]
    loc_supplies: dict[str, int] = {}
    for loc in all_locs:
        wm = "remote" if loc == "remote_india" else work_mode
        s, _ = matching_supply(loc, level, wm, must_ids, cands_base, candidate_skills)
        loc_supplies[loc] = s
    ms_level = market_stats_df[market_stats_df["level"] == level].copy()
    loc_rows = compare_locations(all_locs, loc_supplies, ms_level)
    base_pay = float(mstat_base["sal_p50"])
    pune_row = next((r for r in loc_rows if r["location"] == "pune"), None)
    pune_pay = float(pune_row["pay_p50_lpa"]) if pune_row else base_pay
    pune_pct_below = round(100.0 * (base_pay - pune_pay) / base_pay) if base_pay > 0 else 0

    # Build candidates need upskilling on the key_skill; count coverage excluding it.
    must_ids_no_key = [s for s in must_ids if s != key_skill_id]

    # Years: internal Build count at 5+ and 3+
    build_5plus, top_emp_id, top_emp_level, top_emp_team = _count_internal_build(
        employees_df, emp_skills, must_ids_no_key, min_years
    )
    min_years_3 = max(0, min_years - 2)
    build_3plus, _, _, _ = _count_internal_build(
        employees_df, emp_skills, must_ids_no_key, min_years_3
    )
    extra_at_3plus = build_3plus - build_5plus

    # Years: external supply at 3+
    cands_3 = candidates_df[candidates_df["years_exp"] >= min_years_3].copy()
    supply_3plus, _ = matching_supply(
        location_val, level, work_mode, must_ids, cands_3, candidate_skills
    )

    # Budget: TTF without budget gap
    ttf_adj_budget_relaxed = ttf_adjusted(
        float(mstat_base["ttf_p50"]), supply_base, supply_ref,
        float(mstat_base["sal_p50"]), float(mstat_base["sal_p50"])
    )
    pct_below = round(
        100.0 * (float(mstat_base["sal_p50"]) - budget_lpa) / float(mstat_base["sal_p50"]), 1
    )
    # Budget hover shows the budget-penalty factor alone (not full scarcity×budget).
    budget_factor = 1.0 + 2.0 * max(
        0.0, (float(mstat_base["sal_p50"]) - budget_lpa) / float(mstat_base["sal_p50"])
    )
    ttf_mult = round(budget_factor, 2)

    # Deadline feasibility
    buy_p80 = int(mstat_base["ttf_p80"])
    deadline_feas = "infeasible_to_feasible" if deadline < buy_p80 else "none"

    # Years option feasibility (Build 1→4, improvement ≥15%)
    years_feas: str
    if build_5plus == 0 and build_3plus > 0:
        years_feas = "infeasible_to_feasible"
    elif build_5plus > 0 and build_3plus > build_5plus and (
        (build_3plus - build_5plus) / build_5plus >= 0.15
    ):
        years_feas = "feasibility_improved"
    else:
        years_feas = "none"

    # Contractor with key skill
    ctr_info = (
        _contractor_with_skill(key_skill_id, contractors_df, ctr_skills, today)
        if key_skill_id else None
    )
    pct_removed = (
        round(100.0 * (supply_no_key - supply_base) / supply_no_key)
        if supply_no_key > 0 else 0
    )

    # ── 6. Severity per constraint ───────────────────────────────────────
    sev_location = _severity(
        supply_base, supply_remote,
        ttf_adj_base, ttf_adj_remote,
        base_pay, float(mstat_remote["sal_p50"]),
        "none",
    )

    sev_years = _severity(
        supply_base, supply_3plus,
        0.0, 0.0,   # TTF not meaningful for years (same location, same budget)
        0.0, 0.0,   # pay unchanged
        years_feas,
    )

    ttf_adj_skill_relaxed = ttf_adjusted(
        float(mstat_base["ttf_p50"]), supply_no_key, supply_ref,
        budget_lpa, float(mstat_base["sal_p50"])
    )
    sev_skill = _severity(
        supply_base, supply_no_key,
        ttf_adj_base, ttf_adj_skill_relaxed,
        0.0, 0.0,
        "none",
    )

    sev_budget = _severity(
        supply_base, supply_base,    # supply unchanged when budget relaxed
        ttf_adj_base, ttf_adj_budget_relaxed,
        0.0, 0.0,
        "none",
    )

    sev_deadline = _severity(
        supply_base, supply_base,
        0.0, 0.0,
        0.0, 0.0,
        deadline_feas,
    )

    # ── 7. Hover data & text (IDs, not names) ────────────────────────────
    location_label = location_val.replace("_", "-").title()
    level_label = level.title()

    hover_data_location = {
        "supply_base": supply_base,
        "ttf_p50_base": int(mstat_base["ttf_p50"]),
        "remote_supply": supply_remote,
        "remote_p50": int(mstat_remote["ttf_p50"]),
        "pune_pct_below": pune_pct_below,
    }
    hover_text_location = (
        f"Only {supply_base} matching candidates, P50 {int(mstat_base['ttf_p50'])} days to fill. "
        f"Remote-India: {supply_remote} candidates, P50 {int(mstat_remote['ttf_p50'])} days. "
        f"Pune's P50 pay is {pune_pct_below}% lower."
    )

    _emp_desc = (
        f"{top_emp_id}, {top_emp_level}, {top_emp_team}"
        if top_emp_id else "none"
    )
    hover_data_years = {
        "build_count_5plus": build_5plus,
        "top_emp_id": top_emp_id,
        "top_emp_level": top_emp_level,
        "top_emp_team": top_emp_team,
        "extra_at_3plus": extra_at_3plus,
        "build_count_3plus": build_3plus,
    }
    hover_text_years = (
        f"Only {build_5plus} internal employee qualifies today ({_emp_desc}). "
        f"{extra_at_3plus} more with 3.5–4 years have an 80%+ skill match; "
        f"changing to 3+ widens Build from {build_5plus} to {build_3plus} candidates."
    )

    hover_data_skill = {
        "supply_no_key": supply_no_key,
        "supply_base": supply_base,
        "pct_removed": pct_removed,
        "contractor_id": ctr_info["contractor_id"] if ctr_info else None,
        "weeks_remaining": ctr_info["weeks_remaining"] if ctr_info else None,
    }
    if ctr_info:
        hover_text_skill = (
            f"This one skill removes {pct_removed}% of supply "
            f"({supply_no_key} → {supply_base}). "
            f"Contractor {ctr_info['contractor_id']} already has it; "
            f"his contract ends in {ctr_info['weeks_remaining']} weeks: conversion candidate."
        )
    else:
        hover_text_skill = (
            f"This one skill removes {pct_removed}% of supply "
            f"({supply_no_key} → {supply_base})."
        )

    hover_data_budget = {
        "pct_below": pct_below,
        "market_p50": float(mstat_base["sal_p50"]),
        "ttf_mult": ttf_mult,
        "location_label": location_label,
        "level_label": level_label,
    }
    hover_text_budget = (
        f"{pct_below}% below the {location_label} {level_label} P50 of "
        f"₹{mstat_base['sal_p50']:.0f}L. "
        f"Expect about {ttf_mult}× longer time to fill and lower offer acceptance."
    )

    hover_data_deadline = {
        "deadline": deadline,
        "buy_p80": buy_p80,
        "remote_p80": int(mstat_remote["ttf_p80"]),
        "location_label": location_label,
    }
    hover_text_deadline = (
        f"Not achievable via Buy ({location_label} P80 is {buy_p80} days; "
        f"even Remote-India P80 is {int(mstat_remote['ttf_p80'])} days). "
        f"Only Borrow meets this."
    )

    # ── 8. Constraint list ───────────────────────────────────────────────
    wm_display = wm_field.get("span", work_mode)  # preserves "on-site" hyphen from raw text
    constraints: list[dict] = [
        {
            "id": "c-location",
            "kind": "location",
            "value": f"{location_val}, {wm_display}".lower(),
            "phrase": loc_phrase,
            "span_start": loc_span_start,
            "span_end": loc_span_end,
            "source": "stated",
            "severity": sev_location,
            "hover_data": hover_data_location,
            "hover_text": hover_text_location,
            "cost": {
                "supply_delta": supply_remote - supply_base,
                "days_delta": float(int(mstat_remote["ttf_p50"]) - int(mstat_base["ttf_p50"])),
                "rupees_delta_lpa": float(mstat_remote["sal_p50"]) - base_pay,
            },
            "relaxed_value": "remote_india",
        },
        {
            "id": "c-years",
            "kind": "years",
            "value": years_field["span"],
            "phrase": years_phrase,
            "span_start": years_span_start,
            "span_end": years_span_end,
            "source": "stated",
            "severity": sev_years,
            "hover_data": hover_data_years,
            "hover_text": hover_text_years,
            "cost": {"supply_delta": None, "days_delta": None, "rupees_delta_lpa": None},
            "relaxed_value": f"{min_years_3}+ years",
        },
        {
            "id": f"c-skill-{key_skill_id}",
            "kind": "skill",
            "value": f"must know {key_skill_span_text}",
            "phrase": skill_phrase,
            "span_start": skill_span_start,
            "span_end": skill_span_end,
            "source": "stated",
            "severity": sev_skill,
            "hover_data": hover_data_skill,
            "hover_text": hover_text_skill,
            "cost": {
                "supply_delta": supply_no_key - supply_base,
                "days_delta": None,
                "rupees_delta_lpa": None,
            },
            "relaxed_value": "nice-to-have",
        },
        {
            "id": "c-budget",
            "kind": "budget",
            "value": budget_field["span"],
            "phrase": budget_phrase,
            "span_start": budget_span_start,
            "span_end": budget_span_end,
            "source": "stated",
            "severity": sev_budget,
            "hover_data": hover_data_budget,
            "hover_text": hover_text_budget,
            "cost": {
                "supply_delta": None,
                "days_delta": None,
                "rupees_delta_lpa": float(mstat_base["sal_p50"]) - budget_lpa,
            },
            "relaxed_value": f"₹{mstat_base['sal_p50']:.0f}L (market P50)",
        },
        {
            "id": "c-deadline",
            "kind": "deadline",
            "value": deadline_field["span"],
            "phrase": deadline_phrase,
            "span_start": deadline_span_start,
            "span_end": deadline_span_end,
            "source": "stated",
            "severity": sev_deadline,
            "hover_data": hover_data_deadline,
            "hover_text": hover_text_deadline,
            "cost": {
                "supply_delta": None,
                "days_delta": float(buy_p80 - deadline),
                "rupees_delta_lpa": None,
            },
            "relaxed_value": f"{buy_p80} days (Buy P80)",
        },
    ]

    # ── 9. 32 scenarios ──────────────────────────────────────────────────
    base_ctx: dict = {
        "location": location_val,
        "level": level,
        "work_mode": work_mode,
        "min_years": min_years,
        "must_skill_ids": list(must_ids),
        "budget_lpa": budget_lpa,
        "deadline": deadline,
        "market_p50": float(mstat_base["sal_p50"]),
        "buy_p80": buy_p80,
        "supply_ref": supply_ref,
        "key_skill_id": key_skill_id,
    }
    scenarios = _compute_scenarios(
        base_ctx, candidates_df, candidate_skills, market_stats_df, score_options_fn
    )

    # ── 10. Assumption ledger ────────────────────────────────────────────
    assumption_ledger = {
        "entries": [
            {"kind": c["kind"], "cost": c["cost"], "risk_delta": 0.0}
            for c in constraints
        ],
        "dejareq_risk": (
            dejareq_result.get("risk_adjustments", []) if dejareq_result else []
        ),
        "decision_boundaries": _decision_boundaries(scenarios),
    }

    return {
        "constraints": constraints,
        "constraint_order": CONSTRAINT_ORDER,
        "scenarios": scenarios,
        "assumption_ledger": assumption_ledger,
    }
