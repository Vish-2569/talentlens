"""Options engine — pure functions, no I/O.

Scores Build / Buy / Borrow / Relocate / Automate, generates ranked mixes.

AI reads language; Python does arithmetic; a human decides.
"""
from __future__ import annotations

import itertools
from datetime import date

DEFAULT_WEIGHTS: dict[str, float] = {
    "speed": 0.30,
    "cost": 0.25,
    "fit": 0.20,
    "risk": 0.15,
    "strategic": 0.10,
}

_STRATEGIC_PRIOR: dict[str, float] = {
    "build": 0.90,
    "buy": 0.30,
    "borrow": 0.40,
    "relocate": 0.35,
    "automate": 0.50,
}

_BORROW_READY_DAYS = 14
_AUTOMATE_READY_DAYS = 7
_AUTOMATE_COST_LPA = 1.0
_BUY_FIT_DEFAULT = 0.70
_RELOCATE_FIT_DEFAULT = 0.65


# ── Helpers ──────────────────────────────────────────────────────────────────


def _adjust_weights(
    weights: dict[str, float],
    deadline_days: int,
    duration_months: int,
) -> dict[str, float]:
    w = dict(weights)
    if deadline_days < 60:
        w["speed"] = w.get("speed", 0.30) + 0.10
        w["strategic"] = max(0.0, w.get("strategic", 0.10) - 0.05)
        w["cost"] = max(0.0, w.get("cost", 0.25) - 0.05)
    if duration_months < 9:
        w["speed"] = w.get("speed", 0.30) + 0.05
        w["strategic"] = max(0.0, w.get("strategic", 0.10) - 0.05)
    total = sum(w.values())
    if total > 0:
        w = {k: v / total for k, v in w.items()}
    return w


def _minmax(values: list[float]) -> list[float]:
    mn, mx = min(values), max(values)
    rng = mx - mn
    if rng == 0.0:
        return [0.0] * len(values)
    return [(v - mn) / rng for v in values]


def _risk_label(risk_raw: float) -> str:
    if risk_raw >= 0.6:
        return "High"
    if risk_raw >= 0.45:
        return "Medium-high"
    if risk_raw >= 0.3:
        return "Medium"
    return "Low"


def _self_report_penalty(
    person_ids: list[str],
    evidence_results: dict[str, list[dict]],
) -> tuple[float, list[dict]]:
    penalty = 0.0
    ledger: list[dict] = []
    for pid in person_ids:
        for ev in evidence_results.get(pid, []):
            if ev.get("source") == "self" and not ev.get("ignored"):
                penalty += 0.05
                ledger.append({
                    "person_id": pid,
                    "skill": ev.get("skill", ""),
                    "risk_delta": 0.05,
                })
    return penalty, ledger


def _dejareq_delta(dejareq_result: dict, option_id: str) -> float:
    for adj in dejareq_result.get("risk_adjustments", []):
        if adj.get("option") == option_id:
            return float(adj.get("delta", 0.0))
    return 0.0


def _dejareq_adjustments_ledger(dejareq_result: dict) -> list[dict]:
    return [
        {"option": a["option"], "delta": a["delta"], "reason": a["reason"]}
        for a in dejareq_result.get("risk_adjustments", [])
    ]


# ── Atom generation ──────────────────────────────────────────────────────────


