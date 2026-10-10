"""Internal match scoring — pure functions, no I/O.

Match = round(100 × (0.50·S + 0.20·P + 0.15·R + 0.15·A))

S = weighted skill coverage (must=2, nice=1)
P = seniority fitness
R = evidence recency
A = availability
"""
from __future__ import annotations

from datetime import date
from math import exp

import pandas as pd

_LEVEL_NUM = {"junior": 1, "mid": 2, "senior": 3, "lead": 4}
_IMP_WEIGHT = {"must": 2, "nice": 1}

_CONFIDENCE = {"assessment": 1.00, "certification": 0.90, "project": 0.80, "self": 0.70}
_STALE_MULT = 0.85


def band(score: int) -> str:
    if score >= 85:
        return "redeploy"
    if score >= 70:
        return "Build"
    if score >= 50:
        return "long-term pipeline"
    return "hidden"


def build_edge_lookup(skill_edges_df: pd.DataFrame) -> dict[str, list[tuple[str, float]]]:
    lookup: dict[str, list[tuple[str, float]]] = {}
    for _, row in skill_edges_df.iterrows():
        a, b, w = row["skill_a"], row["skill_b"], float(row["weight"])
        lookup.setdefault(b, []).append((a, w))
        lookup.setdefault(a, []).append((b, w))
    return lookup


def _evidence_credit(
    skill_id: str,
    evidence_scores: list[dict],
    person_skills: set[str],
    edge_lookup: dict[str, list[tuple[str, float]]],
) -> float:
    ev = next((e for e in evidence_scores if e["skill"] == skill_id), None)
    if ev is not None:
        conf = _CONFIDENCE.get(ev["source"], 0.7)
        if ev.get("stale", False):
            conf *= _STALE_MULT
        return (ev["value"] / 100.0) * conf

    best = 0.0
    for adj_skill, edge_weight in edge_lookup.get(skill_id, []):
        if adj_skill not in person_skills:
            continue
        adj_ev = next((e for e in evidence_scores if e["skill"] == adj_skill), None)
        if adj_ev is None:
            continue
        conf = _CONFIDENCE.get(adj_ev["source"], 0.7)
        if adj_ev.get("stale", False):
            conf *= _STALE_MULT
        credit = edge_weight * (adj_ev["value"] / 100.0) * conf
        if credit > best:
            best = credit
    return best


def _compute_S(
    required_skills: list[dict],
    evidence_scores: list[dict],
    person_skills: set[str],
    edge_lookup: dict[str, list[tuple[str, float]]],
) -> tuple[float, bool]:
    total_weighted = 0.0
    total_weight = 0.0
    must_have_zero = False

    for sk in required_skills:
        sid = sk["id"]
        imp = sk.get("importance", "nice")
        w = _IMP_WEIGHT.get(imp, 1)

        credit = _evidence_credit(sid, evidence_scores, person_skills, edge_lookup)
        if imp == "must" and credit == 0.0:
            must_have_zero = True

        total_weighted += w * credit
        total_weight += w

    if total_weight == 0:
        return 0.0, must_have_zero
    return total_weighted / total_weight, must_have_zero


def _compute_P(person_level: str, required_level: str) -> float:
    emp_num = _LEVEL_NUM.get(person_level, 2)
    req_num = _LEVEL_NUM.get(required_level, 3)
    if emp_num >= req_num:
        return 1.0
    return 1.0 - 0.5 * (req_num - emp_num) / req_num


def _compute_R(
    evidence_scores: list[dict],
    must_skill_ids: list[str],
    today: date,
) -> float:
    months = []
    for sid in must_skill_ids:
        ev = next((e for e in evidence_scores if e["skill"] == sid), None)
        if ev and ev.get("observed_on"):
            obs = date.fromisoformat(ev["observed_on"])
            diff = (today - obs).days / 30.44
            months.append(diff)
    if not months:
        return 0.5
    avg = sum(months) / len(months)
    return exp(-avg / 24.0)


def _compute_A_contractor(start_date: date, today: date) -> float:
    tenure_days = (today - start_date).days
    tenure_months = tenure_days / 30.44
    return min(tenure_months / 20.0, 1.0)


def score_employee(
    person_id: str,
    required_skills: list[dict],
    evidence_scores: list[dict],
    person_skills: set[str],
    edge_lookup: dict[str, list[tuple[str, float]]],
    person_level: str,
    required_level: str,
    today: date = date(2026, 10, 8),
) -> dict:
    S, must_zero = _compute_S(required_skills, evidence_scores, person_skills,
                              edge_lookup)
    P = _compute_P(person_level, required_level)
    must_ids = [sk["id"] for sk in required_skills if sk.get("importance") == "must"]
    R = _compute_R(evidence_scores, must_ids, today)
    A = 1.0

    raw = 100.0 * (0.50 * S + 0.20 * P + 0.15 * R + 0.15 * A)
    score = round(raw)
    if must_zero:
        score = min(score, 70)

    evidence_ids = [e["skill"] for e in evidence_scores]

    return {
        "person_id": person_id,
        "match": score,
        "band": band(score),
        "S": round(S, 4),
        "P": round(P, 4),
        "R": round(R, 4),
        "A": round(A, 4),
        "evidence_ids": evidence_ids,
    }


def score_contractor(
    person_id: str,
    required_skills: list[dict],
    evidence_scores: list[dict],
    person_skills: set[str],
    edge_lookup: dict[str, list[tuple[str, float]]],
    person_level: str,
    required_level: str,
    start_date: date,
    today: date = date(2026, 10, 8),
) -> dict:
    S, must_zero = _compute_S(required_skills, evidence_scores, person_skills,
                              edge_lookup)
    P = _compute_P(person_level, required_level)
    must_ids = [sk["id"] for sk in required_skills if sk.get("importance") == "must"]
    R = _compute_R(evidence_scores, must_ids, today)
    A = _compute_A_contractor(start_date, today)

    raw = 100.0 * (0.50 * S + 0.20 * P + 0.15 * R + 0.15 * A)
    score = round(raw)
    if must_zero:
        score = min(score, 70)

    evidence_ids = [e["skill"] for e in evidence_scores]

    return {
        "person_id": person_id,
        "match": score,
        "band": band(score),
        "S": round(S, 4),
        "P": round(P, 4),
        "R": round(R, 4),
        "A": round(A, 4),
        "evidence_ids": evidence_ids,
    }
