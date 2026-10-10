"""Ripple effect engine — pure functions, no I/O.

Traces the downstream backfill chain when an internal candidate fills the
target role. Returns the top-2 movers side by side with net impact scores.

Architecture: AI reads language; Python does arithmetic; a human decides.
"""
from __future__ import annotations

from datetime import date

import pandas as pd

from backend.engine.build import build_plan, build_chain_cost
from backend.engine.evidence import resolve_person
from backend.engine.match import score_employee
from backend.engine.market import matching_supply

_LEVEL_NUM = {"junior": 1, "mid": 2, "senior": 3, "lead": 4}
_LEVEL_NAMES = {1: "junior", 2: "mid", 3: "senior", 4: "lead"}

# Canonical required skills per level (Full Stack Developer, closed vocabulary).
SKILLS_BY_LEVEL: dict[str, list[dict]] = {
    "junior": [
        {"id": "react", "importance": "must"},
        {"id": "nodejs", "importance": "must"},
        {"id": "javascript", "importance": "nice"},
        {"id": "html_css", "importance": "nice"},
        {"id": "git", "importance": "nice"},
        {"id": "jest", "importance": "nice"},
    ],
    "mid": [
        {"id": "react", "importance": "must"},
        {"id": "nodejs", "importance": "must"},
        {"id": "typescript", "importance": "nice"},
        {"id": "javascript", "importance": "nice"},
        {"id": "html_css", "importance": "nice"},
        {"id": "git", "importance": "nice"},
        {"id": "jest", "importance": "nice"},
    ],
    "senior": [
        {"id": "react", "importance": "must"},
        {"id": "nodejs", "importance": "must"},
        {"id": "kubernetes", "importance": "must"},
        {"id": "typescript", "importance": "nice"},
        {"id": "docker", "importance": "nice"},
        {"id": "javascript", "importance": "nice"},
        {"id": "rest_apis", "importance": "nice"},
        {"id": "postgresql", "importance": "nice"},
    ],
    "lead": [
        {"id": "react", "importance": "must"},
        {"id": "nodejs", "importance": "must"},
        {"id": "kubernetes", "importance": "must"},
        {"id": "terraform", "importance": "must"},
        {"id": "system_design", "importance": "must"},
        {"id": "typescript", "importance": "nice"},
        {"id": "docker", "importance": "nice"},
        {"id": "microservices", "importance": "nice"},
    ],
}

# Stopping-rule thresholds.
_GREEN_P50 = 30
_GREEN_SUPPLY = 50
_RED_P50 = 60
_BACKFILL_MIN = 70   # >= 70 qualifies; stop RED when no backfill scores >= 70
_MAX_DEPTH = 3


# ── Helpers ───────────────────────────────────────────────────────────────────


def _stat(
    market_stats_df: pd.DataFrame, location: str, level: str
) -> dict | None:
    row = market_stats_df[
        (market_stats_df["location"] == location) & (market_stats_df["level"] == level)
    ]
    return row.iloc[0].to_dict() if not row.empty else None


def _promotion_raise_lpa(
    level: str, location: str, market_stats_df: pd.DataFrame
) -> float:
    """Annual raise estimate on promotion = (P75 − P50) / 2 at the current level."""
    s = _stat(market_stats_df, location, level)
    if s is None:
        return 0.0
    return (float(s["sal_p75"]) - float(s["sal_p50"])) / 2.0


def _bus_factor_check(
    person_id: str,
    person_skills: set[str],
    project_assignments: dict[str, set[str]],
    projects_df: pd.DataFrame,
    all_emp_skills: dict[str, set[str]],
) -> list[str]:
    """Return skill IDs where the person is the sole holder on any critical project."""
    critical_ids = set(projects_df[projects_df["is_critical"] == True]["project_id"])
    mover_projs = project_assignments.get(person_id, set()) & critical_ids
    if not mover_projs:
        return []

    flags: list[str] = []
    for proj_id in mover_projs:
        proj_row = projects_df[projects_df["project_id"] == proj_id]
        if proj_row.empty:
            continue
        req_str = str(proj_row.iloc[0].get("required_skills", ""))
        proj_required = {s.strip() for s in req_str.split(",") if s.strip()}

        others_on_proj = {
            eid
            for eid, projs in project_assignments.items()
            if proj_id in projs and eid != person_id
        }

        for skill in person_skills & proj_required:
            other_holders = sum(
                1 for eid in others_on_proj if skill in all_emp_skills.get(eid, set())
            )
            if other_holders == 0:
                flags.append(skill)

    return sorted(set(flags))