def _generate_atoms(
    match_results: dict[str, dict],
    build_plans: dict[str, dict],
    borrow_analyses: list[dict],
    location_results: list[dict],
    automation_result: dict,
    market_data: dict,
    ripple_result: dict | None = None,
) -> list[dict]:
    atoms: list[dict] = []

    ripple_flags: dict[str, int] = {}
    for cand in (ripple_result or {}).get("candidates", []):
        ripple_flags[cand["person_id"]] = cand.get("red_flags", 0)

    for pid, m in match_results.items():
        band = m.get("band", "")
        fit = m.get("match", 0) / 100.0
        eids = list(m.get("evidence_ids", []))
        rf = ripple_flags.get(pid, 0)

        if band == "redeploy":
            atoms.append({
                "type": "redeploy",
                "person_id": pid,
                "location": None,
                "option_category": "build",
                "cost_lpa": build_plans.get(pid, {}).get("build_cost_lpa", 0.0),
                "days": build_plans.get(pid, {}).get("readiness_weeks", 0) * 7,
                "fit": fit,
                "red_flags": rf,
                "evidence_ids": eids,
            })
        elif band == "Build":
            atoms.append({
                "type": "build",
                "person_id": pid,
                "location": None,
                "option_category": "build",
                "cost_lpa": build_plans.get(pid, {}).get("build_cost_lpa", 0.0),
                "days": build_plans.get(pid, {}).get("readiness_weeks", 0) * 7,
                "fit": fit,
                "red_flags": rf,
                "evidence_ids": eids,
            })

    for ba in borrow_analyses:
        cid = ba.get("person_id", "")
        fit = ba.get("fit", 0) / 100.0
        atoms.append({
            "type": "extend",
            "person_id": cid,
            "location": None,
            "option_category": "borrow",
            "cost_lpa": ba.get("extend_cost_12m", 0.0),
            "days": _BORROW_READY_DAYS,
            "fit": fit,
            "red_flags": 0,
            "evidence_ids": [],
        })
        atoms.append({
            "type": "bridge",
            "person_id": cid,
            "location": None,
            "option_category": "borrow",
            "cost_lpa": ba.get("extend_cost_3m", 0.0),
            "days": 0,
            "fit": fit,
            "red_flags": 0,
            "evidence_ids": [],
        })
        if ba.get("conversion_signal"):
            atoms.append({
                "type": "convert",
                "person_id": cid,
                "location": None,
                "option_category": "borrow",
                "cost_lpa": ba.get("extend_cost_12m", 0.0),
                "days": _BORROW_READY_DAYS,
                "fit": fit,
                "red_flags": 0,
                "evidence_ids": [],
            })

    atoms.append({
        "type": "buy",
        "person_id": None,
        "location": market_data.get("location", ""),
        "option_category": "buy",
        "cost_lpa": float(market_data.get("sal_p50", 0)),
        "days": int(market_data.get("ttf_p80", 90)),
        "fit": _BUY_FIT_DEFAULT,
        "red_flags": 0,
        "evidence_ids": [],
    })

    for loc in location_results:
        if loc.get("location") == market_data.get("location"):
            continue
        atoms.append({
            "type": "relocate",
            "person_id": None,
            "location": loc["location"],
            "option_category": "relocate",
            "cost_lpa": loc.get("pay_p50_lpa", 0.0),
            "days": int(loc.get("ttf_p80", 60)),
            "fit": _RELOCATE_FIT_DEFAULT,
            "red_flags": 0,
            "evidence_ids": [],
        })

    atoms.append({
        "type": "automate",
        "person_id": None,
        "location": None,
        "option_category": "automate",
        "cost_lpa": _AUTOMATE_COST_LPA,
        "days": _AUTOMATE_READY_DAYS,
        "fit": 0.0,
        "red_flags": 0,
        "evidence_ids": list(automation_result.get("evidence_ids", [])),
    })

    return atoms


# ── Mix generation & filtering ───────────────────────────────────────────────


def _generate_mixes(
    atoms: list[dict],
    headcount: int = 1,
    max_per_mix: int = 3,
) -> list[list[dict]]:
    non_auto = [a for a in atoms if a["type"] != "automate"]
    auto = [a for a in atoms if a["type"] == "automate"]

    mixes: list[list[dict]] = []

    for size in range(1, min(max_per_mix, len(non_auto)) + 1):
        for combo in itertools.combinations(non_auto, size):
            mixes.append(list(combo))

    if auto:
        extra: list[list[dict]] = []
        for mix in mixes:
            extra.append(mix + auto)
        mixes.extend(extra)

    return mixes


def _filter_mixes(
    mixes: list[list[dict]],
    borrow_analyses: list[dict],
) -> list[list[dict]]:
    compliance_ids = {
        ba["person_id"]
        for ba in borrow_analyses
        if ba.get("compliance_flag")
    }

    kept: list[list[dict]] = []
    for mix in mixes:
        person_ids = [a["person_id"] for a in mix if a["person_id"] is not None]
        if len(person_ids) != len(set(person_ids)):
            continue

        non_auto = [a for a in mix if a["type"] != "automate"]
        if not non_auto:
            continue

        if any(a["person_id"] in compliance_ids for a in mix
               if a.get("option_category") == "borrow" and a["person_id"]):
            continue

        kept.append(mix)

    return kept


