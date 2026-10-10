"""Options engine — pure functions, no I/O.

Scores Build / Buy / Borrow / Relocate / Automate, generates ranked mixes.

AI reads language; Python does arithmetic; a human decides.
"""
from __future__ import annotations

import itertools
import math
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

_RED_FLAG_WEIGHT = 0.20
_AUTOMATE_READY_DAYS = 7
_AUTOMATE_COST_LPA = 1.0
_BUY_FIT_DEFAULT = 0.70
_RELOCATE_FIT_DEFAULT = 0.65
_DEFAULT_DURATION_MONTHS = 12

# Risk-label thresholds (documented in DECISIONS.md).
_RISK_HIGH = 0.60
_RISK_MEDIUM_HIGH = 0.45
_RISK_MEDIUM = 0.30

# Dejareq pattern-to-category mapping: churn applies to all external-hire
# categories (buy AND relocate); knowledge-loss applies to borrow.
_DEJAREQ_CATEGORY_MAP: dict[str, list[str]] = {
    "buy": ["buy", "relocate"],
    "borrow": ["borrow"],
}

# Build option card uses Build-band atoms only (match 70-84, needs upskilling).
# Redeploy atoms (match 85-100) stay valid in mixes but are not the Build card.
_BUILD_CARD_TYPES = {"build"}


def round_half_up(x: float) -> int:
    """Half-up rounding (72.5 → 73), matching JS Math.round behaviour."""
    return math.floor(x + 0.5)


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
    if risk_raw >= _RISK_HIGH:
        return "High"
    if risk_raw >= _RISK_MEDIUM_HIGH:
        return "Medium-high"
    if risk_raw >= _RISK_MEDIUM:
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


def _dejareq_delta(dejareq_result: dict, option_category: str) -> float:
    """Sum all dejareq risk adjustments that apply to this option category.

    Churn (option="buy") applies to buy AND relocate (both external hires).
    Knowledge-loss (option="borrow") applies to borrow only.
    """
    total = 0.0
    for adj in dejareq_result.get("risk_adjustments", []):
        pattern = adj.get("option", "")
        targets = _DEJAREQ_CATEGORY_MAP.get(pattern, [pattern])
        if option_category in targets:
            total += float(adj.get("delta", 0.0))
    return total


def _dejareq_adjustments_ledger(dejareq_result: dict) -> list[dict]:
    return [
        {"option": a["option"], "delta": a["delta"], "reason": a["reason"]}
        for a in dejareq_result.get("risk_adjustments", [])
    ]


def _atom_coverage_months(atom: dict) -> int | None:
    """How many months does this atom cover? None = full duration."""
    if atom["type"] == "bridge":
        return 3
    return None


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

    ripple_by_pid: dict[str, dict] = {}
    for cand in (ripple_result or {}).get("candidates", []):
        ripple_by_pid[cand["person_id"]] = cand

    for pid, m in match_results.items():
        band = m.get("band", "")
        fit = m.get("match", 0) / 100.0
        eids = list(m.get("evidence_ids", []))
        rc = ripple_by_pid.get(pid, {})

        cost = rc.get("net_cost_lpa", build_plans.get(pid, {}).get("build_cost_lpa", 0.0))
        weeks = rc.get("readiness_weeks", build_plans.get(pid, {}).get("readiness_weeks", 0))
        rf = rc.get("red_flags", 0)

        if band == "redeploy":
            atoms.append({
                "type": "redeploy",
                "person_id": pid,
                "location": None,
                "option_category": "build",
                "cost_lpa": cost,
                "days": weeks * 7,
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
                "cost_lpa": cost,
                "days": weeks * 7,
                "fit": fit,
                "red_flags": rf,
                "evidence_ids": eids,
            })

    _BRIDGE_MIN_FIT = 0.50  # bridge contractors must be qualified to cover the seat

    for ba in borrow_analyses:
        cid = ba.get("person_id", "")
        fit = ba.get("fit", 0) / 100.0
        atoms.append({
            "type": "extend",
            "person_id": cid,
            "location": None,
            "option_category": "borrow",
            "cost_lpa": ba.get("extend_cost_12m", 0.0),
            "days": 0,
            "fit": fit,
            "red_flags": 0,
            "evidence_ids": [],
        })
        if fit >= _BRIDGE_MIN_FIT:
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
                "days": 0,
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


# ── Coverage validation ──────────────────────────────────────────────────────