def _score_movers(
    employees_df: pd.DataFrame,
    emp_skills: dict[str, set[str]],
    evidence_df: pd.DataFrame,
    required_skills: list[dict],
    required_level: str,
    skill_edges_df: pd.DataFrame,
    today: date,
    one_below_only: bool = False,
) -> list[dict]:
    """Score active open_to_move employees against required_skills.

    If one_below_only=True, restrict to employees exactly one level below
    required_level (backfill search mode).
    """
    mask = (employees_df["open_to_move"] == True) & (employees_df["is_active"] == True)  # noqa: E712
    active = employees_df[mask]

    if one_below_only:
        target_num = _LEVEL_NUM.get(required_level, 0)
        one_below = _LEVEL_NAMES.get(target_num - 1)
        if one_below is None:
            return []
        active = active[active["level"] == one_below]

    results: list[dict] = []
    for _, row in active.iterrows():
        pid = str(row["employee_id"])
        ev = resolve_person(pid, evidence_df, today=today)
        sk = emp_skills.get(pid, set())
        r = score_employee(
            pid, required_skills, ev, sk, skill_edges_df,
            str(row["level"]), required_level, today=today,
        )
        results.append({
            **r,
            "level": str(row["level"]),
            "team": str(row["team"]),
            "location": str(row["location"]),
            "work_mode": str(row["work_mode"]),
        })

    results.sort(key=lambda x: -x["match"])
    return results


def _external_node(level: str, team: str, location: str, work_mode: str,
                   market_stats_df: pd.DataFrame,
                   candidates_df: pd.DataFrame,
                   candidate_skills: dict[str, set[str]]) -> dict:
    """Build a terminal external-hire node using market stats."""
    s = _stat(market_stats_df, location, level)
    p50 = int(s["ttf_p50"]) if s else 99
    supply, _ = matching_supply(location, level, work_mode, [], candidates_df, candidate_skills)
    status = "green" if (p50 <= _GREEN_P50 and supply >= _GREEN_SUPPLY) else "red"
    reason = (
        f"External hire: P50 {p50} days, {supply} candidates"
        if status == "green"
        else f"Hard market: external P50 {p50} days, {supply} candidates"
    )
    return {
        "person_id": None,
        "seat": f"{level}/{team}",
        "status": status,
        "reason": reason,
        "evidence_ids": [],
        "bus_factor_flags": [],
        "external_days": p50,
    }


def _trace_chain(
    level: str,
    team: str,
    location: str,
    work_mode: str,
    employees_df: pd.DataFrame,
    emp_skills: dict[str, set[str]],
    evidence_df: pd.DataFrame,
    skill_edges_df: pd.DataFrame,
    market_stats_df: pd.DataFrame,
    project_assignments: dict[str, set[str]],
    projects_df: pd.DataFrame,
    candidates_df: pd.DataFrame,
    candidate_skills: dict[str, set[str]],
    today: date,
    depth: int = 0,
) -> list[dict]:
    """Recursively resolve the backfill chain for a gap at (level, team).

    Returns a list of chain nodes (not including the mover node itself).
    """
    if depth >= _MAX_DEPTH:
        return [_external_node(level, team, location, work_mode,
                               market_stats_df, candidates_df, candidate_skills)]

    level_num = _LEVEL_NUM.get(level, 1)
    # No level below junior → always external.
    if level_num <= 1:
        return [_external_node(level, team, location, work_mode,
                               market_stats_df, candidates_df, candidate_skills)]

    # Search for internal backfill one level below.
    skills_needed = SKILLS_BY_LEVEL.get(level, SKILLS_BY_LEVEL["senior"])
    scored = _score_movers(
        employees_df, emp_skills, evidence_df,
        skills_needed, level, skill_edges_df, today,
        one_below_only=True,
    )
    best = next((c for c in scored if c["match"] >= _BACKFILL_MIN), None)

    if best is None:
        # Stopping rule: check if market is easy (GREEN) or hard (RED).
        s = _stat(market_stats_df, location, level)
        p50 = int(s["ttf_p50"]) if s else 99
        supply, _ = matching_supply(location, level, work_mode, [], candidates_df, candidate_skills)
        if p50 <= _GREEN_P50 and supply >= _GREEN_SUPPLY:
            status = "green"
            reason = f"External hire: P50 {p50} days, {supply} candidates"
        elif p50 > _RED_P50:
            status = "red"
            reason = f"No internal backfill; external P50 {p50} days"
        else:
            status = "amber"
            reason = f"Moderate market: P50 {p50} days, {supply} candidates"
        return [{
            "person_id": None,
            "seat": f"{level}/{team}",
            "status": status,
            "reason": reason,
            "evidence_ids": [],
            "bus_factor_flags": [],
            "external_days": p50,
        }]

    # Found a viable backfill — build their node and recurse into their old seat.
    bf_pid = best["person_id"]
    bf_flags = _bus_factor_check(
        bf_pid, emp_skills.get(bf_pid, set()),
        project_assignments, projects_df, emp_skills,
    )

    bf_ev = resolve_person(bf_pid, evidence_df, today=today)
    bf_bp = build_plan(
        bf_pid, bf_ev, emp_skills.get(bf_pid, set()),
        skills_needed, skill_edges_df,
        best["level"], level,
    )

    node: dict = {
        "person_id": bf_pid,
        "seat": f"{level}/{team}",
        "status": "green",
        "reason": (
            f"Internal backfill {bf_pid} (match {best['match']}%)"
            + (f"; ready in week {bf_bp['readiness_weeks']}"
               if bf_bp["readiness_weeks"] > 0 else "; ready now")
        ),
        "evidence_ids": best["evidence_ids"],
        "bus_factor_flags": bf_flags,
        "external_days": None,
        "readiness_weeks": bf_bp["readiness_weeks"],
    }

    sub = _trace_chain(
        best["level"], best["team"], best["location"], best["work_mode"],
        employees_df, emp_skills, evidence_df, skill_edges_df, market_stats_df,
        project_assignments, projects_df, candidates_df, candidate_skills, today,
        depth=depth + 1,
    )
    return [node] + sub