# ── Scoring ──────────────────────────────────────────────────────────────────


def _score_mixes(
    mixes: list[list[dict]],
    weights: dict[str, float],
    dejareq_result: dict,
    self_report_ledger: list[dict],
) -> list[dict]:
    if not mixes:
        return []

    mix_stats: list[dict] = []
    for mix in mixes:
        days = max(a["days"] for a in mix)
        cost = sum(a["cost_lpa"] for a in mix)
        fits = [a["fit"] for a in mix if a["type"] != "automate"]
        fit = sum(fits) / len(fits) if fits else 0.0

        categories = {a["option_category"] for a in mix if a["type"] != "automate"}
        risk_raw = 0.10
        for cat in categories:
            risk_raw += _dejareq_delta(dejareq_result, cat)
        risk_raw += sum(a.get("red_flags", 0) * 0.05 for a in mix)
        sr_pids = [a["person_id"] for a in mix if a["person_id"]]
        sr_penalty = sum(
            e["risk_delta"] for e in self_report_ledger
            if e["person_id"] in sr_pids
        )
        risk_raw += sr_penalty

        strat_vals = [_STRATEGIC_PRIOR.get(a["option_category"], 0.5)
                      for a in mix if a["type"] != "automate"]
        strategic = sum(strat_vals) / len(strat_vals) if strat_vals else 0.5

        eids: list[str] = []
        for a in mix:
            eids.extend(a.get("evidence_ids", []))

        mix_stats.append({
            "atoms": mix,
            "days": days,
            "cost": cost,
            "fit": fit,
            "risk_raw": min(risk_raw, 1.0),
            "strategic": strategic,
            "evidence_ids": eids,
        })

    days_vals = [m["days"] for m in mix_stats]
    cost_vals = [m["cost"] for m in mix_stats]
    days_mm = _minmax([float(d) for d in days_vals])
    cost_mm = _minmax(cost_vals)

    scored: list[dict] = []
    for i, ms in enumerate(mix_stats):
        speed_n = 1.0 - days_mm[i]
        cost_n = 1.0 - cost_mm[i]
        fit_n = ms["fit"]
        risk_n = 1.0 - ms["risk_raw"]
        strat_n = ms["strategic"]

        raw = (weights["speed"] * speed_n
               + weights["cost"] * cost_n
               + weights["fit"] * fit_n
               + weights["risk"] * risk_n
               + weights["strategic"] * strat_n)
        score = round(raw * 100)

        scored.append({
            "mix_id": f"mix-{i + 1}",
            "atoms": [
                {"type": a["type"], "person_id": a["person_id"],
                 "location": a["location"], "option_category": a["option_category"]}
                for a in ms["atoms"]
            ],
            "score": score,
            "speed": round(speed_n, 4),
            "cost": round(cost_n, 4),
            "fit": round(fit_n, 4),
            "risk": round(ms["risk_raw"], 4),
            "strategic": round(strat_n, 4),
            "evidence_ids": ms["evidence_ids"],
        })

    scored.sort(key=lambda m: -m["score"])
    return scored[:3]


# ── Five canonical options ───────────────────────────────────────────────────


def _build_option_build(
    ripple_result: dict,
    build_plans: dict[str, dict],
    match_results: dict[str, dict],
    dejareq_result: dict,
    sr_penalty: float,
) -> dict:
    candidates = ripple_result.get("candidates", [])
    if candidates:
        best = candidates[0]
        pid = best["person_id"]
        fit = match_results.get(pid, {}).get("match", 0) / 100.0
        weeks = best.get("readiness_weeks", 0)
        cost = best.get("net_cost_lpa", 0.0)
        eids = list(match_results.get(pid, {}).get("evidence_ids", []))
        red_flags = best.get("red_flags", 0)
        what = f"Promote {pid} via ripple chain"
    else:
        fit = 0.0
        weeks = 0
        cost = 0.0
        eids = []
        red_flags = 0
        what = "No internal candidate available"

    risk_raw = 0.10 + _dejareq_delta(dejareq_result, "build")
    if red_flags > 0:
        risk_raw += 0.05 * red_flags
    risk_raw += sr_penalty
    risk_raw = min(risk_raw, 1.0)

    return {
        "option_id": "build",
        "name": "Build",
        "what_it_means": what,
        "ready_by_p80_days": weeks * 7,
        "year_one_cost_lpa": round(cost, 2),
        "fit": round(fit, 2),
        "risk_raw": round(risk_raw, 4),
        "risk_label": _risk_label(risk_raw),
        "strategic": _STRATEGIC_PRIOR["build"],
        "one_line_reason": (
            f"{int(fit * 100)}% match; ready in {weeks} weeks"
            if candidates else "No internal candidate"
        ),
        "evidence_ids": eids,
    }


