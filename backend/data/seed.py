"""
seed.py — Deterministic synthetic data generator for TalentLens.

Generates all backend/data/*.csv files using Faker + NumPy with seed 42.
Run: python -m backend.data.seed

Every CSV is regenerated from scratch on each run; output is deterministic.
"""
from __future__ import annotations

import csv
from datetime import date, timedelta
from pathlib import Path

import numpy as np
from faker import Faker

SEED = 42
DATA_DIR = Path(__file__).parent
TODAY = date(2026, 10, 8)

ALL_SKILLS = [
    "react", "nodejs", "kubernetes", "aws", "graphql", "terraform", "docker",
    "typescript", "javascript", "nextjs", "express", "postgresql", "mongodb",
    "redis", "rest_apis", "git", "ci_cd", "jest", "html_css", "python",
    "java", "kafka", "linux", "microservices", "system_design", "angular",
    "vue", "azure", "gcp", "sql",
]

TEAMS = ["Payments", "Checkout", "Platform", "Growth", "Infra", "Mobile", "Data"]


# ═══════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════

def _write(name: str, rows: list[dict], fields: list[str],
           output_dir: Path = DATA_DIR) -> None:
    with open(output_dir / name, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def _d(d: date) -> str:
    return d.isoformat()


# ═══════════════════════════════════════════════════════════════════════
# Named Characters (demo story — IDs are fixed, never change)
# ═══════════════════════════════════════════════════════════════════════

_EMP_FIELDS = [
    "employee_id", "display_name", "level", "team", "location",
    "work_mode", "hire_date", "years_exp", "open_to_move", "is_active",
    "rating",
]

NAMED_EMPLOYEES = [
    {"employee_id": "E-010", "display_name": "Vikram", "level": "senior",
     "team": "Payments", "location": "bengaluru", "work_mode": "onsite",
     "hire_date": _d(date(2022, 1, 15)), "years_exp": 5.5,
     "open_to_move": "false", "is_active": "true", "rating": 5},
    {"employee_id": "E-018", "display_name": "Anil", "level": "senior",
     "team": "Payments", "location": "bengaluru", "work_mode": "onsite",
     "hire_date": _d(date(2025, 1, 18)), "years_exp": 5.0,
     "open_to_move": "false", "is_active": "false", "rating": 3},
    {"employee_id": "E-020", "display_name": "Deepak", "level": "senior",
     "team": "Payments", "location": "bengaluru", "work_mode": "onsite",
     "hire_date": _d(date(2025, 12, 20)), "years_exp": 5.5,
     "open_to_move": "false", "is_active": "false", "rating": 3},
    {"employee_id": "E-031", "display_name": "Karthik", "level": "lead",
     "team": "Platform", "location": "bengaluru", "work_mode": "onsite",
     "hire_date": _d(date(2019, 7, 1)), "years_exp": 7.2,
     "open_to_move": "true", "is_active": "true", "rating": 5},
    {"employee_id": "E-038", "display_name": "Sneha", "level": "mid",
     "team": "Growth", "location": "bengaluru", "work_mode": "onsite",
     "hire_date": _d(date(2023, 3, 1)), "years_exp": 3.5,
     "open_to_move": "true", "is_active": "true", "rating": 4},
    {"employee_id": "E-045", "display_name": "Priya", "level": "mid",
     "team": "Checkout", "location": "bengaluru", "work_mode": "onsite",
     "hire_date": _d(date(2022, 9, 1)), "years_exp": 4.0,
     "open_to_move": "true", "is_active": "true", "rating": 4},
    {"employee_id": "E-052", "display_name": "Ananya", "level": "mid",
     "team": "Data", "location": "bengaluru", "work_mode": "onsite",
     "hire_date": _d(date(2023, 1, 15)), "years_exp": 3.7,
     "open_to_move": "true", "is_active": "true", "rating": 3},
    {"employee_id": "E-072", "display_name": "Rahul", "level": "junior",
     "team": "Checkout", "location": "bengaluru", "work_mode": "onsite",
     "hire_date": _d(date(2025, 3, 1)), "years_exp": 1.5,
     "open_to_move": "true", "is_active": "true", "rating": 3},
]

NAMED_EMP_SKILLS: dict[str, list[str]] = {
    "E-010": ["react", "nodejs", "kubernetes", "typescript", "javascript",
              "docker", "aws", "rest_apis", "postgresql", "git", "ci_cd"],
    "E-018": ["react", "nodejs", "kubernetes", "typescript", "javascript",
              "docker", "git"],
    "E-020": ["react", "nodejs", "kubernetes", "typescript", "javascript",
              "docker", "aws", "git", "ci_cd"],
    "E-031": ["react", "nodejs", "kubernetes", "terraform", "typescript",
              "javascript", "docker", "aws", "system_design", "microservices",
              "git", "ci_cd", "postgresql", "rest_apis", "linux", "python"],
    "E-038": ["react", "nodejs", "typescript", "javascript", "docker",
              "git", "ci_cd", "postgresql", "rest_apis", "jest"],
    "E-045": ["react", "nodejs", "typescript", "javascript", "docker",
              "html_css", "git", "ci_cd", "postgresql", "rest_apis", "jest"],
    "E-052": ["react", "nodejs", "typescript", "javascript", "docker",
              "html_css", "git", "postgresql", "rest_apis"],
    "E-072": ["react", "nodejs", "javascript", "html_css", "git", "jest"],
}

_CTR_FIELDS = [
    "contractor_id", "display_name", "supplier_id", "level", "location",
    "work_mode", "start_date", "end_date", "bill_rate_lpa",
]

NAMED_CONTRACTORS = [
    {"contractor_id": "C-17", "display_name": "Arjun",
     "supplier_id": "SUP-01", "level": "senior",
     "location": "bengaluru", "work_mode": "onsite",
     "start_date": _d(date(2025, 7, 1)),
     "end_date": _d(date(2026, 11, 5)),
     "bill_rate_lpa": 24.0},
    {"contractor_id": "C-09", "display_name": "Suresh",
     "supplier_id": "SUP-01", "level": "senior",
     "location": "bengaluru", "work_mode": "onsite",
     "start_date": _d(date(2026, 3, 6)),
     "end_date": _d(date(2026, 8, 15)),
     "bill_rate_lpa": 24.0},
]

NAMED_CTR_SKILLS: dict[str, list[str]] = {
    "C-17": ["react", "nodejs", "kubernetes", "typescript", "javascript",
             "docker", "aws", "postgresql", "rest_apis", "git", "ci_cd",
             "linux"],
    "C-09": ["react", "nodejs", "kubernetes", "typescript", "javascript",
             "docker", "rest_apis", "git"],
}


# ═══════════════════════════════════════════════════════════════════════
# Generators
# ═══════════════════════════════════════════════════════════════════════

def _skill_pool(level: str, team: str) -> list[str]:
    if level == "junior":
        pool = ["react", "nodejs", "javascript", "html_css", "git", "jest",
                "typescript", "python", "sql"]
    elif level == "mid":
        pool = ["react", "nodejs", "typescript", "javascript", "docker",
                "html_css", "git", "ci_cd", "postgresql", "rest_apis", "jest",
                "redis", "mongodb", "express", "nextjs", "python", "sql",
                "angular", "vue"]
    else:
        pool = list(ALL_SKILLS)
    if team == "Platform" and "terraform" in pool:
        pool = [s for s in pool if s != "terraform"]
    return pool


def _gen_employees(fake: Faker, rng: np.random.Generator):
    employees = list(NAMED_EMPLOYEES)
    emp_skills: list[dict] = []

    for eid, skills in NAMED_EMP_SKILLS.items():
        for sid in skills:
            emp_skills.append({"employee_id": eid, "skill_id": sid})

    used = {int(e["employee_id"].split("-")[1]) for e in NAMED_EMPLOYEES}
    avail = sorted(i for i in range(1, 100) if i not in used)

    levels = ["junior", "mid", "senior", "lead"]
    level_p = [0.25, 0.35, 0.30, 0.10]
    loc_p = [0.60, 0.15, 0.15, 0.10]
    locs = ["bengaluru", "hyderabad", "pune", "remote_india"]

    n_random = min(72, len(avail))
    level_choices = list(rng.choice(levels, size=n_random, p=level_p))
    team_choices = list(rng.choice(TEAMS, size=n_random))
    loc_choices = list(rng.choice(locs, size=n_random, p=loc_p))

    for i in range(n_random):
        eid = f"E-{avail[i]:03d}"
        level = str(level_choices[i])
        team = str(team_choices[i])
        loc = str(loc_choices[i])
        wm = "remote" if loc == "remote_india" else (
            str(rng.choice(["onsite", "hybrid"], p=[0.8, 0.2])))

        yr_lo, yr_hi = {"junior": (0.5, 2.0), "mid": (2.0, 5.0),
                        "senior": (5.0, 10.0), "lead": (8.0, 15.0)}[level]
        years = round(float(rng.uniform(yr_lo, yr_hi)), 1)
        hdate = TODAY - timedelta(days=int(years * 365))

        employees.append({
            "employee_id": eid,
            "display_name": fake.first_name(),
            "level": level,
            "team": team,
            "location": loc,
            "work_mode": wm,
            "hire_date": _d(hdate),
            "years_exp": years,
            "open_to_move": "true" if float(rng.random()) < 0.35 else "false",
            "is_active": "true",
            "rating": int(rng.choice([3, 3, 4, 4, 5], p=[0.25, 0.25, 0.25, 0.15, 0.10])),
        })

        pool = _skill_pool(level, team)
        n_sk = int({"junior": rng.integers(4, 8),
                     "mid": rng.integers(7, 12),
                     "senior": rng.integers(10, 16),
                     "lead": rng.integers(12, 18)}[level])
        n_sk = min(n_sk, len(pool))
        chosen = list(rng.choice(pool, size=n_sk, replace=False))
        chosen_set = {str(s) for s in chosen}
        if employees[-1]["open_to_move"] == "true" \
                and "react" in chosen_set and "nodejs" in chosen_set:
            chosen = [s for s in chosen if str(s) != "nodejs"]
        for sid in chosen:
            emp_skills.append({"employee_id": eid, "skill_id": str(sid)})

    return employees, emp_skills


def _gen_contractors(fake: Faker, rng: np.random.Generator):
    contractors = list(NAMED_CONTRACTORS)
    ctr_skills: list[dict] = []

    for cid, skills in NAMED_CTR_SKILLS.items():
        for sid in skills:
            ctr_skills.append({"contractor_id": cid, "skill_id": sid})

    for num in [3, 5, 8, 11, 14, 20, 22]:
        cid = f"C-{num:02d}"
        level = str(rng.choice(["mid", "senior"]))
        loc = str(rng.choice(["bengaluru", "hyderabad", "pune", "remote_india"]))
        contractors.append({
            "contractor_id": cid,
            "display_name": fake.first_name(),
            "supplier_id": str(rng.choice(["SUP-01", "SUP-02", "SUP-03"])),
            "level": level,
            "location": loc,
            "work_mode": "remote" if loc == "remote_india" else "onsite",
            "start_date": _d(TODAY - timedelta(days=int(rng.integers(60, 365)))),
            "end_date": _d(TODAY + timedelta(days=int(rng.integers(30, 180)))),
            "bill_rate_lpa": round(float(rng.uniform(15, 30)), 1),
        })
        pool = list(ALL_SKILLS)
        n_sk = int(rng.integers(6, 12))
        chosen = list(rng.choice(pool, size=min(n_sk, len(pool)), replace=False))
        for sid in chosen:
            ctr_skills.append({"contractor_id": cid, "skill_id": str(sid)})

    return contractors, ctr_skills


def _gen_requisitions():
    fields = [
        "req_id", "role", "level", "team", "location", "work_mode",
        "opened_date", "closed_date", "decision", "outcome", "person_id",
        "time_to_fill_days", "first_year_cost_lpa",
    ]
    rows = [
        {"req_id": "REQ-001", "role": "Full Stack Developer",
         "level": "senior", "team": "Payments",
         "location": "bengaluru", "work_mode": "onsite",
         "opened_date": "2024-11-05", "closed_date": "2025-01-12",
         "decision": "buy", "outcome": "left_9m", "person_id": "E-018",
         "time_to_fill_days": 68, "first_year_cost_lpa": 31.0},
        {"req_id": "REQ-002", "role": "Full Stack Developer",
         "level": "senior", "team": "Payments",
         "location": "bengaluru", "work_mode": "onsite",
         "opened_date": "2025-10-01", "closed_date": "2025-12-14",
         "decision": "buy", "outcome": "left_7m", "person_id": "E-020",
         "time_to_fill_days": 74, "first_year_cost_lpa": 33.0},
        {"req_id": "REQ-003", "role": "Full Stack Developer",
         "level": "senior", "team": "Payments",
         "location": "bengaluru", "work_mode": "onsite",
         "opened_date": "2026-03-01", "closed_date": "2026-03-07",
         "decision": "borrow", "outcome": "knowledge_lost",
         "person_id": "C-09",
         "time_to_fill_days": 6, "first_year_cost_lpa": 24.0},
        {"req_id": "REQ-004", "role": "Full Stack Developer",
         "level": "senior", "team": "Payments",
         "location": "bengaluru", "work_mode": "onsite",
         "opened_date": "2026-06-01", "closed_date": "2026-06-15",
         "decision": "build", "outcome": "still_in_role",
         "person_id": "E-010",
         "time_to_fill_days": 0, "first_year_cost_lpa": 4.0},
    ]
    return rows, fields


def _gen_exits():
    fields = ["employee_id", "exit_date", "tenure_months",
              "exit_reason", "req_origin"]
    rows = [
        {"employee_id": "E-018", "exit_date": "2025-10-18",
         "tenure_months": 9, "exit_reason": "role_mismatch",
         "req_origin": "REQ-001"},
        {"employee_id": "E-020", "exit_date": "2026-07-20",
         "tenure_months": 7, "exit_reason": "counter_offer",
         "req_origin": "REQ-002"},
    ]
    return rows, fields


def _gen_candidates(fake: Faker, rng: np.random.Generator):
    candidates: list[dict] = []
    cand_skills: list[dict] = []
    counter = [1]

    sources = ["job_board", "referral", "direct", "agency"]

    def _batch(loc, wm, level, count, must_have, extra_pool, yr_range):
        yr_lo, yr_hi = yr_range
        for _ in range(count):
            cid = f"EXT-{counter[0]:04d}"
            counter[0] += 1
            years = round(float(rng.uniform(yr_lo, yr_hi)), 1)
            candidates.append({
                "candidate_id": cid, "level": level,
                "location": loc, "work_mode": wm,
                "years_exp": years,
                "source": str(rng.choice(sources)),
            })
            skills = set(must_have)
            avail = [s for s in extra_pool if s not in skills]
            if avail:
                n_extra = int(rng.integers(3, 9))
                n_extra = min(n_extra, len(avail))
                chosen = list(rng.choice(avail, size=n_extra, replace=False))
                skills.update(str(s) for s in chosen)
            for sid in sorted(skills):
                cand_skills.append({"candidate_id": cid, "skill_id": sid})

    sr_extra = [s for s in ALL_SKILLS
                if s not in ("react", "nodejs", "kubernetes")]
    sr_extra_no_k8s = [s for s in ALL_SKILLS
                       if s not in ("react", "nodejs", "kubernetes")]
    sr_no_rn = [s for s in ALL_SKILLS if s not in ("react", "nodejs")]

    sr = (5.0, 12.0)

    # Bengaluru Senior: 14 all-match + 33 react+node only + 15 padding
    _batch("bengaluru", "onsite", "senior", 14,
           ["react", "nodejs", "kubernetes"], sr_extra, sr)
    _batch("bengaluru", "onsite", "senior", 33,
           ["react", "nodejs"], sr_extra_no_k8s, sr)
    _batch("bengaluru", "onsite", "senior", 15,
           [], sr_no_rn, sr)

    # Remote-India Senior: 210 all-match + 40 padding
    _batch("remote_india", "remote", "senior", 210,
           ["react", "nodejs", "kubernetes"], sr_extra, sr)
    _batch("remote_india", "remote", "senior", 40,
           [], sr_no_rn, sr)

    # Hyderabad Senior: 31 all-match + 12 padding
    _batch("hyderabad", "onsite", "senior", 31,
           ["react", "nodejs", "kubernetes"], sr_extra, sr)
    _batch("hyderabad", "onsite", "senior", 12,
           [], sr_no_rn, sr)

    # Pune Senior: 26 all-match + 10 padding
    _batch("pune", "onsite", "senior", 26,
           ["react", "nodejs", "kubernetes"], sr_extra, sr)
    _batch("pune", "onsite", "senior", 10,
           [], sr_no_rn, sr)

    # Other levels
    jr_pool = ["react", "nodejs", "javascript", "html_css", "git", "jest",
               "typescript", "python", "sql"]
    mid_pool = jr_pool + ["docker", "ci_cd", "postgresql", "rest_apis",
                          "mongodb", "express"]

    _batch("bengaluru", "onsite", "junior", 100, [], jr_pool, (0.5, 2.0))
    _batch("bengaluru", "onsite", "mid", 60, [], mid_pool, (2.0, 5.0))
    _batch("bengaluru", "onsite", "lead", 15, [], ALL_SKILLS, (8.0, 15.0))
    _batch("remote_india", "remote", "junior", 50, [], jr_pool, (0.5, 2.0))
    _batch("remote_india", "remote", "mid", 40, [], mid_pool, (2.0, 5.0))
    _batch("hyderabad", "onsite", "junior", 30, [], jr_pool, (0.5, 2.0))
    _batch("hyderabad", "onsite", "mid", 25, [], mid_pool, (2.0, 5.0))
    _batch("pune", "onsite", "junior", 25, [], jr_pool, (0.5, 2.0))
    _batch("pune", "onsite", "mid", 20, [], mid_pool, (2.0, 5.0))

    return candidates, cand_skills


def _gen_evidence():
    fields = ["person_id", "skill_id", "source", "value",
              "observed_on", "detail"]
    ev: list[dict] = []

    def _add(pid, sid, src, val, obs, detail=""):
        ev.append({"person_id": pid, "skill_id": sid, "source": src,
                    "value": val, "observed_on": obs, "detail": detail})

    # ── Demo-specific evidence (Section 13) ──

    _add("E-072", "aws", "assessment", "35", "2026-03-12")
    _add("E-072", "aws", "self", "intermediate", "2026-03-12")

    _add("E-045", "kubernetes", "assessment", "40", "2026-08-18")
    _add("E-045", "kubernetes", "self", "expert", "2026-08-18")

    _add("E-031", "terraform", "certification", "", "2025-06-15",
         "Terraform Associate 2025")
    _add("E-031", "terraform", "project", "30", "2026-09-01",
         "Platform-Core")

    _add("E-045", "graphql", "self", "intermediate", "2025-02-15")

    # ── Data quality targets (2 conflicts, 1 stale, 3 self-report-only) ──

    _add("E-031", "python", "assessment", "38", "2026-04-01")
    _add("E-031", "python", "self", "expert", "2026-04-01")

    _add("E-045", "docker", "assessment", "70", "2024-09-15")

    _add("E-072", "mongodb", "self", "beginner", "2025-08-01")

    _add("C-17", "gcp", "self", "intermediate", "2025-09-01")

    # ── Karthik remaining skills ──
    for sid, score in [
        ("react", 85), ("nodejs", 82), ("kubernetes", 78),
        ("typescript", 80), ("javascript", 88), ("docker", 85),
        ("aws", 75), ("system_design", 90), ("microservices", 82),
        ("git", 90), ("ci_cd", 78), ("postgresql", 80),
        ("rest_apis", 85), ("linux", 82),
    ]:
        _add("E-031", sid, "assessment", str(score), "2026-04-01")

    # ── Priya remaining skills (docker already added as stale above) ──
    for sid, score in [
        ("react", 90), ("nodejs", 88), ("typescript", 82),
        ("javascript", 85), ("html_css", 82), ("git", 85),
        ("ci_cd", 70), ("postgresql", 78), ("rest_apis", 80), ("jest", 80),
    ]:
        _add("E-045", sid, "assessment", str(score), "2026-05-01")

    # ── Rahul remaining skills ──
    for sid, score in [
        ("react", 68), ("nodejs", 64), ("javascript", 75),
        ("html_css", 75), ("git", 80), ("jest", 65),
    ]:
        _add("E-072", sid, "assessment", str(score), "2026-06-01")

    # ── Arjun remaining skills ──
    for sid, score in [
        ("react", 80), ("nodejs", 78), ("kubernetes", 82),
        ("typescript", 75), ("javascript", 85), ("docker", 80),
        ("aws", 72), ("postgresql", 75), ("rest_apis", 78),
        ("git", 85), ("ci_cd", 76), ("linux", 80),
    ]:
        _add("C-17", sid, "assessment", str(score), "2026-06-01")

    return ev, fields


def _gen_market_stats():
    fields = ["location", "level", "work_mode", "demand",
              "sal_p25", "sal_p50", "sal_p75", "ttf_p50", "ttf_p80",
              "col_index", "remote_share", "reloc_package_lpa"]
    rows = [
        {"location": "bengaluru", "level": "senior", "work_mode": "onsite",
         "demand": 8, "sal_p25": 24, "sal_p50": 32, "sal_p75": 40,
         "ttf_p50": 62, "ttf_p80": 81,
         "col_index": 1.00, "remote_share": 0.05, "reloc_package_lpa": 2.0},
        {"location": "remote_india", "level": "senior", "work_mode": "remote",
         "demand": 15, "sal_p25": 22, "sal_p50": 29, "sal_p75": 36,
         "ttf_p50": 28, "ttf_p80": 40,
         "col_index": 1.00, "remote_share": 1.00, "reloc_package_lpa": 0.0},
        {"location": "hyderabad", "level": "senior", "work_mode": "onsite",
         "demand": 5, "sal_p25": 23, "sal_p50": 30, "sal_p75": 38,
         "ttf_p50": 44, "ttf_p80": 58,
         "col_index": 0.70, "remote_share": 0.30, "reloc_package_lpa": 1.0},
        {"location": "pune", "level": "senior", "work_mode": "onsite",
         "demand": 4, "sal_p25": 20, "sal_p50": 26, "sal_p75": 33,
         "ttf_p50": 47, "ttf_p80": 62,
         "col_index": 0.78, "remote_share": 0.15, "reloc_package_lpa": 1.0},
        {"location": "bengaluru", "level": "junior", "work_mode": "onsite",
         "demand": 20, "sal_p25": 5, "sal_p50": 7, "sal_p75": 10,
         "ttf_p50": 21, "ttf_p80": 30,
         "col_index": 1.00, "remote_share": 0.05, "reloc_package_lpa": 2.0},
        {"location": "bengaluru", "level": "mid", "work_mode": "onsite",
         "demand": 12, "sal_p25": 14, "sal_p50": 18, "sal_p75": 24,
         "ttf_p50": 35, "ttf_p80": 50,
         "col_index": 1.00, "remote_share": 0.05, "reloc_package_lpa": 2.0},
        {"location": "bengaluru", "level": "lead", "work_mode": "onsite",
         "demand": 3, "sal_p25": 35, "sal_p50": 42, "sal_p75": 52,
         "ttf_p50": 76, "ttf_p80": 95,
         "col_index": 1.00, "remote_share": 0.05, "reloc_package_lpa": 2.0},
        {"location": "remote_india", "level": "junior", "work_mode": "remote",
         "demand": 30, "sal_p25": 4, "sal_p50": 6, "sal_p75": 8,
         "ttf_p50": 18, "ttf_p80": 25,
         "col_index": 1.00, "remote_share": 1.00, "reloc_package_lpa": 0.0},
        {"location": "remote_india", "level": "mid", "work_mode": "remote",
         "demand": 20, "sal_p25": 12, "sal_p50": 16, "sal_p75": 22,
         "ttf_p50": 30, "ttf_p80": 42,
         "col_index": 1.00, "remote_share": 1.00, "reloc_package_lpa": 0.0},
        {"location": "remote_india", "level": "lead", "work_mode": "remote",
         "demand": 5, "sal_p25": 30, "sal_p50": 38, "sal_p75": 48,
         "ttf_p50": 65, "ttf_p80": 85,
         "col_index": 1.00, "remote_share": 1.00, "reloc_package_lpa": 0.0},
        {"location": "hyderabad", "level": "junior", "work_mode": "onsite",
         "demand": 15, "sal_p25": 4, "sal_p50": 6, "sal_p75": 9,
         "ttf_p50": 23, "ttf_p80": 32,
         "col_index": 0.70, "remote_share": 0.30, "reloc_package_lpa": 1.0},
        {"location": "hyderabad", "level": "mid", "work_mode": "onsite",
         "demand": 10, "sal_p25": 12, "sal_p50": 17, "sal_p75": 23,
         "ttf_p50": 38, "ttf_p80": 52,
         "col_index": 0.70, "remote_share": 0.30, "reloc_package_lpa": 1.0},
        {"location": "hyderabad", "level": "lead", "work_mode": "onsite",
         "demand": 2, "sal_p25": 32, "sal_p50": 40, "sal_p75": 50,
         "ttf_p50": 70, "ttf_p80": 90,
         "col_index": 0.70, "remote_share": 0.30, "reloc_package_lpa": 1.0},
        {"location": "pune", "level": "junior", "work_mode": "onsite",
         "demand": 12, "sal_p25": 4, "sal_p50": 5, "sal_p75": 8,
         "ttf_p50": 25, "ttf_p80": 35,
         "col_index": 0.78, "remote_share": 0.15, "reloc_package_lpa": 1.0},
        {"location": "pune", "level": "mid", "work_mode": "onsite",
         "demand": 8, "sal_p25": 11, "sal_p50": 15, "sal_p75": 21,
         "ttf_p50": 40, "ttf_p80": 55,
         "col_index": 0.78, "remote_share": 0.15, "reloc_package_lpa": 1.0},
        {"location": "pune", "level": "lead", "work_mode": "onsite",
         "demand": 2, "sal_p25": 30, "sal_p50": 38, "sal_p75": 48,
         "ttf_p50": 72, "ttf_p80": 92,
         "col_index": 0.78, "remote_share": 0.15, "reloc_package_lpa": 1.0},
    ]
    return rows, fields


def _gen_projects(employees: list[dict]):
    proj_fields = ["project_id", "name", "team", "is_critical",
                   "required_skills"]
    projects = [
        {"project_id": "PROJ-01", "name": "Platform-Core",
         "team": "Platform", "is_critical": "true",
         "required_skills": "terraform,kubernetes,aws,docker,linux"},
        {"project_id": "PROJ-02", "name": "Checkout-Main",
         "team": "Checkout", "is_critical": "false",
         "required_skills": "react,nodejs,typescript,postgresql"},
        {"project_id": "PROJ-03", "name": "Payments-API",
         "team": "Payments", "is_critical": "false",
         "required_skills": "react,nodejs,rest_apis,postgresql"},
        {"project_id": "PROJ-04", "name": "Growth-Engine",
         "team": "Growth", "is_critical": "false",
         "required_skills": "react,nodejs,typescript,postgresql"},
        {"project_id": "PROJ-05", "name": "Infra-Pipeline",
         "team": "Infra", "is_critical": "false",
         "required_skills": "docker,kubernetes,linux,ci_cd"},
        {"project_id": "PROJ-06", "name": "Mobile-App",
         "team": "Mobile", "is_critical": "false",
         "required_skills": "react,typescript,rest_apis"},
        {"project_id": "PROJ-07", "name": "Data-Platform",
         "team": "Data", "is_critical": "false",
         "required_skills": "python,postgresql,kafka,aws"},
    ]

    team_proj = {p["team"]: p["project_id"] for p in projects}

    asgn_fields = ["employee_id", "project_id", "start_date"]
    assignments: list[dict] = []
    for emp in employees:
        if emp["is_active"] == "true":
            proj = team_proj.get(emp["team"])
            if proj:
                assignments.append({
                    "employee_id": emp["employee_id"],
                    "project_id": proj,
                    "start_date": emp["hire_date"],
                })

    return projects, proj_fields, assignments, asgn_fields


def _gen_sourcing():
    fields = ["channel", "fill_rate", "median_days",
              "applicable_levels", "notes"]
    rows = [
        {"channel": "past_finalists", "fill_rate": "", "median_days": "",
         "applicable_levels": "senior",
         "notes": "ATS rediscovery pool"},
        {"channel": "referral", "fill_rate": 0.38, "median_days": 34,
         "applicable_levels": "all",
         "notes": "Employee referral program"},
        {"channel": "supplier", "fill_rate": 0.45, "median_days": 9,
         "applicable_levels": "senior,mid",
         "notes": "Staffing supplier A via MSP"},
        {"channel": "job_board", "fill_rate": 0.22, "median_days": 52,
         "applicable_levels": "all",
         "notes": "Public job board"},
        {"channel": "campus", "fill_rate": 0.15, "median_days": 90,
         "applicable_levels": "junior",
         "notes": "Campus recruitment"},
    ]
    return rows, fields


def _gen_suppliers():
    fields = ["supplier_id", "name", "fill_rate",
              "median_days_to_submit", "avg_bill_rate_lpa"]
    rows = [
        {"supplier_id": "SUP-01", "name": "Staffing Supplier A",
         "fill_rate": 0.45, "median_days_to_submit": 9,
         "avg_bill_rate_lpa": 2.0},
        {"supplier_id": "SUP-02", "name": "Staffing Supplier B",
         "fill_rate": 0.30, "median_days_to_submit": 14,
         "avg_bill_rate_lpa": 2.2},
        {"supplier_id": "SUP-03", "name": "Staffing Supplier C",
         "fill_rate": 0.25, "median_days_to_submit": 18,
         "avg_bill_rate_lpa": 1.8},
    ]
    return rows, fields


def _gen_past_finalists():
    fields = ["candidate_id", "req_role", "stage_reached", "outcome",
              "decided_on", "open_to_remote", "opted_in_pool"]
    rows = [
        {"candidate_id": "PF-01", "req_role": "Full Stack Developer",
         "stage_reached": "final", "outcome": "declined",
         "decided_on": "2026-04-15", "open_to_remote": "true",
         "opted_in_pool": "true"},
        {"candidate_id": "PF-02", "req_role": "Full Stack Developer",
         "stage_reached": "final", "outcome": "closed",
         "decided_on": "2026-02-10", "open_to_remote": "true",
         "opted_in_pool": "true"},
        {"candidate_id": "PF-03", "req_role": "Full Stack Developer",
         "stage_reached": "final", "outcome": "declined",
         "decided_on": "2025-12-01", "open_to_remote": "false",
         "opted_in_pool": "true"},
    ]
    return rows, fields


# ═══════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════

def main(output_dir: Path | None = None):
    if output_dir is None:
        output_dir = DATA_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    rng = np.random.default_rng(SEED)
    fake = Faker("en_IN")
    Faker.seed(SEED)

    emp, emp_sk = _gen_employees(fake, rng)
    ctr, ctr_sk = _gen_contractors(fake, rng)
    reqs, req_fields = _gen_requisitions()
    exits, exit_fields = _gen_exits()
    cands, cand_sk = _gen_candidates(fake, rng)
    evidence, ev_fields = _gen_evidence()
    market, mkt_fields = _gen_market_stats()
    projects, proj_fields, assignments, asgn_fields = _gen_projects(emp)
    sourcing, src_fields = _gen_sourcing()
    suppliers, sup_fields = _gen_suppliers()
    finalists, fin_fields = _gen_past_finalists()

    w = lambda name, rows, fields: _write(name, rows, fields, output_dir)
    w("employees.csv", emp, _EMP_FIELDS)
    w("employee_skills.csv", emp_sk, ["employee_id", "skill_id"])
    w("contractors.csv", ctr, _CTR_FIELDS)
    w("contractor_skills.csv", ctr_sk, ["contractor_id", "skill_id"])
    w("requisitions.csv", reqs, req_fields)
    w("exits.csv", exits, exit_fields)
    w("candidates.csv", cands,
       ["candidate_id", "level", "location", "work_mode",
        "years_exp", "source"])
    w("candidate_skills.csv", cand_sk, ["candidate_id", "skill_id"])
    w("evidence.csv", evidence, ev_fields)
    w("market_stats.csv", market, mkt_fields)
    w("projects.csv", projects, proj_fields)
    w("project_assignments.csv", assignments, asgn_fields)
    w("sourcing_history.csv", sourcing, src_fields)
    w("suppliers.csv", suppliers, sup_fields)
    w("past_finalists.csv", finalists, fin_fields)


if __name__ == "__main__":
    main()
