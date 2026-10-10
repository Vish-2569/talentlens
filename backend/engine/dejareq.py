"""Deja Req — past-requisition pattern analysis. Pure functions, no I/O.

Matches the current requisition against past requisitions by role, level,
skill Jaccard, and 24-month window. Detects churn and knowledge-loss patterns,
computes risk adjustments, and builds a cost story.
"""
from __future__ import annotations

from datetime import date

import pandas as pd


_EXIT_REASON_LABELS = {
    "role_mismatch": "role mismatch",
    "counter_offer": "counter offer",
    "better_offer": "better offer",
    "relocation": "relocation",
    "performance": "performance",
    "personal": "personal reasons",
    "layoff": "layoff",
    "contract_end": "contract ended",
}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    union = a | b
    if not union:
        return 0.0
    return len(a & b) / len(union)


_RATING_LABELS: dict[int, str] = {
    5: "Exceeds",
    4: "Meets+",
    3: "Meets",
    2: "Below",
    1: "Needs improvement",
}


def _outcome_text(
    req_row: dict, exits_df: pd.DataFrame, employees_df: pd.DataFrame,
) -> str:
    outcome = req_row["outcome"]

    if outcome == "still_in_role":
        pid = req_row["person_id"]
        emp = employees_df[employees_df["employee_id"] == pid]
        if not emp.empty:
            rating = int(emp.iloc[0].get("rating", 3))
            label = _RATING_LABELS.get(rating, f"rating {rating}")
            return f"Still in role, rated {label}"
        return "Still in role"

    if outcome == "knowledge_lost":
        return "Contract ended, knowledge lost"

    pid = req_row["person_id"]
    exit_match = exits_df[exits_df["employee_id"] == pid]
    if not exit_match.empty:
        row = exit_match.iloc[0]
        tenure = int(row["tenure_months"])
        reason = _EXIT_REASON_LABELS.get(row["exit_reason"], row["exit_reason"])
        return f"Left after {tenure} months ({reason})"

    if outcome.startswith("left_"):
        months = outcome.replace("left_", "").replace("m", "")
        return f"Left after {months} months"

    return outcome


