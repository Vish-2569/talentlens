"""Build (upskill) analysis — pure functions, no I/O.

weeks_per_skill = base_weeks × distance × level_gap_factor
readiness = max(weeks) across gap skills (parallel learning)
"""
from __future__ import annotations

import pandas as pd

_LEVEL_NUM = {"junior": 1, "mid": 2, "senior": 3, "lead": 4}

_GAP_THRESHOLD = 60

COURSES: dict[str, dict] = {
    "react": {"base_weeks": 8, "cost_lpa": 0.3},
    "nodejs": {"base_weeks": 8, "cost_lpa": 0.3},
    "kubernetes": {"base_weeks": 8, "cost_lpa": 0.5},
    "aws": {"base_weeks": 10, "cost_lpa": 0.5},
    "graphql": {"base_weeks": 6, "cost_lpa": 0.2},
    "terraform": {"base_weeks": 10, "cost_lpa": 0.5},
    "docker": {"base_weeks": 6, "cost_lpa": 0.3},
    "typescript": {"base_weeks": 6, "cost_lpa": 0.2},
    "javascript": {"base_weeks": 6, "cost_lpa": 0.2},
    "nextjs": {"base_weeks": 6, "cost_lpa": 0.2},
    "express": {"base_weeks": 4, "cost_lpa": 0.1},
    "postgresql": {"base_weeks": 6, "cost_lpa": 0.2},
    "mongodb": {"base_weeks": 4, "cost_lpa": 0.2},
    "redis": {"base_weeks": 4, "cost_lpa": 0.1},
    "rest_apis": {"base_weeks": 4, "cost_lpa": 0.1},
    "git": {"base_weeks": 2, "cost_lpa": 0.05},
    "ci_cd": {"base_weeks": 6, "cost_lpa": 0.2},
    "jest": {"base_weeks": 4, "cost_lpa": 0.1},
    "html_css": {"base_weeks": 4, "cost_lpa": 0.1},
    "python": {"base_weeks": 8, "cost_lpa": 0.3},
    "java": {"base_weeks": 10, "cost_lpa": 0.3},
    "kafka": {"base_weeks": 8, "cost_lpa": 0.3},
    "linux": {"base_weeks": 6, "cost_lpa": 0.2},
    "microservices": {"base_weeks": 8, "cost_lpa": 0.3},
    "system_design": {"base_weeks": 10, "cost_lpa": 0.3},
    "angular": {"base_weeks": 8, "cost_lpa": 0.3},
    "vue": {"base_weeks": 6, "cost_lpa": 0.2},
    "azure": {"base_weeks": 10, "cost_lpa": 0.5},
    "gcp": {"base_weeks": 10, "cost_lpa": 0.5},
    "sql": {"base_weeks": 4, "cost_lpa": 0.1},
}


def _build_adj_lookup(skill_edges_df: pd.DataFrame) -> dict[str, set[str]]:
    lookup: dict[str, set[str]] = {}
    for _, row in skill_edges_df.iterrows():
        a, b = row["skill_a"], row["skill_b"]
        lookup.setdefault(a, set()).add(b)
        lookup.setdefault(b, set()).add(a)
    return lookup


def _build_weighted_adj(skill_edges_df: pd.DataFrame) -> dict[str, list[tuple[str, float]]]:
    lookup: dict[str, list[tuple[str, float]]] = {}
    for _, row in skill_edges_df.iterrows():
        a, b, w = row["skill_a"], row["skill_b"], float(row["weight"])
        lookup.setdefault(a, []).append((b, w))
        lookup.setdefault(b, []).append((a, w))
    return lookup


def _distance(
    skill_id: str,
    person_skills: set[str],
    evidence_scores: list[dict],
    adj_lookup: dict[str, set[str]],
    weighted_adj: dict[str, list[tuple[str, float]]],
) -> float:
    ev = next((e for e in evidence_scores if e["skill"] == skill_id), None)
    if ev is not None and ev["value"] >= _GAP_THRESHOLD:
        return 0.0

    best_adj = 0.0
    for adj_skill, weight in weighted_adj.get(skill_id, []):
        if adj_skill in person_skills:
            best_adj = max(best_adj, weight)
    if best_adj > 0:
        return best_adj

    return 1.0


def _level_gap_factor(person_level: str, required_level: str) -> float:
    gap = _LEVEL_NUM.get(required_level, 3) - _LEVEL_NUM.get(person_level, 2)
    if gap <= 0:
        return 1.0
    if gap == 1:
        return 1.5
    return 2.0


def build_plan(
    person_id: str,
    evidence_scores: list[dict],
    person_skills: set[str],
    required_skills: list[dict],
    skill_edges_df: pd.DataFrame,
    person_level: str,
    required_level: str,
) -> dict:
    adj_lookup = _build_adj_lookup(skill_edges_df)
    weighted_adj = _build_weighted_adj(skill_edges_df)
    lgf = _level_gap_factor(person_level, required_level)

    gap_skills: list[dict] = []
    evidence_ids: list[str] = [e["skill"] for e in evidence_scores]

    for sk in required_skills:
        sid = sk["id"]
        if sk.get("importance") != "must":
            continue
        ev = next((e for e in evidence_scores if e["skill"] == sid), None)
        if ev is not None and ev["value"] >= _GAP_THRESHOLD:
            continue

        dist = _distance(sid, person_skills, evidence_scores, adj_lookup, weighted_adj)
        if dist == 0.0:
            continue

        course = COURSES.get(sid, {"base_weeks": 8, "cost_lpa": 0.3})
        weeks = round(course["base_weeks"] * dist * lgf)
        cost = course["cost_lpa"]

        gap_skills.append({
            "skill_id": sid,
            "distance": dist,
            "weeks": weeks,
            "cost_lpa": cost,
            "current_value": ev["value"] if ev else 0,
        })

    readiness_weeks = max((g["weeks"] for g in gap_skills), default=0)
    build_cost_lpa = round(sum(g["cost_lpa"] for g in gap_skills), 2)

    return {
        "person_id": person_id,
        "readiness_weeks": readiness_weeks,
        "build_cost_lpa": build_cost_lpa,
        "gap_skills": gap_skills,
        "evidence_ids": evidence_ids,
    }


def build_chain_cost(
    junior_salary_lpa: float,
    raises_lpa: float,
    upskill_cost_lpa: float,
) -> dict:
    total = round(junior_salary_lpa + raises_lpa + upskill_cost_lpa, 2)
    return {
        "total_cost_lpa": total,
        "breakdown": {
            "junior_hire": junior_salary_lpa,
            "raises": raises_lpa,
            "upskill": upskill_cost_lpa,
        },
    }