def _mix_covers_duration(mix: list[dict], duration_months: int) -> bool:
    """A mix is valid only if it covers the full need duration.

    A bridge atom covers only 3 months. A standalone bridge (or bridge +
    automate) cannot fill a 12-month need. A bridge paired with a longer-term
    atom (build, extend, buy, relocate) is valid because the longer atom takes
    over when the bridge ends.
    """
    non_auto = [a for a in mix if a["type"] != "automate"]
    if not non_auto:
        return False

    has_bridge_only = all(
        _atom_coverage_months(a) is not None
        and _atom_coverage_months(a) < duration_months
        for a in non_auto
    )
    return not has_bridge_only


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
    duration_months: int = _DEFAULT_DURATION_MONTHS,
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

        if not _mix_covers_duration(mix, duration_months):
            continue

        kept.append(mix)

    return kept


# ── Mix aggregation ──────────────────────────────────────────────────────────


def _mix_ready_by(mix: list[dict]) -> int:
    """Ready-by for a mix: a bridge or borrow covers day 0 while a build
    candidate ramps up, so the seat is covered from the earliest atom."""
    non_auto = [a for a in mix if a["type"] != "automate"]
    if not non_auto:
        return 0
    has_immediate = any(a["days"] == 0 for a in non_auto)
    if has_immediate and len(non_auto) > 1:
        return 0
    return max(a["days"] for a in non_auto)


def _mix_fit(mix: list[dict]) -> float:
    """Coverage-weighted fit: each non-automate atom contributes its fit
    weighted by its share of the time horizon it covers."""
    non_auto = [a for a in mix if a["type"] != "automate"]
    if not non_auto:
        return 0.0
    if len(non_auto) == 1:
        return non_auto[0]["fit"]
    total_days = sum(max(a["days"], 1) for a in non_auto)
    if total_days == 0:
        return sum(a["fit"] for a in non_auto) / len(non_auto)
    return sum(a["fit"] * max(a["days"], 1) / total_days for a in non_auto)


# ── Unified scoring ─────────────────────────────────────────────────────────


def _compute_entry_stats(
    mix: list[dict],
    dejareq_result: dict,
    sr_ledger: list[dict],
) -> dict:
    """Compute raw stats for a mix (or a single-atom option card treated
    as a one-element mix).  Used for both option cards and mixes so they
    share one normalization pool."""
    days = _mix_ready_by(mix)
    cost = sum(a["cost_lpa"] for a in mix)
    fit = _mix_fit(mix)

    categories = {a["option_category"] for a in mix if a["type"] != "automate"}
    risk_raw = 0.10
    for cat in categories:
        risk_raw += _dejareq_delta(dejareq_result, cat)
    risk_raw += sum(a.get("red_flags", 0) * _RED_FLAG_WEIGHT for a in mix)
    sr_pids = [a["person_id"] for a in mix if a["person_id"]]
    sr_penalty = sum(
        e["risk_delta"] for e in sr_ledger
        if e["person_id"] in sr_pids
    )
    risk_raw += sr_penalty

    strat_vals = [_STRATEGIC_PRIOR.get(a["option_category"], 0.5)
                  for a in mix if a["type"] != "automate"]
    strategic = sum(strat_vals) / len(strat_vals) if strat_vals else 0.5

    eids: list[str] = []
    for a in mix:
        eids.extend(a.get("evidence_ids", []))

    return {
        "atoms": mix,
        "days": days,
        "cost": cost,
        "fit": fit,
        "risk_raw": min(risk_raw, 1.0),
        "strategic": strategic,
        "evidence_ids": eids,
    }


def _score_pool(
    entries: list[dict],
    weights: dict[str, float],
) -> tuple[list[int], list[dict[str, float]]]:
    """Min-max normalize speed/cost across ALL entries and return (scores, dimensions)."""
    days_vals = [float(e["days"]) for e in entries]
    cost_vals = [e["cost"] for e in entries]
    days_mm = _minmax(days_vals)
    cost_mm = _minmax(cost_vals)

    scores: list[int] = []
    dims: list[dict[str, float]] = []
    for i, e in enumerate(entries):
        speed_n = 1.0 - days_mm[i]
        cost_n = 1.0 - cost_mm[i]
        fit_n = e["fit"]
        risk_n = 1.0 - e["risk_raw"]
        strat_n = e["strategic"]

        raw = (weights["speed"] * speed_n
               + weights["cost"] * cost_n
               + weights["fit"] * fit_n
               + weights["risk"] * risk_n
               + weights["strategic"] * strat_n)
        scores.append(round_half_up(raw * 100))
        dims.append({
            "speed": round(speed_n, 4),
            "cost": round(cost_n, 4),
            "fit": round(fit_n, 4),
            "risk": round(risk_n, 4),
            "strategic": round(strat_n, 4),
        })

    return scores, dims


