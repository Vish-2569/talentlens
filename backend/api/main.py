from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.api.schemas import (
    AnalysisResult,
    AnalyzeRequest,
    Brief,
    BriefSection,
    Constraint,
    ConstraintCost,
    ContractorCard,
    DataQuality,
    DejaReq,
    Health,
    InternalCandidate,
    MarketCard,
    MixOption,
    NetImpact,
    OptionCard,
    OptionSummary,
    OptionWeights,
    Options,
    ParsedField,
    ParsedRequisition,
    ParsedSkill,
    PastFinalist,
    Pattern,
    Redline,
    RelocateRow,
    Ripple,
    RippleCandidate,
    RippleNode,
    ScenarioResult,
    SkillScore,
    Sourcing,
    SourcingChannel,
    SupplierRanking,
    TimelineEntry,
    AverageByDecision,
    Tokens,
    TitleMapping,
    TitleNormalization,
    DecisionRequest,
)
from backend.config import settings
from backend.db import Database
from backend.decisions import record_decision
from backend.store import DataStore

from backend.engine.parser import regex_parse
from backend.engine.normalize import title_normalization_panel
from backend.engine.evidence import resolve_person, data_quality as ev_data_quality
from backend.engine.match import score_employee, score_contractor
from backend.engine.build import build_plan
from backend.engine.borrow import analyze_contractor
from backend.engine.dejareq import dejareq
from backend.engine.ripple import analyze_ripple
from backend.engine.automate import estimate_automation
from backend.engine.sourcing import analyze_sourcing
from backend.engine.location import compare_locations
from backend.engine.market import matching_supply, market_card as mk_market_card
from backend.engine.options import generate_options, make_scenario_scorer
from backend.engine.redline import analyze_redline
from backend.engine.brief import generate_brief
import backend.llm as llm

app = FastAPI(title="TalentLens", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_methods=["*"],
    allow_headers=["*"],
)

_STUB_PATH = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "analyze_stub.json"
_stub_data: dict | None = None


def _load_stub() -> dict:
    global _stub_data
    if _stub_data is None:
        _stub_data = json.loads(_STUB_PATH.read_text(encoding="utf-8"))
    return _stub_data


# ── DataStore lazy singleton ──────────────────────────────────────────────────

_store: DataStore | None = None


def _get_store() -> DataStore:
    global _store
    if _store is None:
        _store = DataStore()
    return _store


# ── Location display names ────────────────────────────────────────────────────

_LOC_DISPLAY: dict[str, str] = {
    "remote_india": "Remote-India",
    "hyderabad": "Hyderabad (on-site)",
    "pune": "Pune (on-site)",
}


def _loc_display(loc_id: str, base_location: str) -> str:
    if loc_id == base_location:
        return f"{loc_id.replace('_', '-').title()} (on-site, as requested)"
    return _LOC_DISPLAY.get(loc_id, loc_id.replace("_", "-").title())


# ── req_id ────────────────────────────────────────────────────────────────────

def _make_req_id(text: str, today: date) -> str:
    norm = " ".join(text.lower().split())
    return "REQ-" + hashlib.sha256(f"{norm}|{today}".encode()).hexdigest()[:8].upper()


# ── Field helpers ─────────────────────────────────────────────────────────────

def _inferred_field(value: Any = None) -> dict:
    return {"value": value, "span": None, "span_start": None, "span_end": None, "label": "inferred"}


def _merge_llm_fields(fields: dict, llm_result: dict, text: str, needs: list[str]) -> None:
    """Merge LLM extracted fields into the regex fields dict for needed fields."""
    for field_name in needs:
        llm_field = llm_result.get(field_name)
        if llm_field is None:
            continue
        val = llm_field.get("value") if isinstance(llm_field, dict) else None
        span = llm_field.get("span") if isinstance(llm_field, dict) else None
        if val is None:
            continue
        # Find span positions if possible
        start, end = 0, 0
        if span:
            idx = text.lower().find(span.lower())
            if idx >= 0:
                start, end = idx, idx + len(span)
        fields[field_name] = {
            "value": val,
            "span": span or val,
            "span_start": start,
            "span_end": end,
            "label": "inferred",
        }


def _fill_defaults(fields: dict) -> dict:
    """Fill any still-missing fields with inferred defaults."""
    defaults = {
        "headcount": 1,
        "duration_months": None,
        "criticality": None,
        "min_years": 0,
        "budget_lpa": 0,
        "need_by_days": 90,
    }
    for key, default_val in defaults.items():
        if key not in fields:
            fields[key] = _inferred_field(default_val)
    # Required enum fields default to None if still missing (triggers warning but doesn't crash)
    for key in ("level", "location", "work_mode"):
        if key not in fields:
            fields[key] = _inferred_field(None)
    return fields


# ── Ripple chain → nested RippleNode ─────────────────────────────────────────

