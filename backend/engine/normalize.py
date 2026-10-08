"""Title and skill normalization — pure functions, no I/O."""
from __future__ import annotations

import re

import pandas as pd
from rapidfuzz import fuzz

ESCO_URI = "http://data.europa.eu/esco/occupation/f2b15a0e-e65a-438a-affb-29b9d50b77d1"

_LEVEL_TOKENS = [
    (re.compile(r"\bSDE[-\s]?1\b", re.I), "junior"),
    (re.compile(r"\bSDE[-\s]?2\b", re.I), "mid"),
    (re.compile(r"\bSDE[-\s]?3\b", re.I), "senior"),
    (re.compile(r"\bJr\.?\b", re.I), "junior"),
    (re.compile(r"\bJunior\b", re.I), "junior"),
    (re.compile(r"\bMid\b", re.I), "mid"),
    (re.compile(r"\bSr\.?\b", re.I), "senior"),
    (re.compile(r"\bSenior\b", re.I), "senior"),
    (re.compile(r"\bLead\b", re.I), "lead"),
    (re.compile(r"\bIII\b"), "senior"),
    (re.compile(r"\bII\b"), "mid"),
    (re.compile(r"\b(?<!\w)I(?!\w)\b"), "junior"),
]

DEMO_TITLES = [
    ("SDE-2 (Full Stack)", "hris"),
    ("MERN Stack Developer", "ats"),
    ("Full-Stack Engineer – Contract", "vms"),
    ("Web Developer", "jobboard"),
    ("Sr. Full Stack Developer", "ats"),
    ("Full Stack Developer III", "hris"),
    ("Lead Full Stack Engineer", "hris"),
    ("SDE-1", "hris"),
    ("React + Node Developer", "jobboard"),
    ("MEAN Stack Developer", "ats"),
    ("Full Stack Web Developer", "jobboard"),
    ("SDE-3 (Full Stack)", "hris"),
]


def _extract_level(raw_title: str) -> tuple[str | None, str]:
    """Extract seniority level and return (level, cleaned_title)."""
    level = None
    cleaned = raw_title
    for pat, lvl in _LEVEL_TOKENS:
        if pat.search(cleaned):
            level = lvl
            cleaned = pat.sub("", cleaned).strip()
            break
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" ,-–()")
    return level, cleaned


def normalize_title(
    raw_title: str,
    source_system: str,
    title_aliases: pd.DataFrame,
    canonical_roles: list[dict],
) -> dict:
    level_from_token, cleaned = _extract_level(raw_title)
    level_label = "stated" if level_from_token else "inferred"

    role_info = canonical_roles[0]
    esco_uri = role_info["esco_uri"]
    onet_codes = role_info["onet_codes"]

    exact = title_aliases[
        title_aliases["raw_title"].str.lower() == raw_title.lower()
    ]
    if not exact.empty:
        row = exact.iloc[0]
        level = row["level"] if pd.notna(row["level"]) and row["level"] else level_from_token
        onet = _pick_onet(row.get("method", "manual"), onet_codes)
        return {
            "role": "Full Stack Developer",
            "level": level,
            "level_label": level_label,
            "method": row["method"],
            "confidence": float(row["confidence"]),
            "esco_uri": esco_uri,
            "onet_code": onet,
        }

    best_score = 0
    best_row = None
    for _, row in title_aliases.iterrows():
        _, alias_cleaned = _extract_level(row["raw_title"])
        score = fuzz.token_set_ratio(cleaned.lower(), alias_cleaned.lower())
        if score > best_score:
            best_score = score
            best_row = row

    if best_score >= 90:
        level = best_row["level"] if pd.notna(best_row["level"]) and best_row["level"] else level_from_token
        onet = _pick_onet("fuzzy", onet_codes)
        return {
            "role": "Full Stack Developer",
            "level": level,
            "level_label": level_label,
            "method": "fuzzy",
            "confidence": round(best_score / 100, 2),
            "esco_uri": esco_uri,
            "onet_code": onet,
        }

    if best_score >= 75:
        level = best_row["level"] if pd.notna(best_row["level"]) and best_row["level"] else level_from_token
        onet = _pick_onet("fuzzy", onet_codes)
        return {
            "role": "Full Stack Developer",
            "level": level,
            "level_label": "inferred",
            "method": "fuzzy",
            "confidence": round(best_score / 100, 2),
            "esco_uri": esco_uri,
            "onet_code": onet,
        }

    return {"rejected": True, "reason": f"No match for '{raw_title}' (best score {best_score})"}


def _pick_onet(method: str, onet_codes: list[str]) -> str:
    if method == "onet" and len(onet_codes) > 1:
        return onet_codes[0]
    return onet_codes[-1] if onet_codes else ""


def title_normalization_panel(
    title_aliases: pd.DataFrame,
    canonical_roles: list[dict],
) -> dict:
    mappings = []
    levels_seen: set[str] = set()

    for raw, system in DEMO_TITLES:
        result = normalize_title(raw, system, title_aliases, canonical_roles)
        if result.get("rejected"):
            continue
        m = {
            "raw_title": raw,
            "source_system": system,
            "role": result["role"],
            "level": result["level"],
            "method": result["method"],
            "confidence": result["confidence"],
            "esco_uri": result["esco_uri"],
            "onet_code": result["onet_code"],
        }
        mappings.append(m)
        if result["level"]:
            levels_seen.add(result["level"])

    return {
        "raw_titles_count": len(mappings),
        "role": "Full Stack Developer",
        "levels": sorted(levels_seen, key=["junior", "mid", "senior", "lead"].index),
        "mappings": mappings,
    }


def normalize_skill(
    token: str,
    skills: pd.DataFrame,
    skill_aliases: pd.DataFrame,
) -> dict:
    lower = token.strip().lower()

    if lower in skills["id"].values:
        return {"skill_id": lower}

    alias_match = skill_aliases[skill_aliases["alias"].str.lower() == lower]
    if not alias_match.empty:
        return {"skill_id": alias_match.iloc[0]["skill_id"]}

    best_score = 0
    best_id = None
    for _, row in skill_aliases.iterrows():
        score = fuzz.token_set_ratio(lower, row["alias"].lower())
        if score > best_score:
            best_score = score
            best_id = row["skill_id"]

    for _, row in skills.iterrows():
        score = fuzz.token_set_ratio(lower, row["id"].lower())
        if score > best_score:
            best_score = score
            best_id = row["id"]
        if pd.notna(row.get("name")):
            score = fuzz.token_set_ratio(lower, row["name"].lower())
            if score > best_score:
                best_score = score
                best_id = row["id"]

    if best_score >= 90:
        return {"skill_id": best_id}
    if best_score >= 75:
        return {"skill_id": best_id, "inferred": True}

    return {"unknown": True, "token": token}


def skill_relation(
    a: str,
    b: str,
    skill_edges: pd.DataFrame,
) -> tuple[str, float] | None:
    match = skill_edges[
        (skill_edges.skill_a == a) & (skill_edges.skill_b == b)
    ]
    if not match.empty:
        row = match.iloc[0]
        return (row["type"], float(row["weight"]))

    reverse = skill_edges[
        (skill_edges.skill_a == b) & (skill_edges.skill_b == a)
    ]
    if not reverse.empty:
        row = reverse.iloc[0]
        return (row["type"], float(row["weight"]))

    return None