# ── Build card selection (Build-band only) ───────────────────────────────────


def _best_atom_for_card(
    atoms: list[dict],
    category: str,
    weights: dict[str, float],
    dejareq_result: dict,
    sr_ledger: list[dict],
    duration_months: int = _DEFAULT_DURATION_MONTHS,
) -> dict | None:
    """Pick the best atom for an option card.

    For "build": only Build-band atoms (type=="build", match 70-84) are
    eligible; redeploy atoms (85-100) stay valid in mixes.
    For other categories: all atoms in that category, minus those that
    cannot cover the full need duration standalone.
    """
    if category == "build":
        candidates = [a for a in atoms
                      if a["option_category"] == "build"
                      and a["type"] in _BUILD_CARD_TYPES]
    else:
        candidates = [a for a in atoms if a["option_category"] == category]

    valid = [
        a for a in candidates
        if _atom_coverage_months(a) is None
        or _atom_coverage_months(a) >= duration_months
    ]
    if not valid:
        return None

    # Use a simple ranking for card selection within the same category:
    # the atom that will score best once it enters the shared pool.
    # Since we don't have min-max yet, use absolute approximation.
    max_days = 90.0
    max_cost = 40.0

    def _approx(a: dict) -> float:
        speed_n = max(0.0, 1.0 - a["days"] / max_days)
        cost_n = max(0.0, 1.0 - a["cost_lpa"] / max_cost)
        fit_n = a["fit"]
        risk_raw = 0.10 + _dejareq_delta(dejareq_result, a["option_category"])
        risk_raw += a.get("red_flags", 0) * _RED_FLAG_WEIGHT
        pid = a.get("person_id")
        if pid:
            risk_raw += sum(e["risk_delta"] for e in sr_ledger if e["person_id"] == pid)
        risk_raw = min(risk_raw, 1.0)
        strat_n = _STRATEGIC_PRIOR.get(a["option_category"], 0.5)
        return (weights["speed"] * speed_n
                + weights["cost"] * cost_n
                + weights["fit"] * fit_n
                + weights["risk"] * (1.0 - risk_raw)
                + weights["strategic"] * strat_n)

    return max(valid, key=_approx)


_OPTION_META: dict[str, dict] = {
    "build": {"option_id": "build", "name": "Build"},
    "buy": {"option_id": "buy", "name": "Buy"},
    "borrow": {"option_id": "borrow", "name": "Borrow"},
    "relocate": {"option_id": "relocate", "name": "Relocate"},
}


def _option_card_text(atom: dict, category: str) -> tuple[str, str]:
    """Return (what_it_means, one_line_reason) for an option card."""
    pid = atom.get("person_id")
    if category == "build":
        what = f"Promote {pid} via ripple chain" if pid else "No internal candidate"
        weeks = atom["days"] // 7
        reason = (f"{int(atom['fit'] * 100)}% match; ready in {weeks} weeks"
                  if pid else "No internal candidate")
    elif category == "buy":
        loc = atom.get("location", "")
        what = f"Hire externally in {loc}"
        reason = f"P80 {atom['days']} days; ₹{atom['cost_lpa']}L"
    elif category == "borrow":
        what = f"Extend contractor {pid}" if pid else "No contractor"
        reason = (f"{pid} available now; ₹{atom['cost_lpa']}L/year"
                  if pid else "No contractor")
    else:
        loc = atom.get("location", "")
        what = f"Hire in {loc}" if loc else "No alternative location"
        reason = (f"{loc}: P80 {atom['days']} days, ₹{atom['cost_lpa']}L"
                  if loc else "No alternative")
    return what, reason