def _chain_list_to_node(chain: list[dict], name_map: dict[str, str]) -> RippleNode:
    """Convert flat chain list (mover is chain[0]) into nested RippleNode tree."""
    if not chain:
        raise ValueError("Empty chain")

    def _build(idx: int) -> RippleNode:
        n = chain[idx]
        pid = n.get("person_id")
        children = [_build(idx + 1)] if idx + 1 < len(chain) else []
        return RippleNode(
            seat=n["seat"],
            person_id=pid,
            display_name=name_map.get(pid) if pid else None,
            status=n["status"],
            reason=n["reason"],
            children=children,
        )

    return _build(0)


# ── Option card fit string ────────────────────────────────────────────────────

def _fit_str(fit_float: float, category: str) -> str:
    if category in ("buy", "relocate"):
        return "Market"
    return f"{int(round(fit_float * 100))}%"


def _mix_fit_str(atoms: list[dict]) -> str:
    fits = sorted(
        {int(round(a["fit"] * 100)) for a in atoms if a.get("fit") and a["type"] != "automate"}
    )
    if not fits:
        return "—"
    if len(fits) == 1:
        return f"{fits[0]}%"
    return f"{fits[0]}-{fits[-1]}%"


# ── Actions list ──────────────────────────────────────────────────────────────

def _make_actions(
    options_result: dict,
    contractor_cards_raw: list[dict],
    sourcing_result: dict,
    ripple_result: dict,
) -> list[dict]:
    actions: list[dict] = []
    top_mixes = options_result.get("top_mixes", [])
    if top_mixes:
        mix = top_mixes[0]
        atoms = mix.get("atoms", [])
        bridge = next((a for a in atoms if a["type"] == "bridge"), None)
        build_atom = next((a for a in atoms if a["type"] == "build"), None)
        if bridge and bridge.get("person_id") and contractor_cards_raw:
            ctr = next((c for c in contractor_cards_raw if c["person_id"] == bridge["person_id"]), None)
            if ctr:
                weeks = 4
                actions.append({"title": f"Extend {ctr['person_id']} contract for 3-month bridge"})
        if build_atom and build_atom.get("person_id"):
            ripple_cands = ripple_result.get("candidates", [])
            rc = next((c for c in ripple_cands if c["person_id"] == build_atom["person_id"]), None)
            if rc:
                wks = rc.get("readiness_weeks", 6)
                actions.append({"title": f"Start {build_atom['person_id']} upskill ({wks} weeks)"})
    pf = sourcing_result.get("past_finalists", {})
    count = pf.get("count", 0) if isinstance(pf, dict) else 0
    if count > 0:
        actions.append({"title": f"Contact {count} past finalists from ATS"})
    return actions or [{"title": "Review options and approve a path forward"}]


# ── Main analysis orchestrator ────────────────────────────────────────────────

