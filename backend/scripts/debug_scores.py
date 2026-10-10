"""Step B diagnostic: computed scores vs Section 7A targets."""
from __future__ import annotations
from datetime import date
from backend.data.seed import main as seed_main
from backend.store import DataStore
from backend.engine.match import score_employee, score_contractor
from backend.engine.evidence import resolve_person
from backend.engine.build import build_plan
from backend.engine.borrow import analyze_contractor
from backend.engine.market import matching_supply, market_card
from backend.engine.location import compare_locations
from backend.engine.automate import estimate_automation
from backend.engine.ripple import analyze_ripple
from backend.engine.dejareq import dejareq
from backend.engine.options import generate_options, _generate_atoms, _dejareq_delta

TODAY = date(2026, 10, 8)
SENIOR_SKILLS = [
    {"id": "react", "importance": "must"},
    {"id": "nodejs", "importance": "must"},
    {"id": "kubernetes", "importance": "must"},
    {"id": "typescript", "importance": "nice"},
    {"id": "docker", "importance": "nice"},
    {"id": "javascript", "importance": "nice"},
    {"id": "rest_apis", "importance": "nice"},
    {"id": "postgresql", "importance": "nice"},
]

DEMO_PARSED_REQ = {
    "role": "Full Stack Developer",
    "level": "senior",
    "location": "bengaluru",
    "work_mode": "onsite",
    "team": "Payments",
    "skill_ids": ["react", "nodejs", "kubernetes", "typescript",
                  "docker", "javascript", "rest_apis", "postgresql"],
}

seed_main()
store = DataStore()

employees_df = store.hris.employees()
emp_skills = store.hris.employee_skills()
evidence_df = store.evidence.skill_evidence()
skill_edges = store.reference.skill_edges()
market_stats = store.market.market_stats()
projects_df = store.hris.projects()
proj_assign = store.hris.project_assignments()
candidates_df = store.ats.candidates()
candidate_skills = store.ats.candidate_skills()
contractors_df = store.vms.contractors()
ctr_skills = store.vms.contractor_skills()

match_results: dict[str, dict] = {}
build_plans: dict[str, dict] = {}
evidence_results: dict[str, list[dict]] = {}

mask = (employees_df["open_to_move"] == True) & (employees_df["is_active"] == True)
for _, row in employees_df[mask].iterrows():
    pid = str(row["employee_id"])
    ev = resolve_person(pid, evidence_df, today=TODAY)
    sk = emp_skills.get(pid, set())
    m = score_employee(pid, SENIOR_SKILLS, ev, sk, skill_edges,
                       str(row["level"]), "senior", today=TODAY)
    if m["match"] >= 70:
        match_results[pid] = m
        build_plans[pid] = build_plan(pid, ev, sk, SENIOR_SKILLS, skill_edges,
                                      str(row["level"]), "senior")
        evidence_results[pid] = ev

borrow_analyses: list[dict] = []
for _, row in contractors_df.iterrows():
    cid = str(row["contractor_id"])
    ev = resolve_person(cid, evidence_df, today=TODAY)
    sk = ctr_skills.get(cid, set())
    cm = score_contractor(cid, SENIOR_SKILLS, ev, sk, skill_edges,
                          str(row["level"]), "senior",
                          start_date=date.fromisoformat(str(row["start_date"])),
                          today=TODAY)
    if cm["match"] >= 70:
        sd = date.fromisoformat(str(row["start_date"]))
        ed = date.fromisoformat(str(row["end_date"]))
        ba = analyze_contractor(cid, float(row["bill_rate_lpa"]), sd, ed,
                                cm["match"], proj_assign, projects_df, today=TODAY)
        borrow_analyses.append(ba)
        evidence_results[cid] = ev

supply, _ = matching_supply("bengaluru", "senior", "onsite",
    [s["id"] for s in SENIOR_SKILLS if s["importance"] == "must"],
    candidates_df, candidate_skills)
mstat = store.market.stat("bengaluru", "senior")
mcard = market_card("bengaluru", "senior", supply, mstat)

locations = ["bengaluru", "hyderabad", "pune", "remote_india"]
supplies: dict[str, int] = {}
for loc in locations:
    s, _ = matching_supply(loc, "senior",
        "remote" if loc == "remote_india" else "onsite",
        [sk["id"] for sk in SENIOR_SKILLS if sk["importance"] == "must"],
        candidates_df, candidate_skills)
    supplies[loc] = s