def _build_option_automate(automation_result: dict) -> dict:
    low = automation_result.get("range_low", 0)
    high = automation_result.get("range_high", 0)
    return {
        "option_id": "automate",
        "name": "Automate",
        "what_it_means": "AI coding-assistant seats for the team (add-on)",
        "ready_by_p80_days": _AUTOMATE_READY_DAYS,
        "year_one_cost_lpa": _AUTOMATE_COST_LPA,
        "fit": 0.0,
        "risk_label": "Low",
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

    atoms = _generate_atoms(
        match_results, build_plans, borrow_analyses,
        location_results, automation_result, market_data,
        ripple_result=ripple_result,
    )

    # ── Pick representative atom per option card ──────────────────────
    card_atoms: dict[str, dict | None] = {}
    for cat in ("build", "buy", "borrow", "relocate"):
        card_atoms[cat] = _best_atom_for_card(
            atoms, cat, w, dejareq_result, sr_ledger,
            duration_months=duration_months,
        )

    # ── Generate and filter all mixes ─────────────────────────────────
    mixes = _generate_mixes(atoms, headcount)
    filtered = _filter_mixes(mixes, borrow_analyses, duration_months=duration_months)

    # ── Build unified scoring pool ────────────────────────────────────
    # Option cards (as single-atom mixes) + all valid mixes, in one pool
    # so min-max normalization is shared.
    pool: list[dict] = []          # entry stats
    pool_labels: list[str] = []    # "card:<cat>" or "mix"

    for cat in ("build", "buy", "borrow", "relocate"):
        atom = card_atoms[cat]
        if atom:
            pool.append(_compute_entry_stats([atom], dejareq_result, sr_ledger))
            pool_labels.append(f"card:{cat}")
        else:
            pool.append({
                "atoms": [],
                "days": 90,
                "cost": 0.0,
                "fit": 0.0,
                "risk_raw": 0.5,
                "strategic": _STRATEGIC_PRIOR[cat],
                "evidence_ids": [],
            })
            pool_labels.append(f"card:{cat}")

    for mix in filtered:
        pool.append(_compute_entry_stats(mix, dejareq_result, sr_ledger))
        pool_labels.append("mix")

    # ── Score the entire pool with shared min-max ─────────────────────
    all_scores, all_dims = _score_pool(pool, w)

    # ── Build option card dicts ───────────────────────────────────────
    options: list[dict] = []
    for idx, cat in enumerate(("build", "buy", "borrow", "relocate")):
        atom = card_atoms[cat]
        entry = pool[idx]
        score = all_scores[idx]
        dims = all_dims[idx]

        if atom:
            what, reason = _option_card_text(atom, cat)
            options.append({
                **_OPTION_META[cat],
                "what_it_means": what,
                "ready_by_p80_days": entry["days"],
                "year_one_cost_lpa": round(entry["cost"], 2),
                "fit": round(entry["fit"], 2),
                "risk_label": _risk_label(entry["risk_raw"]),
                "risk_raw": entry["risk_raw"],
                "score": score,
                "one_line_reason": reason,
                "evidence_ids": entry["evidence_ids"],
                "dimensions": dims,
            })
        else:
            options.append({
                **_OPTION_META[cat],
                "what_it_means": f"No {cat} candidate",
                "ready_by_p80_days": 90,
                "year_one_cost_lpa": 0.0,
                "fit": 0.0,
                "risk_label": "Medium",
                "risk_raw": 0.5,
                "score": score,
                "one_line_reason": f"No {cat} candidate available",
                "evidence_ids": [],
                "dimensions": dims,
            })

    automate_opt = _build_option_automate(automation_result)
    options.append(automate_opt)

    # ── Build top-3 mixes from pool ───────────────────────────────────
    n_cards = 4
    mix_scored: list[dict] = []
    for i in range(n_cards, len(pool)):
        ms = pool[i]
        score = all_scores[i]
        dims = all_dims[i]

        mix_scored.append({
            "mix_id": f"mix-{i - n_cards + 1}",
            "atoms": [
                {"type": a["type"], "person_id": a["person_id"],
                 "location": a["location"], "option_category": a["option_category"]}
                for a in ms["atoms"]
            ],
            "score": score,
            "cost_lpa": round(ms["cost"], 2),
            "ready_by_p80_days": ms["days"],
            "dimensions": dims,
            "evidence_ids": ms["evidence_ids"],
        })

    mix_scored.sort(key=lambda m: (-m["score"], m["cost_lpa"], len(m["atoms"])))
    top_mixes = mix_scored[:3]

    # ── Assumption ledger ─────────────────────────────────────────────
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


# ── Scenario scorer for redline ──────────────────────────────────────────────


def make_scenario_scorer(
    *,
    match_results: dict[str, dict],
    build_plans: dict[str, dict],
    borrow_analyses: list[dict],
    location_results: list[dict],
    automation_result: dict,
    ripple_result: dict,
    dejareq_result: dict,
    evidence_results: dict[str, list[dict]],
    base_location: str = "bengaluru",
    base_must_skill_ids: list[str] | None = None,
    deadline_days: int = 90,
    duration_months: int = 12,
) -> "Callable[[dict, dict], dict]":
    """Return a scorer function for redline scenarios.

    The returned callable has signature (ctx, market_ctx) -> dict with keys
    top_option_id, panel_text, options.

    Scenarios show how relaxing constraints changes the best option:
    - Base (no relaxation): Buy as-requested
    - Location relaxed: Relocate may beat Buy
    - Location + key skill relaxed: the full Mix recommendation surfaces

    Build/Borrow/Mix are constraint-independent (internal candidates), so
    they only appear when the scenario has relaxed enough constraints to
    warrant the full challenger recommendation.
    """
    w = _adjust_weights(dict(DEFAULT_WEIGHTS), deadline_days, duration_months)

    all_pids = list(match_results.keys()) + [ba["person_id"] for ba in borrow_analyses]
    _, sr_ledger = _self_report_penalty(all_pids, evidence_results)

    base_atoms = _generate_atoms(
        match_results, build_plans, borrow_analyses,
        location_results, automation_result,
        {"location": "", "sal_p50": 0, "ttf_p80": 90},
        ripple_result=ripple_result,
    )

    # Pre-compute the mix score for when it's included.
    bridge_build = [
        a for a in base_atoms
        if a["type"] in ("bridge", "build") and a.get("person_id")
    ]
    mix_entry = _compute_entry_stats(bridge_build, dejareq_result, sr_ledger) if bridge_build else None

    base_musts = set(base_must_skill_ids or [])

    def _scorer(ctx: dict, market_ctx: dict) -> dict:
        loc = ctx.get("location", base_location)
        loc_relaxed = (loc != base_location)
        ctx_musts = set(ctx.get("must_skill_ids", base_musts))
        skill_relaxed = (ctx_musts != base_musts)

        # Buy atom uses scenario-specific market data.
        buy_atom = {
            "type": "buy",
            "person_id": None,
            "location": loc,
            "option_category": "buy",
            "cost_lpa": float(market_ctx.get("pay_p50", 32.0)),
            "days": int(market_ctx.get("ttf_p80", 90)),
            "fit": _BUY_FIT_DEFAULT,
            "red_flags": 0,
            "evidence_ids": [],
        }

        buy_stats = _compute_entry_stats([buy_atom], dejareq_result, sr_ledger)

        # Relocate card: best alternative location (pre-computed, fixed).
        relocate_atoms = [a for a in base_atoms if a["option_category"] == "relocate"]
        best_reloc = None
        if loc_relaxed and relocate_atoms:
            best_reloc = relocate_atoms[0]
            reloc_stats = _compute_entry_stats([best_reloc], dejareq_result, sr_ledger)

        # Build the scoring pool: Buy + maybe Relocate + maybe Mix.
        pool = [buy_stats]
        pool_ids = ["buy"]

        if best_reloc is not None:
            pool.append(reloc_stats)
            pool_ids.append("relocate")

        include_mix = loc_relaxed and skill_relaxed and mix_entry is not None
        if include_mix:
            pool.append(mix_entry)
            pool_ids.append("mix")

        scores, _scenario_dims = _score_pool(pool, w)

        best_i = max(range(len(scores)), key=lambda i: scores[i])
        top_id = pool_ids[best_i]
        top_score = scores[best_i]
        top_entry = pool[best_i]

        p50 = market_ctx.get("ttf_p50", 62)
        pay = market_ctx.get("pay_p50", 32.0)

        if top_id == "buy":
            panel_text = f"Buy: P50 {p50} days, ₹{pay:.0f}L."
            options_out = [{
                "option_id": "buy",
                "name": "Buy",
                "score": float(top_score),
                "ready_by_p80_days": top_entry["days"],
                "year_one_cost_lpa": round(top_entry["cost"], 2),
                "panel_line": f"Hire in {loc}",
            }]
        elif top_id == "relocate":
            rloc = best_reloc["location"] if best_reloc else loc
            panel_text = f"Relocate: {rloc.replace('_', '-').title()}, P50 {p50} days, ₹{pay:.0f}L."
            options_out = [{
                "option_id": "relocate",
                "name": "Relocate",
                "score": float(top_score),
                "ready_by_p80_days": top_entry["days"],
                "year_one_cost_lpa": round(top_entry["cost"], 2),
                "panel_line": f"Hire in {rloc}",
            }]
        else:
            atoms_desc = " + ".join(
                a.get("person_id") or a.get("location", "")
                for a in top_entry["atoms"] if a["type"] != "automate"
            )
            panel_text = (
                f"Borrow {atoms_desc}: available now, "
                f"₹{top_entry['cost']:.0f}L in year one."
            )
            options_out = [{
                "option_id": "mix",
                "name": "Recommended mix",
                "score": float(top_score),
                "ready_by_p80_days": top_entry["days"],
                "year_one_cost_lpa": round(top_entry["cost"], 2),
                "panel_line": atoms_desc,
            }]

        return {
            "top_option_id": top_id,
            "panel_text": panel_text,
            "options": options_out,
        }

    return _scorer