def _run_analysis(text: str, today: date) -> AnalysisResult:  # noqa: C901  (long but linear)
    store = _get_store()

    # 1. Regex parse
    fields, needs_llm = regex_parse(
        text, store.reference.skills(), store.reference.skill_aliases()
    )

    # 2. LLM fallback for missing required fields
    if needs_llm:
        llm_result = llm.parse(text)
        if llm_result:
            _merge_llm_fields(fields, llm_result, text, needs_llm)

    # 3. Fill defaults
    _fill_defaults(fields)

    # 4. Title normalization (12 demo titles panel)
    title_norm = title_normalization_panel(
        store.reference.title_aliases(), store.reference.canonical_roles()
    )

    # 5. req_id
    req_id = _make_req_id(text, today)

    # 6. Flat values
    level = str(fields["level"]["value"] or "senior")
    location = str(fields["location"]["value"] or "bengaluru")
    work_mode = str(fields["work_mode"]["value"] or "onsite")
    min_years = int(fields["min_years"]["value"] or 0)
    budget_lpa = float(fields["budget_lpa"]["value"] or 0)
    deadline_days = int(fields["need_by_days"]["value"] or 90)
    skill_ids_all = {s["skill_id"] for s in fields.get("skills", [])}
    must_ids = [s["skill_id"] for s in fields.get("skills", []) if s["importance"] == "must"]
    required_skills = [
        {"id": s["skill_id"], "importance": s["importance"]}
        for s in fields.get("skills", [])
    ]

    # Adapters
    employees_df = store.hris.employees()
    emp_skills = store.hris.employee_skills()
    projects_df = store.hris.projects()
    proj_asgn = store.hris.project_assignments()
    exits_df = store.hris.exits()
    candidates_df = store.ats.candidates()
    cand_skills = store.ats.candidate_skills()
    contractors_df = store.vms.contractors()
    ctr_skills = store.vms.contractor_skills()
    market_stats_df = store.market.market_stats()
    evidence_df = store.evidence.skill_evidence()
    skill_edges_df = store.reference.skill_edges()

    # 7. Deja Req
    deja_parsed = {
        "role": "Full Stack Developer",
        "level": level,
        "skill_ids": set(must_ids),
        "team": "Payments",
    }
    deja_result = dejareq(
        deja_parsed,
        store.ats.requisitions(),
        employees_df,
        emp_skills,
        contractors_df,
        ctr_skills,
        exits_df,
        today=today,
    )

    # 8. Match + build plans for internal candidates (match >= 50)
    match_results: dict[str, dict] = {}
    build_plans: dict[str, dict] = {}
    active_otm = employees_df[
        (employees_df["open_to_move"] == True) & (employees_df["is_active"] == True)  # noqa: E712
    ]
    for _, row in active_otm.iterrows():
        pid = str(row["employee_id"])
        ev = resolve_person(pid, evidence_df, today=today)
        sk = emp_skills.get(pid, set())
        r = score_employee(
            pid, required_skills, ev, sk, skill_edges_df,
            str(row["level"]), level, today=today,
        )
        if r["match"] >= 50:
            match_results[pid] = r
            bp = build_plan(pid, ev, sk, required_skills, skill_edges_df, str(row["level"]), level)
            build_plans[pid] = bp

    # 9. Ripple (top-2 internal)
    ripple_result = analyze_ripple(
        required_skills, level, "Payments", location, work_mode,
        employees_df, emp_skills, evidence_df, skill_edges_df, market_stats_df,
        projects_df, proj_asgn, candidates_df, cand_skills, today=today,
    )

    # 10. Borrow analyses (all contractors)
    borrow_analyses: list[dict] = []
    for _, ctr in contractors_df.iterrows():
        cid = str(ctr["contractor_id"])
        ctr_ev = resolve_person(cid, evidence_df, today=today)
        ctr_sk = ctr_skills.get(cid, set())
        fit_result = score_contractor(
            cid, required_skills, ctr_ev, ctr_sk, skill_edges_df,
            str(ctr["level"]), level,
            date.fromisoformat(str(ctr["start_date"])),
            today=today,
        )
        ba = analyze_contractor(
            cid,
            float(ctr["bill_rate_lpa"]),
            date.fromisoformat(str(ctr["start_date"])),
            date.fromisoformat(str(ctr["end_date"])),
            fit_result["match"],
            proj_asgn,
            projects_df,
            today=today,
        )
        borrow_analyses.append({**ba, "person_id": cid})

    # 11. Automation
    auto_result = estimate_automation(store.reference.automation_tasks())

    # 12. Sourcing
    sourcing_raw = analyze_sourcing(
        sourcing_df=store.ats.sourcing_history(),
        past_finalists_df=store.ats.past_finalists(),
        suppliers_df=store.vms.suppliers(),
        level=level,
        today=today,
    )

    # 13. Location results (compare all 4 locations)
    all_locs = ["remote_india", "hyderabad", "pune", location]
    # deduplicate while preserving order
    seen_locs: set[str] = set()
    unique_locs: list[str] = []
    for loc in all_locs:
        if loc not in seen_locs:
            seen_locs.add(loc)
            unique_locs.append(loc)
    all_locs = unique_locs

    cands_base = candidates_df[candidates_df["years_exp"] >= min_years].copy()
    loc_supplies: dict[str, int] = {}
    for loc in all_locs:
        wm = "remote" if loc == "remote_india" else work_mode
        s, _ = matching_supply(loc, level, wm, must_ids, cands_base, cand_skills)
        loc_supplies[loc] = s

    ms_level = market_stats_df[market_stats_df["level"] == level].copy()
    location_results = compare_locations(all_locs, loc_supplies, ms_level)

    # 14. Market card (base location)
    supply_base = loc_supplies.get(location, 0)
    mstat = store.market.stat(location, level)
    mc = mk_market_card(location, level, supply_base, mstat)

    # 15. Evidence results dict for options scoring
    all_pids = list(match_results.keys()) + [ba["person_id"] for ba in borrow_analyses]
    evidence_results: dict[str, list[dict]] = {}
    for pid in all_pids:
        if pid not in evidence_results:
            evidence_results[pid] = resolve_person(pid, evidence_df, today=today)

    # 16. Options (generate_options)
    options_result = generate_options(
        match_results=match_results,
        build_plans=build_plans,
        borrow_analyses=borrow_analyses,
        market_data=mc,
        location_results=location_results,
        automation_result=auto_result,
        ripple_result=ripple_result,
        dejareq_result=deja_result,
        evidence_results=evidence_results,
        headcount=1,
        deadline_days=deadline_days,
        duration_months=12,
        today=today,
    )

    # 17. Scenario scorer + Redline
    scenario_scorer = make_scenario_scorer(
        match_results=match_results,
        build_plans=build_plans,
        borrow_analyses=borrow_analyses,
        location_results=location_results,
        automation_result=auto_result,
        ripple_result=ripple_result,
        dejareq_result=deja_result,
        evidence_results=evidence_results,
        base_location=location,
        base_must_skill_ids=must_ids,
        deadline_days=deadline_days,
        duration_months=12,
    )
    redline_result = analyze_redline(
        fields, text,
        candidates_df, cand_skills,
        employees_df, emp_skills,
        contractors_df, ctr_skills,
        skill_edges_df, market_stats_df,
        deja_result, scenario_scorer,
        today=today,
    )

    # 18. Internal candidates list (sorted by match desc)
    internal_candidates_raw: list[dict] = []
    name_map = store.display_names(list(match_results.keys()) + [ba["person_id"] for ba in borrow_analyses])
    for pid, r in match_results.items():
        emp_row = employees_df[employees_df["employee_id"] == pid]
        if emp_row.empty:
            continue
        bp = build_plans.get(pid, {})
        internal_candidates_raw.append({
            "person_id": pid,
            "display_name": name_map.get(pid, pid),
            "match": float(r["match"]),
            "band": r["band"],
            "readiness_weeks": bp.get("readiness_weeks", 0),
            "build_cost_lpa": bp.get("build_cost_lpa", 0.0),
            "evidence_ids": r["evidence_ids"],
        })
    internal_candidates_raw.sort(key=lambda x: -x["match"])

    # 19. Contractor cards raw (with extend_cost_3m for brief)
    contractor_cards_raw: list[dict] = []
    for ba in borrow_analyses:
        cid = ba["person_id"]
        contractor_cards_raw.append({
            "person_id": cid,
            "display_name": name_map.get(cid, cid),
            "fit": float(ba["fit"]),
            "availability": ba["availability"],
            "extend_cost_lpa": ba["extend_cost_12m"],
            "extend_cost_3m": ba["extend_cost_3m"],
            "convert_saving_lpa": None,
            "conversion_signal": ba["conversion_signal"],
            "compliance_flag": ba["compliance_flag"],
            "evidence_ids": [cid],
        })

    # 20. Data quality (all shortlisted evidence)
    all_ev_scores: list[dict] = []
    for pid in all_pids:
        all_ev_scores.extend(evidence_results.get(pid, []))
    dq = ev_data_quality(all_ev_scores)

    # 21. Brief
    ref_meta = store.reference.reference()
    actions_list = _make_actions(options_result, contractor_cards_raw, sourcing_raw, ripple_result)
    brief_result = generate_brief(
        raw_text=text,
        parsed_req=fields,
        dejareq_result=deja_result,
        redline_result=redline_result,
        ripple_result=ripple_result,
        options_result=options_result,
        sourcing_result=sourcing_raw,
        market_card=mc,
        relocate_card=location_results,
        contractor_cards=contractor_cards_raw,
        internal_candidates=internal_candidates_raw,
        evidence_quality=dq,
        actions_list=actions_list,
        decision_rows=[],
        reference_meta=ref_meta,
    )

    # 22. Tokens
    tokens_snap = llm.get_meter().snapshot()

    # 23. Persist to DB
    db = Database()
    try:
        db.save_requisition(
            req_id, "Full Stack Developer", level, location, work_mode,
            json.dumps(fields, default=str),
        )
        constraints_for_db = [
            {"kind": c["kind"], "value": str(c["value"]) if c["value"] is not None else "", "source": c["source"]}
            for c in redline_result.get("constraints", [])
        ]
        db.save_constraints(req_id, constraints_for_db)
        db.save_skills(req_id, fields.get("skills", []))
        for mask, scenario in redline_result.get("scenarios", {}).items():
            db.save_scenario(req_id, mask, json.dumps(scenario, default=str))
    finally:
        db.close()

    # 24. Build API response
    return _build_analysis_result(
        req_id=req_id,
        fields=fields,
        title_norm=title_norm,
        deja_result=deja_result,
        redline_result=redline_result,
        ripple_result=ripple_result,
        options_result=options_result,
        sourcing_raw=sourcing_raw,
        location_results=location_results,
        mc=mc,
        contractor_cards_raw=contractor_cards_raw,
        internal_candidates_raw=internal_candidates_raw,
        dq=dq,
        brief_result=brief_result,
        tokens_snap=tokens_snap,
        name_map=name_map,
        base_location=location,
        store=store,
    )


