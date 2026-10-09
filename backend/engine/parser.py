"""Regex pre-parser for requisition text — pure, no I/O."""
from __future__ import annotations

import re
from typing import Any

import pandas as pd

REQUIRED_FIELDS = ("level", "location", "work_mode")

# ── Numeric patterns (Section 8) ─────────────────────────────────────

_BUDGET_RE = re.compile(r"₹\s?(\d+)\s?(?:L|lakh|lakhs)\b", re.I)
_YEARS_RE = re.compile(r"(\d+)\+?\s*years?\b", re.I)
_DEADLINE_RE = re.compile(r"(\d+)\s*days?\b", re.I)

# ── Enum patterns ─────────────────────────────────────────────────────

_CITY_MAP: dict[str, re.Pattern[str]] = {
    "bengaluru": re.compile(r"\b(?:bengaluru|bangalore)\b", re.I),
    "hyderabad": re.compile(r"\bhyderabad\b", re.I),
    "pune": re.compile(r"\bpune\b", re.I),
    "remote_india": re.compile(r"\bremote[\s\-]*india\b", re.I),
}

_WORK_MODE_MAP: dict[str, re.Pattern[str]] = {
    "onsite": re.compile(r"\b(?:on[\s\-]*site|onsite|in[\s\-]*office)\b", re.I),
    "hybrid": re.compile(r"\bhybrid\b", re.I),
    "remote": re.compile(r"\bremote\b(?![\s\-]*india)", re.I),
}

_LEVEL_MAP: dict[str, re.Pattern[str]] = {
    "junior": re.compile(r"\bjunior\b|\bjr\.?(?=\W|$)", re.I),
    "mid": re.compile(r"\bmid(?:dle)?(?:[\s\-]*level)?\b", re.I),
    "senior": re.compile(r"\bsenior\b|\bsr\.?(?=\W|$)", re.I),
    "lead": re.compile(r"\blead\b", re.I),
}

# ── Must / nice cue words ────────────────────────────────────────────

_MUST_CUE = re.compile(
    r"\b(?:must\s+(?:know|have)|required|essential|mandatory)\b", re.I,
)
_NICE_CUE = re.compile(
    r"\b(?:nice\s+to\s+have|good\s+to\s+have|bonus|(?:a\s+)?plus"
    r"|prefer(?:red|ably)?)\b",
    re.I,
)


# ── Helpers ───────────────────────────────────────────────────────────

def _field(
    value: Any, span: str, start: int, end: int, label: str = "stated",
) -> dict[str, Any]:
    return {
        "value": value,
        "span": span,
        "span_start": start,
        "span_end": end,
        "label": label,
    }


def _match_enum(
    text: str, patterns: dict[str, re.Pattern[str]],
) -> list[tuple[str, re.Match[str]]]:
    return [(val, m) for val, pat in patterns.items() if (m := pat.search(text))]


def _importance_at(pos: int, cues: list[tuple[int, str]]) -> str:
    imp = "must"
    for cue_end, cue_type in cues:
        if cue_end <= pos:
            imp = cue_type
        else:
            break
    return imp


def _build_skill_lookup(
    skills_df: pd.DataFrame,
    skill_aliases_df: pd.DataFrame,
) -> list[tuple[str, str, re.Pattern[str]]]:
    entries: list[tuple[str, str]] = []
    for _, row in skill_aliases_df.iterrows():
        entries.append((str(row["alias"]).strip(), str(row["skill_id"])))
    for _, row in skills_df.iterrows():
        entries.append((str(row["id"]).strip(), str(row["id"])))
        if pd.notna(row.get("name")):
            entries.append((str(row["name"]).strip(), str(row["id"])))

    seen: set[tuple[str, str]] = set()
    unique: list[tuple[str, str]] = []
    for token, sid in entries:
        key = (token.lower(), sid)
        if key not in seen:
            seen.add(key)
            unique.append((token, sid))
    unique.sort(key=lambda x: len(x[0]), reverse=True)

    result: list[tuple[str, str, re.Pattern[str]]] = []
    for token, sid in unique:
        escaped = re.escape(token).replace(" ", r"\s+")
        try:
            pat = re.compile(r"\b" + escaped + r"\b", re.I)
            result.append((token, sid, pat))
        except re.error:
            pass
    return result


def _extract_skills(
    text: str,
    skills_df: pd.DataFrame,
    skill_aliases_df: pd.DataFrame,
) -> list[dict[str, Any]]:
    cues: list[tuple[int, str]] = sorted(
        [(m.end(), "must") for m in _MUST_CUE.finditer(text)]
        + [(m.end(), "nice") for m in _NICE_CUE.finditer(text)],
        key=lambda x: x[0],
    )
    lookups = _build_skill_lookup(skills_df, skill_aliases_df)
    found: dict[str, dict[str, Any]] = {}
    used: list[tuple[int, int]] = []

    for _token, skill_id, pat in lookups:
        for m in pat.finditer(text):
            if any(m.start() < e and m.end() > s for s, e in used):
                continue
            if skill_id in found:
                continue
            found[skill_id] = {
                "skill_id": skill_id,
                "importance": _importance_at(m.start(), cues),
                "confidence": 1.0,
                "span": m.group(),
                "span_start": m.start(),
                "span_end": m.end(),
            }
            used.append((m.start(), m.end()))

    return list(found.values())


# ── Main entry point ──────────────────────────────────────────────────

def regex_parse(
    text: str,
    skills_df: pd.DataFrame,
    skill_aliases_df: pd.DataFrame,
) -> tuple[dict[str, Any], list[str]]:
    """
    Regex pre-parser. Runs FIRST before any LLM call.

    Returns (fields, needs_llm) where *needs_llm* lists required field
    names that are empty or ambiguous and therefore need LLM extraction.
    """
    fields: dict[str, Any] = {}

    for name, patterns in [
        ("level", _LEVEL_MAP),
        ("location", _CITY_MAP),
        ("work_mode", _WORK_MODE_MAP),
    ]:
        hits = _match_enum(text, patterns)
        if len(hits) == 1:
            val, m = hits[0]
            fields[name] = _field(val, m.group(), m.start(), m.end())
        elif len(hits) > 1:
            val, m = hits[0]
            f = _field(val, m.group(), m.start(), m.end())
            f["ambiguous"] = True
            fields[name] = f

    bm = _BUDGET_RE.search(text)
    if bm:
        fields["budget_lpa"] = _field(
            int(bm.group(1)), bm.group(), bm.start(), bm.end(),
        )

    ym = _YEARS_RE.search(text)
    if ym:
        fields["min_years"] = _field(
            int(ym.group(1)), ym.group(), ym.start(), ym.end(),
        )

    dm = _DEADLINE_RE.search(text)
    if dm:
        fields["need_by_days"] = _field(
            int(dm.group(1)), dm.group(), dm.start(), dm.end(),
        )

    fields["skills"] = _extract_skills(text, skills_df, skill_aliases_df)

    needs_llm = [
        f for f in REQUIRED_FIELDS
        if f not in fields or fields[f].get("ambiguous")
    ]
    return fields, needs_llm
