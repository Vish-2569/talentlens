"""Next-action drafts from the chosen option — pure functions, no I/O.

From the recommended mix, generate draft actions: contract extensions,
development plans, backfill requisitions, and ATS rediscovery.
Drafts only; nothing is executed or sent.
"""
from __future__ import annotations


def _find_contractor(person_id: str, contractor_cards: list[dict]) -> dict | None:
    for c in contractor_cards:
        if c["person_id"] == person_id:
            return c
    return None


def _find_internal(person_id: str, internal_candidates: list[dict]) -> dict | None:
    for c in internal_candidates:
        if c["person_id"] == person_id:
            return c
    return None


def _find_ripple_candidate(person_id: str, ripple_result: dict) -> dict | None:
    for c in ripple_result.get("candidates", []):
        if c["person_id"] == person_id:
            return c
    return None


def _external_hire_nodes(chain: list[dict]) -> list[dict]:
    return [n for n in chain if n.get("person_id") is None]


def _gap_skills_from_candidate(internal: dict) -> list[str]:
    bp = internal.get("build_plan", {})
    return [g["skill_id"] for g in bp.get("gap_skills", [])]


def generate_actions(
    *,
    chosen_mix: dict,
    ripple_result: dict,
    sourcing_result: dict,
    contractor_cards: list[dict],
    internal_candidates: list[dict],
) -> list[dict]:
    """Generate next-action drafts from the chosen option/mix.

    Parameters
    ----------
    chosen_mix : dict
        A mix from ``options_result["top_mixes"]``.  Has ``atoms`` (list of
        dicts with type/person_id/location/option_category), ``score``,
        ``cost_lpa``.
    ripple_result : dict
        Output of ``analyze_ripple``.
    sourcing_result : dict
        Output of ``analyze_sourcing``.
    contractor_cards : list[dict]
        Contractor analysis cards (from borrow + match).
    internal_candidates : list[dict]
        Internal candidate cards with match/band/readiness.

    Returns
    -------
    list[dict]
        Each action: ``{type, title, detail, evidence_ids}``.
    """
    actions: list[dict] = []
    atoms = chosen_mix.get("atoms", [])

    for atom in atoms:
        atype = atom.get("type", "")
        pid = atom.get("person_id")

        if atype in ("bridge", "extend") and pid:
            ctr = _find_contractor(pid, contractor_cards)
            if ctr is None:
                continue
            name = ctr.get("display_name", pid)
            if atype == "bridge":
                months = 3
                cost = ctr.get("extend_cost_3m",
                               round(ctr.get("extend_cost_lpa", 0) / 4, 1))
                title = f"Extend {name}'s contract for {months} months (bridge)"
                detail = (
                    f"Bridge engagement: ₹{cost}L for {months} months. "
                    f"Fit {ctr.get('fit', 0)}%, "
                    f"{ctr.get('availability', 'availability unknown')}."
                )
            else:
                months = 12
                cost = ctr.get("extend_cost_lpa", 0)
                title = f"Extend {name}'s contract for {months} months"
                detail = (
                    f"Full extension: ₹{cost}L for {months} months. "
                    f"Fit {ctr.get('fit', 0)}%, "
                    f"{ctr.get('availability', 'availability unknown')}."
                )
            actions.append({
                "type": "contract_extension",
                "title": title,
                "detail": detail,
                "evidence_ids": ctr.get("evidence_ids", []),
            })

        elif atype == "build" and pid:
            internal = _find_internal(pid, internal_candidates)
            if internal is None:
                continue
            name = internal.get("display_name", pid)
            weeks = internal.get("readiness_weeks", 0)

            gap_skills = _gap_skills_from_candidate(internal)
            if gap_skills:
                skill_label = ", ".join(gap_skills)
                title = f"Start {name}'s {skill_label} upskill ({weeks} weeks)"
            else:
                title = f"Start {name}'s development plan ({weeks} weeks)"

            detail = (
                f"Readiness: week {weeks}. "
                f"Build cost: ₹{internal.get('build_cost_lpa', 0)}L."
            )
            actions.append({
                "type": "development_plan",
                "title": title,
                "detail": detail,
                "evidence_ids": internal.get("evidence_ids", []),
            })

            ripple_cand = _find_ripple_candidate(pid, ripple_result)
            if ripple_cand:
                chain = ripple_cand.get("chain", [])
                for ext_node in _external_hire_nodes(chain):
                    seat = ext_node.get("seat", "unknown seat")
                    actions.append({
                        "type": "backfill_requisition",
                        "title": f"Open backfill requisition: {seat}",
                        "detail": ext_node.get("reason", ""),
                        "evidence_ids": ext_node.get("evidence_ids", []),
                    })

    pf = sourcing_result.get("past_finalists", {})
    if pf.get("count", 0) > 0:
        count = pf["count"]
        remote = pf.get("remote_ready", 0)
        actions.append({
            "type": "ats_rediscovery",
            "title": f"Contact {count} past finalists from ATS",
            "detail": (
                f"{count} candidates reached the final round in the last "
                f"12 months; {remote} open to remote."
            ),
            "evidence_ids": pf.get("ids", []),
        })

    return actions