# ── Public API ────────────────────────────────────────────────────────────────


def borrow_coverage_check(
    contractor_id: str,
    project_assignments: dict[str, set[str]],
    projects_df: pd.DataFrame,
    all_emp_skills: dict[str, set[str]],
    ctr_skills: dict[str, set[str]],
) -> dict:
    """Check whether a contractor leaving causes any critical project to lose coverage.

    Returns {"loses_coverage": False} when the contractor is not on any critical
    project, or when other holders exist for every at-risk skill.
    """
    ctr_skill_set = ctr_skills.get(contractor_id, set())
    critical_ids = set(projects_df[projects_df["is_critical"] == True]["project_id"])
    ctr_projs = project_assignments.get(contractor_id, set()) & critical_ids

    if not ctr_projs:
        return {"loses_coverage": False, "reason": "contractor not on any critical project"}

    lost: list[str] = []
    for proj_id in ctr_projs:
        proj_row = projects_df[projects_df["project_id"] == proj_id]
        if proj_row.empty:
            continue
        req_str = str(proj_row.iloc[0].get("required_skills", ""))
        proj_required = {s.strip() for s in req_str.split(",") if s.strip()}
        others = {
            eid
            for eid, projs in project_assignments.items()
            if proj_id in projs and eid != contractor_id
        }
        for skill in ctr_skill_set & proj_required:
            if not any(skill in all_emp_skills.get(eid, set()) for eid in others):
                lost.append(skill)

    if lost:
        return {"loses_coverage": True, "skills_at_risk": sorted(set(lost))}
    return {"loses_coverage": False, "reason": "other holders exist for all skills"}