def _build_option_buy(
    market_data: dict,
    dejareq_result: dict,
) -> dict:
    ttf_p80 = int(market_data.get("ttf_p80", 90))
    sal_p50 = float(market_data.get("sal_p50", 0))
    supply = int(market_data.get("supply", 0))
    location = market_data.get("location", "")

    risk_raw = 0.20 + _dejareq_delta(dejareq_result, "buy")
    if supply < 20:
        risk_raw += 0.15
    risk_raw = min(risk_raw, 1.0)

    return {
        "option_id": "buy",
        "name": "Buy",
        "what_it_means": f"Hire externally in {location}",
        "ready_by_p80_days": ttf_p80,
        "year_one_cost_lpa": round(sal_p50, 2),
        "fit": _BUY_FIT_DEFAULT,
        "risk_raw": round(risk_raw, 4),
        "risk_label": _risk_label(risk_raw),
        "strategic": _STRATEGIC_PRIOR["buy"],
        "one_line_reason": f"P80 {ttf_p80} days; supply {supply}; ₹{sal_p50}L",
        "evidence_ids": [],
    }


def _build_option_borrow(
    borrow_analyses: list[dict],
    dejareq_result: dict,
    duration_months: int,
    sr_penalty: float,
) -> dict:
    if borrow_analyses:
        best = borrow_analyses[0]
        cid = best["person_id"]
        fit = best.get("fit", 0) / 100.0
        if duration_months <= 3:
            cost = best.get("extend_cost_3m", 0.0)
        else:
            cost = best.get("extend_cost_12m", 0.0)
        what = f"Extend contractor {cid}"
    else:
        cid = ""
        fit = 0.0
        cost = 0.0
        what = "No contractor available"

    risk_raw = 0.15 + _dejareq_delta(dejareq_result, "borrow") + sr_penalty
    risk_raw = min(risk_raw, 1.0)

    return {
        "option_id": "borrow",
        "name": "Borrow",
        "what_it_means": what,
        "ready_by_p80_days": _BORROW_READY_DAYS if borrow_analyses else 90,
        "year_one_cost_lpa": round(cost, 2),
        "fit": round(fit, 2),
        "risk_raw": round(risk_raw, 4),
        "risk_label": _risk_label(risk_raw),
        "strategic": _STRATEGIC_PRIOR["borrow"],
        "one_line_reason": (
            f"{cid} available now; ₹{cost}L/year"
            if borrow_analyses else "No contractor available"
        ),
        "evidence_ids": [],
    }


def _build_option_relocate(
    location_results: list[dict],
    requested_location: str,
    dejareq_result: dict,
) -> dict:
    alt = [r for r in location_results if r.get("location") != requested_location]
    if alt:
        best = alt[0]
        loc = best["location"]
        ttf_p80 = int(best.get("ttf_p80", 60))
        pay = float(best.get("pay_p50_lpa", 0))
        supply = int(best.get("supply", 0))
        what = f"Hire in {loc} instead of {requested_location}"
    else:
        loc = ""
        ttf_p80 = 90
        pay = 0.0
        supply = 0
        what = "No alternative location"

    risk_raw = 0.25 + _dejareq_delta(dejareq_result, "buy")
    risk_raw = min(risk_raw, 1.0)

    return {
        "option_id": "relocate",
        "name": "Relocate",
        "what_it_means": what,
        "ready_by_p80_days": ttf_p80,
        "year_one_cost_lpa": round(pay, 2),
        "fit": _RELOCATE_FIT_DEFAULT,
        "risk_raw": round(risk_raw, 4),
        "risk_label": _risk_label(risk_raw),
        "strategic": _STRATEGIC_PRIOR["relocate"],
        "one_line_reason": (
            f"{loc}: supply {supply}, P80 {ttf_p80} days, ₹{pay}L"
            if alt else "No alternative location"
        ),
        "evidence_ids": [],
    }