# ── Response builder ──────────────────────────────────────────────────────────

def _build_analysis_result(  # noqa: C901
    *,
    req_id: str,
    fields: dict,
    title_norm: dict,
    deja_result: dict,
    redline_result: dict,
    ripple_result: dict,
    options_result: dict,
    sourcing_raw: dict,
    location_results: list[dict],
    mc: dict,
    contractor_cards_raw: list[dict],
    internal_candidates_raw: list[dict],
    dq: dict,
    brief_result: dict,
    tokens_snap: dict,
    name_map: dict[str, str],
    base_location: str,
    store: DataStore,
) -> AnalysisResult:

    # ── parsed ──────────────────────────────────────────────────────────────
    def _pf(key: str) -> ParsedField:
        d = fields.get(key, _inferred_field())
        return ParsedField(
            value=d.get("value"),
            span=d.get("span"),
            span_start=d.get("span_start"),
            span_end=d.get("span_end"),
            label=d.get("label", "inferred"),
        )

    parsed_skills = [
        ParsedSkill(skill_id=s["skill_id"], importance=s["importance"],
                    confidence=float(s.get("confidence", 1.0)))
        for s in fields.get("skills", [])
    ]

    mappings = [
        TitleMapping(
            raw_title=m["raw_title"],
            source_system=m["source_system"],
            role=m["role"],
            level=m.get("level"),
            method=m["method"],
            confidence=float(m["confidence"]),
            esco_uri=m.get("esco_uri"),
            onet_code=m.get("onet_code"),
        )
        for m in title_norm.get("mappings", [])
    ]
    tn = TitleNormalization(
        raw_titles_count=title_norm["raw_titles_count"],
        role=title_norm["role"],
        levels=title_norm.get("levels", []),
        mappings=mappings,
    )

    parsed = ParsedRequisition(
        req_id=req_id,
        level=_pf("level"),
        headcount=_pf("headcount"),
        location=_pf("location"),
        work_mode=_pf("work_mode"),
        min_years=_pf("min_years"),
        budget_lpa=_pf("budget_lpa"),
        need_by_days=_pf("need_by_days"),
        duration_months=_pf("duration_months"),
        criticality=_pf("criticality"),
        skills=parsed_skills,
        title_normalization=tn,
    )

    # ── dejareq ─────────────────────────────────────────────────────────────
    mc_deja = deja_result.get("match_count", 0)
    if mc_deja < 2:
        dejareq_obj = DejaReq(
            match_count=mc_deja,
            banner_text=deja_result.get("banner"),
            chip=deja_result.get("chip"),
            timeline=[],
            averages_by_decision=[],
            patterns=[],
            insight_text=None,
        )
    else:
        timeline_entries = []
        for t in deja_result.get("timeline", []):
            timeline_entries.append(TimelineEntry(
                req_id=t["req_id"],
                opened=str(t["opened_date"])[:7],  # YYYY-MM
                decision=t["decision"],
                time_to_fill_days=t.get("time_to_fill_days"),
                ramp_note=None,
                first_year_cost_lpa=float(t["first_year_cost_lpa"]),
                outcome_text=t["outcome"],
                evidence_ids=t.get("evidence_ids", []),
            ))

        avgs_by_dec = []
        for dec, avg in deja_result.get("averages", {}).items():
            avgs_by_dec.append(AverageByDecision(
                decision=dec,
                count=avg["count"],
                avg_tenure_months=avg.get("avg_tenure_months"),
                avg_cost_lpa=float(avg["avg_cost_lpa"]),
                avg_time_to_fill_days=float(avg.get("avg_ttf_days", 0)),
            ))

        patterns_raw = deja_result.get("patterns", {})
        risk_adj = deja_result.get("risk_adjustments", [])
        patterns = []
        churn = patterns_raw.get("churn", False)
        kl = patterns_raw.get("knowledge_loss", False)
        ww = patterns_raw.get("what_worked")
        if churn:
            ra = next((r for r in risk_adj if r["option"] == "buy"), {})
            patterns.append(Pattern(
                name="churn",
                fired=True,
                text=ra.get("reason", "Churn pattern detected"),
                risk_option="buy",
                risk_penalty=float(ra.get("delta", 0.20)),
            ))
        if kl:
            ra = next((r for r in risk_adj if r["option"] == "borrow"), {})
            patterns.append(Pattern(
                name="knowledge_loss",
                fired=True,
                text=ra.get("reason", "Knowledge loss pattern detected"),
                risk_option="borrow",
                risk_penalty=float(ra.get("delta", 0.10)),
            ))
        if ww:
            patterns.append(Pattern(
                name="what_worked",
                fired=True,
                text=f"The {ww} is still in role.",
                risk_option=None,
                risk_penalty=0.0,
            ))

        dejareq_obj = DejaReq(
            match_count=mc_deja,
            banner_text=deja_result.get("banner"),
            chip=None,
            timeline=timeline_entries,
            averages_by_decision=avgs_by_dec,
            patterns=patterns,
            insight_text=deja_result.get("insight"),
        )

    # ── redline ──────────────────────────────────────────────────────────────
    constraints_out: list[Constraint] = []
    for c in redline_result.get("constraints", []):
        constraints_out.append(Constraint(
            id=c["id"],
            kind=c["kind"],
            value=str(c["value"]),
            phrase=c["phrase"],
            span_start=c["span_start"],
            span_end=c["span_end"],
            source=c["source"],
            severity=c["severity"],
            hover_text=c["hover_text"],
            cost=ConstraintCost(
                supply_delta=c["cost"].get("supply_delta"),
                days_delta=c["cost"].get("days_delta"),
                rupees_delta_lpa=c["cost"].get("rupees_delta_lpa"),
            ),
            relaxed_value=c.get("relaxed_value"),
        ))

    scenarios_out: dict[str, ScenarioResult] = {}
    for mask, scen in redline_result.get("scenarios", {}).items():
        opts = [
            OptionSummary(
                option_id=o["option_id"],
                name=o["name"],
                score=float(o["score"]) if o.get("score") is not None else None,
                ready_by_p80_days=o.get("ready_by_p80_days"),
                year_one_cost_lpa=o.get("year_one_cost_lpa"),
                panel_line=o["panel_line"],
            )
            for o in scen.get("options", [])
        ]
        scenarios_out[mask] = ScenarioResult(
            top_option_id=scen["top_option_id"],
            panel_text=scen["panel_text"],
            options=opts,
        )

    redline_obj = Redline(
        constraints=constraints_out,
        constraint_order=redline_result.get("constraint_order", []),
        scenarios=scenarios_out,
    )

    # ── ripple ───────────────────────────────────────────────────────────────
    ripple_cands: list[RippleCandidate] = []
    for cand in ripple_result.get("candidates", []):
        pid = cand["person_id"]
        chain_list = cand["chain"]
        try:
            chain_node = _chain_list_to_node(chain_list, name_map)
        except (ValueError, IndexError):
            continue
        ni = cand.get("net_impact") or {}
        ripple_cands.append(RippleCandidate(
            person_id=pid,
            display_name=name_map.get(pid, pid),
            match=float(cand["match"]),
            chain=chain_node,
            net_impact=NetImpact(
                days_to_fill_last_gap=cand.get("net_days_to_fill"),
                total_cost_lpa=float(cand.get("net_cost_lpa", 0)),
                promotions=cand.get("promotions", 0),
                red_flags=cand.get("red_flags", 0),
            ),
        ))
    ripple_obj = Ripple(candidates=ripple_cands)

    # ── options ──────────────────────────────────────────────────────────────

    # Build engine option cards dict keyed by category
    engine_opts: dict[str, dict] = {}
    for o in options_result.get("options", []):
        cat = o.get("option_id", "")
        engine_opts[cat] = o

    top_mixes = options_result.get("top_mixes", [])

    # Build five OptionCards: [mix, borrow, build, relocate, buy]
    five: list[OptionCard] = []

    # Mix card from top_mixes[0]
    if top_mixes:
        mx = top_mixes[0]
        atoms_raw = mx.get("atoms", [])
        mix_fit = _mix_fit_str(atoms_raw)
        mix_risk_raw = float(mx.get("risk", 0.10))
        from backend.engine.options import _risk_label
        five.append(OptionCard(
            id="mix",
            name="Recommended mix",
            what_it_means=" + ".join(
                name_map.get(a["person_id"], a["person_id"])
                if a.get("person_id") else a.get("location", a["type"])
                for a in atoms_raw if a["type"] != "automate"
            ) or "Recommended mix",
            ready_by_p80_days=mx.get("ready_by_p80_days", 0),
            year_one_cost_lpa=float(mx.get("cost_lpa", 0)),
            fit=mix_fit,
            risk_label=_risk_label(mix_risk_raw),
            risk_value=round(mix_risk_raw, 2),
            score=float(mx["score"]),
            reason="Recommended mix combining bridge and build options",
            evidence_ids=mx.get("evidence_ids", []),
        ))
    elif engine_opts.get("borrow"):
        # Fallback: no mix, use borrow as first
        pass  # will still add borrow below

    # Standard option cards
    for cat in ("borrow", "build", "relocate", "buy"):
        o = engine_opts.get(cat)
        if o is None:
            continue
        fit_val = o.get("fit", 0)
        five.append(OptionCard(
            id=cat,
            name=o.get("name", cat.title()),
            what_it_means=o.get("what_it_means", ""),
            ready_by_p80_days=o.get("ready_by_p80_days"),
            year_one_cost_lpa=o.get("year_one_cost_lpa"),
            fit=_fit_str(float(fit_val) if isinstance(fit_val, (int, float)) else 0.0, cat),
            risk_label=o.get("risk_label", "Medium"),
            risk_value=round(float(o.get("risk_raw", 0.3)), 2),
            score=float(o["score"]) if isinstance(o.get("score"), (int, float)) else None,
            reason=o.get("one_line_reason", ""),
            evidence_ids=o.get("evidence_ids", []),
        ))

    # MixOption list from top_mixes
    mixes_out: list[MixOption] = []
    for i, mx in enumerate(top_mixes):
        atoms_raw = mx.get("atoms", [])
        atom_strs = [
            f"{a['type']}-{a['person_id'] or a.get('location', '')}"
            for a in atoms_raw
        ]
        mixes_out.append(MixOption(
            id=mx.get("mix_id", f"mix-{i+1}"),
            name=" + ".join(
                name_map.get(a["person_id"], a.get("person_id", ""))
                if a.get("person_id") else a.get("type", "")
                for a in atoms_raw if a["type"] != "automate"
            ) or mx.get("mix_id", f"mix-{i+1}"),
            atoms=atom_strs,
            score=float(mx["score"]),
            ready_by_p80_days=int(mx.get("ready_by_p80_days", 0)),
            year_one_cost_lpa=float(mx.get("cost_lpa", 0)),
            reason="Bridge-then-build strategy" if i == 0 else "Alternative mix",
        ))

    # Relocate card (convert IDs to display names, sort by score desc already done)
    relocate_card_out = [
        RelocateRow(
            location=_loc_display(r["location"], base_location),
            supply=r["supply"],
            ttf_p50=r["ttf_p50"],
            ttf_p80=r["ttf_p80"],
            pay_p50_lpa=float(r["pay_p50_lpa"]),
            score=float(r["score"]),
        )
        for r in location_results
    ]
    # Sort by score descending
    relocate_card_out.sort(key=lambda r: -r.score)

    # Market card
    market_card_out = MarketCard(
        location=mc["location"],
        level=mc["level"],
        supply=mc["supply"],
        demand=mc["demand"],
        sal_p25=float(mc["sal_p25"]),
        sal_p50=float(mc["sal_p50"]),
        sal_p75=float(mc["sal_p75"]),
        ttf_p50=int(mc["ttf_p50"]),
        ttf_p80=int(mc["ttf_p80"]),
    )

    # Contractor cards (schema-compliant, drop extend_cost_3m)
    contractor_cards_out = [
        ContractorCard(
            person_id=cc["person_id"],
            display_name=cc["display_name"],
            fit=float(cc["fit"]),
            availability=cc["availability"],
            extend_cost_lpa=float(cc["extend_cost_lpa"]),
            convert_saving_lpa=cc.get("convert_saving_lpa"),
            conversion_signal=bool(cc["conversion_signal"]),
            compliance_flag=bool(cc["compliance_flag"]),
            evidence_ids=cc.get("evidence_ids", []),
        )
        for cc in contractor_cards_raw
    ]

    # Internal candidates
    internal_candidates_out = [
        InternalCandidate(
            person_id=ic["person_id"],
            display_name=ic["display_name"],
            match=float(ic["match"]),
            band=ic["band"],
            readiness_weeks=ic.get("readiness_weeks"),
            build_cost_lpa=ic.get("build_cost_lpa"),
            evidence_ids=ic.get("evidence_ids", []),
        )
        for ic in internal_candidates_raw
    ]

    # Sourcing
    channels_out = [
        SourcingChannel(
            rank=ch.get("rank"),
            channel=ch["channel"],
            evidence=ch.get("evidence", ""),
            use_for=ch.get("use_for", ""),
        )
        for ch in sourcing_raw.get("channels", [])
    ]

    # Past finalists: look up actual rows from ATS
    pf_info = sourcing_raw.get("past_finalists", {})
    pf_ids = pf_info.get("ids", []) if isinstance(pf_info, dict) else []
    finalists_df = store.ats.past_finalists()
    past_finalists_out: list[PastFinalist] = []
    for fid in pf_ids:
        row = finalists_df[finalists_df["candidate_id"] == fid]
        if row.empty:
            continue
        r = row.iloc[0]
        past_finalists_out.append(PastFinalist(
            candidate_id=str(r["candidate_id"]),
            stage_reached=str(r["stage_reached"]),
            outcome=str(r["outcome"]),
            decided_on=str(r["decided_on"]),
            open_to_remote=bool(r["open_to_remote"]),
        ))

    suppliers_out = [
        SupplierRanking(
            supplier_id=s["supplier_id"],
            name=s["name"],
            fill_rate=float(s["fill_rate"]),
            median_days_to_submit=int(s["median_days_to_submit"]),
            avg_bill_rate=float(s["avg_bill_rate_lpa"]),
        )
        for s in sourcing_raw.get("suppliers", [])
    ]

    sourcing_obj = Sourcing(
        channels=channels_out,
        past_finalists=past_finalists_out,
        suppliers=suppliers_out,
    )

    # Decision boundaries from redline assumption_ledger
    decision_boundaries = (
        redline_result.get("assumption_ledger", {}).get("decision_boundaries", [])
    )

    weights_used = options_result.get("weights_used", {})
    weights_obj = OptionWeights(
        speed=float(weights_used.get("speed", 0.30)),
        cost=float(weights_used.get("cost", 0.25)),
        fit=float(weights_used.get("fit", 0.20)),
        risk=float(weights_used.get("risk", 0.15)),
        strategic=float(weights_used.get("strategic", 0.10)),
    )

    options_obj = Options(
        five=five,
        mixes=mixes_out,
        relocate_card=relocate_card_out,
        market_card=market_card_out,
        contractor_cards=contractor_cards_out,
        internal_candidates=internal_candidates_out,
        sourcing=sourcing_obj,
        decision_boundaries=decision_boundaries,
        weights=weights_obj,
    )

    # ── brief ────────────────────────────────────────────────────────────────
    brief_sections = [
        BriefSection(key=s["key"], title=s["title"], markdown=s["markdown"])
        for s in brief_result.get("sections", [])
    ]
    brief_obj = Brief(
        sections=brief_sections,
        markdown=brief_result.get("markdown", ""),
        html=brief_result.get("html", ""),
    )

    # ── data quality ─────────────────────────────────────────────────────────
    dq_obj = DataQuality(
        conflicts=dq["conflicts"],
        stale=dq["stale"],
        self_report_only=dq["self_report_only"],
        line=dq["line"],
    )

    # ── tokens ───────────────────────────────────────────────────────────────
    tokens_obj = Tokens(
        calls=tokens_snap["calls"],
        input_tokens=tokens_snap["input_tokens"],
        output_tokens=tokens_snap["output_tokens"],
        cache_hit=bool(tokens_snap["cache_hit"]),
        est_cost=float(tokens_snap["est_cost"]),
    )

    return AnalysisResult(
        parsed=parsed,
        dejareq=dejareq_obj,
        redline=redline_obj,
        ripple=ripple_obj,
        options=options_obj,
        brief=brief_obj,
        data_quality=dq_obj,
        tokens=tokens_obj,
    )


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/api/health", response_model=Health)
def health() -> Health:
    cache_dir = Path(__file__).resolve().parent.parent / "cache"
    return Health(
        ok=True,
        cache_loaded=(cache_dir / "reference.json").exists(),
        llm_configured=bool(settings.gemini_api_key),
    )