def dejareq(
    parsed_req: dict,
    past_reqs: pd.DataFrame,
    employees: pd.DataFrame,
    emp_skills: dict[str, set[str]],
    contractors: pd.DataFrame,
    ctr_skills: dict[str, set[str]],
    exits: pd.DataFrame,
    today: date = date(2026, 10, 8),
) -> dict:
    role = parsed_req["role"]
    level = parsed_req["level"]
    skill_ids = set(parsed_req.get("skill_ids", []))
    cutoff = date(today.year - 2, today.month, today.day)

    matched_rows: list[dict] = []
    for _, req in past_reqs.iterrows():
        if req["role"] != role or req["level"] != level:
            continue
        opened = date.fromisoformat(req["opened_date"])
        if opened < cutoff:
            continue
        pid = req["person_id"]
        person_skills = (emp_skills.get(pid, set()) if pid.startswith("E-")
                         else ctr_skills.get(pid, set()))
        if _jaccard(skill_ids, person_skills) < 0.5:
            continue
        matched_rows.append(req.to_dict())

    n = len(matched_rows)

    if n == 0:
        return {"match_count": 0}

    if n == 1:
        return {"match_count": 1, "chip": "seen_once"}

    matched_rows.sort(key=lambda r: r["opened_date"], reverse=True)

    timeline: list[dict] = []
    for req in matched_rows:
        timeline.append({
            "req_id": req["req_id"],
            "opened_date": req["opened_date"],
            "closed_date": req["closed_date"],
            "decision": req["decision"],
            "outcome": _outcome_text(req, exits, employees),
            "person_id": req["person_id"],
            "first_year_cost_lpa": float(req["first_year_cost_lpa"]),
            "time_to_fill_days": int(req["time_to_fill_days"]),
            "evidence_ids": [req["req_id"], req["person_id"]],
        })

    team = parsed_req["team"]
    banner = (f"You've hired a {level.capitalize()} {role} for the "
              f"{team} team {n} times in the last 2 years.")

    # ── Churn: >= 2 buy decisions whose hires left within 12 months ──
    buy_rows = [t for t in timeline if t["decision"] == "buy"]
    buy_tenures: list[int] = []
    for t in buy_rows:
        exit_match = exits[exits["employee_id"] == t["person_id"]]
        if not exit_match.empty:
            buy_tenures.append(int(exit_match.iloc[0]["tenure_months"]))

    avg_tenure = sum(buy_tenures) / len(buy_tenures) if buy_tenures else 0.0
    churn = len(buy_tenures) >= 2 and avg_tenure < 12

    # ── Knowledge loss: a Borrow that ended without conversion ──
    knowledge_loss = any(
        t["decision"] == "borrow" and "knowledge lost" in t["outcome"].lower()
        for t in timeline
    )

    # ── What worked: any hire still active >= 3 months after close ──
    what_worked: str | None = None
    for t in timeline:
        pid = t["person_id"]
        if not pid.startswith("E-"):
            continue
        emp_row = employees[employees["employee_id"] == pid]
        if emp_row.empty or not emp_row.iloc[0]["is_active"]:
            continue
        closed = date.fromisoformat(t["closed_date"])
        if (today - closed).days / 30.44 >= 3:
            what_worked = t["decision"]
            break

    # ── Risk adjustments ──
    risk_adjustments: list[dict] = []
    if churn:
        risk_adjustments.append({
            "option": "buy",
            "delta": 0.20,
            "reason": (f"churn pattern: {len(buy_tenures)} external hires "
                       f"left in avg {round(avg_tenure)} months"),
        })
    if knowledge_loss:
        kl_count = sum(1 for t in timeline
                       if t["decision"] == "borrow"
                       and "knowledge lost" in t["outcome"].lower())
        risk_adjustments.append({
            "option": "borrow",
            "delta": 0.10,
            "reason": (f"knowledge loss: {kl_count} borrow ended "
                       f"without conversion"),
        })

    # ── Insight text ──
    parts: list[str] = []
    if churn:
        parts.append(
            f"Pattern: external hires for this role left in under a year "
            f"(average {round(avg_tenure)} months, "
            f"{len(buy_tenures)} of {len(buy_rows)})."
        )
    if what_worked:
        label = {"build": "internal move", "borrow": "contractor",
                 "buy": "external hire"}.get(what_worked, what_worked)
        parts.append(f"The one {label} is still in role.")
    parts.append("This requisition implies Buy.")
    if churn:
        parts.append("Your own history says that hasn't worked.")
    insight = " ".join(parts)

    # ── Cost story: Buy total vs Build total ──
    buy_total = sum(t["first_year_cost_lpa"] for t in timeline
                    if t["decision"] == "buy")
    build_total = sum(t["first_year_cost_lpa"] for t in timeline
                      if t["decision"] == "build")
    cost_story = {
        "buy_total_lpa": buy_total,
        "build_total_lpa": build_total,
        "difference_lpa": buy_total - build_total,
        "evidence_ids": [t["req_id"] for t in timeline],
    }

    # ── Averages by decision type ──
    averages: dict[str, dict] = {}
    by_dec: dict[str, list[dict]] = {}
    for t in timeline:
        by_dec.setdefault(t["decision"], []).append(t)
    for dec, rows in by_dec.items():
        entry: dict = {
            "count": len(rows),
            "avg_cost_lpa": round(
                sum(r["first_year_cost_lpa"] for r in rows) / len(rows), 1),
            "avg_ttf_days": round(
                sum(r["time_to_fill_days"] for r in rows) / len(rows)),
        }
        if dec == "buy":
            tenures: list[int] = []
            for r in rows:
                em = exits[exits["employee_id"] == r["person_id"]]
                if not em.empty:
                    tenures.append(int(em.iloc[0]["tenure_months"]))
            if tenures:
                entry["avg_tenure_months"] = round(
                    sum(tenures) / len(tenures))
        averages[dec] = entry

    all_evidence: list[str] = []
    for t in timeline:
        all_evidence.extend(t["evidence_ids"])

    return {
        "match_count": n,
        "banner": banner,
        "timeline": timeline,
        "averages": averages,
        "patterns": {
            "churn": churn,
            "knowledge_loss": knowledge_loss,
            "what_worked": what_worked,
        },
        "risk_adjustments": risk_adjustments,
        "insight": insight,
        "cost_story": cost_story,
        "evidence_ids": sorted(set(all_evidence)),
    }