def _build_option_automate(
    automation_result: dict,
) -> dict:
    pct = automation_result.get("hours_saved_pct", 0)
    low = automation_result.get("range_low", 0)
    high = automation_result.get("range_high", 0)
    return {
        "option_id": "automate",
        "name": "Automate",
        "what_it_means": "AI coding-assistant seats for the team (add-on)",
        "ready_by_p80_days": _AUTOMATE_READY_DAYS,
        "year_one_cost_lpa": _AUTOMATE_COST_LPA,
        "fit": 0.0,
        "risk_raw": 0.05,
        "risk_label": "Low",
        "strategic": _STRATEGIC_PRIOR["automate"],
        "score": "add-on",
        "one_line_reason": f"Absorbs ~{low:.0f}-{high:.0f}% of routine hours",
        "evidence_ids": list(automation_result.get("evidence_ids", [])),
    }


# ── Main public function ────────────────────────────────────────────────────


def generate_options(
    *,
    match_results: dict[str, dict],
    build_plans: dict[str, dict],
    borrow_analyses: list[dict],
    market_data: dict,
    location_results: list[dict],
    automation_result: dict,
    ripple_result: dict,
    dejareq_result: dict,
    evidence_results: dict[str, list[dict]],
    headcount: int = 1,
    deadline_days: int = 90,
    duration_months: int = 12,
    weights: dict[str, float] | None = None,
    today: date = date(2026, 10, 8),
) -> dict:
    w = _adjust_weights(weights or dict(DEFAULT_WEIGHTS), deadline_days, duration_months)

    all_person_ids = (
        list(match_results.keys())
        + [ba["person_id"] for ba in borrow_analyses]
    )
    sr_total, sr_ledger = _self_report_penalty(all_person_ids, evidence_results)

    build_opt = _build_option_build(
        ripple_result, build_plans, match_results, dejareq_result,
        sr_penalty=sr_total,
    )
    buy_opt = _build_option_buy(market_data, dejareq_result)
    borrow_opt = _build_option_borrow(
        borrow_analyses, dejareq_result, duration_months, sr_penalty=sr_total,
    )
    relocate_opt = _build_option_relocate(
        location_results, market_data.get("location", ""), dejareq_result,
    )
    automate_opt = _build_option_automate(automation_result)

    scored_options = [build_opt, buy_opt, borrow_opt, relocate_opt]

    days_vals = [o["ready_by_p80_days"] for o in scored_options]
    cost_vals = [o["year_one_cost_lpa"] for o in scored_options]
    days_mm = _minmax([float(d) for d in days_vals])
    cost_mm = _minmax(cost_vals)

    for i, opt in enumerate(scored_options):
        speed_n = 1.0 - days_mm[i]
        cost_n = 1.0 - cost_mm[i]
        fit_n = opt["fit"]
        risk_n = 1.0 - opt["risk_raw"]
        strat_n = opt["strategic"]

        raw = (w["speed"] * speed_n
               + w["cost"] * cost_n
               + w["fit"] * fit_n
               + w["risk"] * risk_n
               + w["strategic"] * strat_n)
        opt["score"] = round(raw * 100)

    for opt in scored_options:
        del opt["risk_raw"]
        del opt["strategic"]

    automate_opt.pop("risk_raw", None)
    automate_opt.pop("strategic", None)

    options = scored_options + [automate_opt]

    atoms = _generate_atoms(
        match_results, build_plans, borrow_analyses,
        location_results, automation_result, market_data,
        ripple_result=ripple_result,
    )
    mixes = _generate_mixes(atoms, headcount)
    filtered = _filter_mixes(mixes, borrow_analyses)
    top_mixes = _score_mixes(filtered, w, dejareq_result, sr_ledger)

    weight_shifts: list[dict] = []
    if deadline_days < 60:
        weight_shifts.append({"shift": "deadline < 60 days", "effect": "speed +0.10"})
    if duration_months < 9:
        weight_shifts.append({"shift": "duration < 9 months", "effect": "speed +0.05, borrow favoured"})

    return {
        "options": options,
        "top_mixes": top_mixes,
        "weights_used": w,
        "assumption_ledger": {
            "self_report_risks": sr_ledger,
            "dejareq_adjustments": _dejareq_adjustments_ledger(dejareq_result),
            "weight_shifts": weight_shifts,
        },
    }
