"""Skill evidence scoring — pure functions, no I/O.

Rules:
- Trust rank: assessment 1, certification 2, project 3, self 4
- Confidence weight: assessment 1.00, certification 0.90, project 0.80, self 0.70
- Stale (>24 months): drops one rank, confidence × 0.85
- Select: highest-ranked source; tie → most recent
- Self-only discount: score × 0.70
- Conflict: any non-stale source differs by >= 30 points (self compared undiscounted)
"""
from __future__ import annotations

from datetime import date

import pandas as pd

_TRUST_RANK = {"assessment": 1, "certification": 2, "project": 3, "self": 4}
_CONFIDENCE = {"assessment": 1.00, "certification": 0.90, "project": 0.80, "self": 0.70}

_CERT_LEVELS = {"associate": 65, "professional": 80, "specialty": 85}
_SELF_LEVELS = {"beginner": 30, "intermediate": 55, "advanced": 75, "expert": 90}

_MONTH_NAMES = {
    1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun",
    7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec",
}


def normalize_evidence(row: dict) -> int:
    source = row["source"]
    value = row.get("value", "")
    detail = row.get("detail", "")

    if source == "assessment":
        return int(value)

    if source == "certification":
        lower = detail.lower()
        for level, score in _CERT_LEVELS.items():
            if level in lower:
                return score
        return 65

    if source == "project":
        months = int(value) if value else 0
        if months < 3:
            base = 40
        elif months <= 6:
            base = 55
        elif months <= 12:
            base = 65
        else:
            base = 75
        if "tech lead" in (detail or "").lower():
            base = min(base + 10, 85)
        return base

    if source == "self":
        return _SELF_LEVELS.get(value.lower(), 55)

    return 0


def _age_months(observed_on: str, today: date) -> float:
    obs = date.fromisoformat(observed_on)
    delta = today - obs
    return delta.days / 30.44


def _fmt_date(iso: str) -> str:
    d = date.fromisoformat(iso)
    return f"{d.day} {_MONTH_NAMES[d.month]} {d.year}"


def _fmt_month_year(iso: str) -> str:
    d = date.fromisoformat(iso)
    return f"{_MONTH_NAMES[d.month]} {d.year}"


def resolve_person(
    person_id: str,
    evidence_df: pd.DataFrame,
    today: date = date(2026, 10, 8),
) -> list[dict]:
    if evidence_df.empty:
        return []

    person_ev = evidence_df[evidence_df.person_id == person_id]
    if person_ev.empty:
        return []

    skills = person_ev.skill_id.unique()
    results = []

    for skill in skills:
        skill_rows = person_ev[person_ev.skill_id == skill]
        entries = []
        for _, r in skill_rows.iterrows():
            row_dict = r.to_dict()
            norm_val = normalize_evidence(row_dict)
            age = _age_months(r["observed_on"], today)
            stale = age > 24
            rank = _TRUST_RANK.get(r["source"], 5)
            conf = _CONFIDENCE.get(r["source"], 0.5)
            if stale:
                rank = min(rank + 1, 5)
                conf *= 0.85
            entries.append({
                "source": r["source"],
                "value": norm_val,
                "raw_value": r["value"],
                "observed_on": r["observed_on"],
                "detail": r.get("detail", ""),
                "rank": rank,
                "confidence": round(conf, 4),
                "stale": stale,
                "age_months": age,
            })

        entries.sort(key=lambda e: (e["rank"], -date.fromisoformat(e["observed_on"]).toordinal()))
        selected = entries[0]
        others = entries[1:]

        used_value = selected["value"]
        self_only = len(entries) == 1 and selected["source"] == "self"
        if self_only:
            used_value = int(selected["value"] * 0.70 + 0.5)

        conflict = False
        for other in entries:
            if other is selected:
                continue
            if other["stale"]:
                continue
            other_val = other["value"]
            if abs(used_value - other_val) >= 30:
                conflict = True
                break

        ignored = []
        for other in others:
            reason = _ignore_reason(selected, other)
            ignored.append({
                "source": other["source"],
                "value": other["value"],
                "reason": reason,
            })

        tooltip = _build_tooltip(selected, others, used_value, self_only, conflict, skill)

        results.append({
            "skill": skill,
            "value": used_value,
            "source": selected["source"],
            "observed_on": selected["observed_on"],
            "confidence": selected["confidence"],
            "stale": selected["stale"],
            "conflict": conflict,
            "ignored": ignored,
            "tooltip": tooltip,
        })

    return results


def _ignore_reason(selected: dict, other: dict) -> str:
    if other["stale"]:
        return f"Stale ({_fmt_month_year(other['observed_on'])})"
    if selected["rank"] < other["rank"]:
        return f"{selected['source']} is more reliable"
    if selected["rank"] == other["rank"]:
        return f"{selected['source']} is more recent"
    return f"{selected['source']} is higher ranked"


def _build_tooltip(
    selected: dict,
    others: list[dict],
    used_value: int,
    self_only: bool,
    conflict: bool,
    skill: str,
) -> str:
    parts = []

    if selected["source"] == "assessment":
        parts.append(
            f"Assessment score {selected['value']}/100, "
            f"taken {_fmt_date(selected['observed_on'])}."
        )
        for other in others:
            if other["source"] == "self":
                raw = other["raw_value"]
                parts.append(
                    f"Also self-reported as '{raw}' "
                    f"(ignored: assessment is more recent and more reliable)."
                )
            elif other["source"] == "certification":
                parts.append(
                    f"Also has certification ({other['value']}/100) "
                    f"(ignored: assessment is more reliable)."
                )
        if conflict:
            diff = max(abs(selected["value"] - o["value"]) for o in others if not o["stale"])
            parts[-1] = parts[-1].rstrip(".")
            parts[-1] += f". ⚠ Sources disagree by {diff} points."

    elif selected["source"] == "certification":
        detail = selected.get("detail", "")
        parts.append(
            f"Certification ({detail or 'certified'}), "
            f"{_fmt_month_year(selected['observed_on'])}."
        )
        for other in others:
            if other["stale"]:
                parts.append(
                    f"Also has {other['source']} ({other['value']}/100, "
                    f"{_fmt_month_year(other['observed_on'])}) "
                    f"(ignored: stale)."
                )
            else:
                parts.append(
                    f"Also has {other['source']} ({other['value']}/100) "
                    f"(ignored: certification is higher ranked)."
                )

    elif selected["source"] == "self":
        raw = selected["raw_value"]
        parts.append(
            f"Self-reported as '{raw}', "
            f"{_fmt_month_year(selected['observed_on'])}."
        )
        if self_only:
            parts.append(
                f"No assessment, certification or project record. "
                f"Discounted to {used_value}% (× 0.7)."
            )

    elif selected["source"] == "project":
        parts.append(
            f"Project history ({selected['value']}/100), "
            f"{_fmt_month_year(selected['observed_on'])}."
        )

    return " ".join(parts)


def data_quality(scores: list[dict]) -> dict:
    conflicts = sum(1 for s in scores if s["conflict"])
    stale = sum(1 for s in scores if s["stale"])
    self_only = sum(
        1 for s in scores
        if s["source"] == "self" and not s["ignored"]
    )

    line = (
        f"Shortlist: {conflicts} skill conflict{'s' if conflicts != 1 else ''}, "
        f"{stale} stale score{'s' if stale != 1 else ''}, "
        f"{self_only} self-report-only skill{'s' if self_only != 1 else ''}"
    )
    return {
        "conflicts": conflicts,
        "stale": stale,
        "self_report_only": self_only,
        "line": line,
    }