def analyze_ripple(
    required_skills: list[dict],
    required_level: str,
    required_team: str,
    required_location: str,
    required_work_mode: str,
    employees_df: pd.DataFrame,
    emp_skills: dict[str, set[str]],
    evidence_df: pd.DataFrame,
    skill_edges_df: pd.DataFrame,
    market_stats_df: pd.DataFrame,
    projects_df: pd.DataFrame,
    project_assignments: dict[str, set[str]],
    candidates_df: pd.DataFrame,
    candidate_skills: dict[str, set[str]],
    today: date = date(2026, 10, 8),
) -> dict:
    """Score top internal candidates and trace their backfill ripple chains.

    Returns the top-2 movers ordered by match score, each with a chain list,
    net cost, days saved, and promotion count.  Every number is derived from
    market_stats and build_plan; no story literals appear here.
    """
    baseline = _stat(market_stats_df, required_location, required_level)
    baseline_days = int(baseline["ttf_p50"]) if baseline else 62
    baseline_cost_lpa = float(baseline["sal_p50"]) if baseline else 32.0

    # Score all active open-to-move employees against the target role.
    scored = _score_movers(
        employees_df, emp_skills, evidence_df,
        required_skills, required_level, skill_edges_df, today,
    )
    top2 = [c for c in scored if c["match"] > 0][:2]

    candidates_out: list[dict] = []
    for cand in top2:
        pid = cand["person_id"]
        emp_row = employees_df[employees_df["employee_id"] == pid]
        if emp_row.empty:
            continue
        emp = emp_row.iloc[0]

        mover_level = str(emp["level"])
        mover_team = str(emp["team"])
        mover_loc = str(emp["location"])
        mover_wm = str(emp["work_mode"])

        # Bus-factor check for the mover.
        bf_flags = _bus_factor_check(
            pid, emp_skills.get(pid, set()),
            project_assignments, projects_df, emp_skills,
        )

        # Upskill plan for the mover against the target role.
        mover_ev = resolve_person(pid, evidence_df, today=today)
        bp = build_plan(
            pid, mover_ev, emp_skills.get(pid, set()),
            required_skills, skill_edges_df, mover_level, required_level,
        )

        mover_node: dict = {
            "person_id": pid,
            "seat": f"{required_level}/{required_team}",
            "status": "green",
            "reason": (
                f"Match {cand['match']}%"
                + (f"; ready week {bp['readiness_weeks']}" if bp["readiness_weeks"] > 0 else "")
            ),
            "evidence_ids": cand["evidence_ids"],
            "bus_factor_flags": bf_flags,
            "external_days": None,
            "readiness_weeks": bp["readiness_weeks"],
        }

        # Build ripple chain for the mover's vacated seat.
        chain = [mover_node] + _trace_chain(
            mover_level, mover_team, mover_loc, mover_wm,
            employees_df, emp_skills, evidence_df, skill_edges_df, market_stats_df,
            project_assignments, projects_df, candidates_df, candidate_skills, today,
        )

        # ── Net impact ─────────────────────────────────────────────────
        # Last external-hire node determines net days and the junior hire cost.
        last_ext = next(
            (n for n in reversed(chain) if n["person_id"] is None and n.get("external_days") is not None),
            None,
        )
        net_days = last_ext["external_days"] if last_ext else None
        days_saved = (baseline_days - net_days) if net_days is not None else None

        # Promotion count: internal fills where seat level > person's current level.
        promotions = 0
        for node in chain:
            if node["person_id"] is None:
                continue
            n_emp = employees_df[employees_df["employee_id"] == node["person_id"]]
            if n_emp.empty:
                continue
            seat_level = node["seat"].split("/")[0]
            person_level = str(n_emp.iloc[0]["level"])
            if _LEVEL_NUM.get(seat_level, 0) > _LEVEL_NUM.get(person_level, 0):
                promotions += 1

        # Raises: one raise per internal promotion.
        raises_lpa = 0.0
        for node in chain:
            if node["person_id"] is None:
                continue
            n_emp = employees_df[employees_df["employee_id"] == node["person_id"]]
            if n_emp.empty:
                continue
            seat_level = node["seat"].split("/")[0]
            person_level = str(n_emp.iloc[0]["level"])
            person_loc = str(n_emp.iloc[0]["location"])
            if _LEVEL_NUM.get(seat_level, 0) > _LEVEL_NUM.get(person_level, 0):
                raises_lpa += _promotion_raise_lpa(person_level, person_loc, market_stats_df)

        # External hire cost: salary P50 for the bottom external hire level.
        ext_hire_cost = 0.0
        if last_ext is not None:
            ext_level = last_ext["seat"].split("/")[0]
            ext_stat = _stat(market_stats_df, mover_loc, ext_level)
            if ext_stat:
                ext_hire_cost = float(ext_stat["sal_p50"])

        chain_cost = build_chain_cost(
            junior_salary_lpa=ext_hire_cost,
            raises_lpa=round(raises_lpa, 2),
            upskill_cost_lpa=bp["build_cost_lpa"],
        )
        net_cost_lpa = chain_cost["total_cost_lpa"]
        cost_saved_lpa = (
            round(baseline_cost_lpa - net_cost_lpa, 2)
            if net_days is not None else None
        )

        # Red flag count: bus-factor flags across all chain nodes.
        red_flags = sum(len(n.get("bus_factor_flags", [])) for n in chain)

        candidates_out.append({
            "person_id": pid,
            "match": cand["match"],
            "chain": chain,
            "bus_factor_flags": bf_flags,
            "readiness_weeks": bp["readiness_weeks"],
            "net_days_to_fill": net_days,
            "baseline_days": baseline_days,
            "days_saved": days_saved,
            "net_cost_lpa": net_cost_lpa,
            "baseline_cost_lpa": baseline_cost_lpa,
            "cost_saved_lpa": cost_saved_lpa,
            "promotions": promotions,
            "red_flags": red_flags,
            "upskill_breakdown": chain_cost["breakdown"],
        })

    return {
        "candidates": candidates_out,
        "baseline_days": baseline_days,
        "baseline_cost_lpa": baseline_cost_lpa,
    }