@app.post("/api/analyze", response_model=AnalysisResult)
def analyze(req: AnalyzeRequest, stub: bool = Query(default=False)) -> AnalysisResult:
    if stub:
        return AnalysisResult.model_validate(_load_stub())
    return _run_analysis(req.text, settings.demo_today)


_VALID_OPTIONS = ["mix", "build", "borrow", "relocate", "buy",
                  "mix-1", "mix-2", "mix-3", "automate"]


@app.post("/api/decisions", status_code=201)
def create_decision(req: DecisionRequest) -> dict:
    db = Database()
    try:
        req_row = db.get_requisition(req.req_id)
        if req_row is None:
            raise HTTPException(status_code=400,
                                detail=f"Requisition {req.req_id} not found")

        parsed_json = json.loads(req_row["raw_json"])

        scenarios = db.get_scenarios(req.req_id)
        scenario_row = next(
            (s for s in scenarios if s["relaxed_mask"] == req.relaxed_mask),
            None,
        )
        options_json = (
            json.loads(scenario_row["outputs_json"]) if scenario_row else {}
        )

        result = record_decision(
            db=db,
            req_id=req.req_id,
            option_id=req.option_id,
            verb=req.verb.value,
            relaxed_mask=req.relaxed_mask,
            decided_by=req.decided_by,
            reason=req.reason,
            valid_options=_VALID_OPTIONS,
            parsed_json=parsed_json,
            options_json=options_json,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()


@app.get("/api/people/{person_id}/skills", response_model=list[SkillScore])
def person_skills(person_id: str) -> list[SkillScore]:
    store = _get_store()
    emp_ids = set(store.hris._employees["employee_id"].astype(str))
    ctr_ids = set(store.vms._contractors["contractor_id"].astype(str))
    if person_id not in emp_ids and person_id not in ctr_ids:
        raise HTTPException(status_code=404, detail=f"Person {person_id} not found")
    ev_df = store.evidence.skill_evidence(person_id)
    scores = resolve_person(person_id, ev_df, today=settings.demo_today)
    return [
        SkillScore(
            skill=s["skill"],
            value=float(s["value"]),
            source=s["source"],
            observed_on=s["observed_on"],
            confidence=float(s["confidence"]),
            stale=bool(s["stale"]),
            conflict=bool(s["conflict"]),
            tooltip=s["tooltip"],
            ignored=[
                {"source": ig["source"], "value": float(ig["value"]), "reason": ig["reason"]}
                for ig in s.get("ignored", [])
            ],
        )
        for s in scores
    ]


# ── SPA fallback ──────────────────────────────────────────────────────────────

_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"

if _DIST.is_dir():
    @app.get("/{full_path:path}")
    async def spa_fallback(full_path: str) -> FileResponse:
        file = _DIST / full_path
        if file.is_file():
            return FileResponse(file)
        return FileResponse(_DIST / "index.html")

    app.mount("/", StaticFiles(directory=str(_DIST), html=True), name="frontend")