loc_stats = market_stats[market_stats["level"] == "senior"]
loc_results = compare_locations(locations, supplies, loc_stats)

automation_result = estimate_automation(store.reference.automation_tasks())

ripple_result = analyze_ripple(
    required_skills=SENIOR_SKILLS, required_level="senior",
    required_team="Payments", required_location="bengaluru",
    required_work_mode="onsite", employees_df=employees_df,
    emp_skills=emp_skills, evidence_df=evidence_df,
    skill_edges_df=skill_edges, market_stats_df=market_stats,
    projects_df=projects_df, project_assignments=proj_assign,
    candidates_df=candidates_df, candidate_skills=candidate_skills,
    today=TODAY)

reqs = store.ats.requisitions()
exits = store.hris.exits()
dejareq_result = dejareq(
    parsed_req=DEMO_PARSED_REQ, past_reqs=reqs,
    employees=employees_df, emp_skills=emp_skills,
    contractors=contractors_df, ctr_skills=ctr_skills,
    exits=exits, today=TODAY)

result = generate_options(
    match_results=match_results, build_plans=build_plans,
    borrow_analyses=borrow_analyses, market_data=mcard,
    location_results=loc_results, automation_result=automation_result,
    ripple_result=ripple_result, dejareq_result=dejareq_result,
    evidence_results=evidence_results,
    headcount=1, deadline_days=30, duration_months=12, today=TODAY)

print("=" * 90)
print(f"{'Option':<12} {'Score':>6} {'Target':>7} {'P80':>5} {'Cost':>7} {'Fit':>6} {'Risk':<13}")
print("-" * 90)
targets = {"Build": 78, "Buy": 41, "Borrow": 71, "Relocate": 64, "Mix": 84}
for opt in result["options"]:
    name = opt["name"]
    t = targets.get(name, "")
    print(f"{name:<12} {str(opt['score']):>6} {str(t):>7} "
          f"{opt['ready_by_p80_days']:>4}d {opt['year_one_cost_lpa']:>6.1f}L "
          f"{opt['fit']:>5.2f} {opt['risk_label']:<13}")

print()
print("Top 3 mixes:")
for mx in result["top_mixes"]:
    atoms_str = "+".join(f"{a['type']}({a.get('person_id') or a.get('location','')})"
                         for a in mx["atoms"])
    print(f"  {atoms_str:50s} score={mx['score']} speed={mx['speed']:.2f} "
          f"cost={mx['cost']:.2f} fit={mx['fit']:.2f} risk={mx['risk']:.2f} "
          f"strat={mx['strategic']:.2f}")

print()
w = result["weights_used"]
print(f"Weights: speed={w['speed']:.4f} cost={w['cost']:.4f} "
      f"fit={w['fit']:.4f} risk={w['risk']:.4f} strategic={w['strategic']:.4f}")

print()
print("Dejareq adjustments:", dejareq_result.get("risk_adjustments", []))
print("Dejareq delta for buy:", _dejareq_delta(dejareq_result, "buy"))
print("Dejareq delta for relocate:", _dejareq_delta(dejareq_result, "relocate"))
print("Dejareq delta for borrow:", _dejareq_delta(dejareq_result, "borrow"))
print("Dejareq delta for build:", _dejareq_delta(dejareq_result, "build"))

print()
print("Self-report:", ", ".join(
    f"{e['person_id']} {e['skill']} +{e['risk_delta']:.2f}"
    for e in result["assumption_ledger"]["self_report_risks"]))

print()
print("Ripple candidates:")
for c in ripple_result["candidates"]:
    print(f"  {c['person_id']} match={c['match']} weeks={c['readiness_weeks']} "
          f"net_cost={c['net_cost_lpa']:.1f} red_flags={c['red_flags']}")

print()
print("Borrow analyses:")
for ba in borrow_analyses:
    print(f"  {ba['person_id']} fit={ba['fit']} 12m={ba['extend_cost_12m']:.1f} "
          f"3m={ba['extend_cost_3m']:.1f} compliance={ba['compliance_flag']}")

print()
print("Atoms generated:")
atoms = _generate_atoms(match_results, build_plans, borrow_analyses,
                        loc_results, automation_result, mcard,
                        ripple_result=ripple_result)
for a in atoms:
    print(f"  {a['type']:10s} {str(a.get('person_id') or a.get('location','')):>14} "
          f"days={a['days']:>3} cost={a['cost_lpa']:>6.1f} "
          f"fit={a['fit']:.2f} rf={a['red_flags']}")
