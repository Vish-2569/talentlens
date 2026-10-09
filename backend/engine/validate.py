"""Hallucination guardrails and merge logic — pure, no I/O."""
from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, ConfigDict, model_validator

from backend.api.schemas import Level, Location, WorkMode

# ── Closed-vocabulary sets ────────────────────────────────────────────

_VALID_LEVELS = {e.value for e in Level}
_VALID_LOCATIONS = {e.value for e in Location}
_VALID_WORK_MODES = {e.value for e in WorkMode}

_ENUM_SETS: dict[str, set[str]] = {
    "level": _VALID_LEVELS,
    "location": _VALID_LOCATIONS,
    "work_mode": _VALID_WORK_MODES,
}


# ── FactsPayload (for polish — no person fields) ─────────────────────

_PERSON_PATTERNS = {"person", "employee", "emp_id", "name", "display",
                    "candidate", "ctr_id", "contractor"}


class FactsPayload(BaseModel):
    """Aggregates and option IDs only — structurally prevents person data."""
    model_config = ConfigDict(extra="forbid")

    values: dict[str, int | float | str] = {}
    option_ids: list[str] = []

    @model_validator(mode="after")
    def _no_person_fields(self) -> "FactsPayload":
        for key in self.values:
            kl = key.lower()
            for pat in _PERSON_PATTERNS:
                if pat in kl:
                    raise ValueError(
                        f"Person-related key not allowed in FactsPayload: {key}"
                    )
        return self


# ── 1. Closed vocabulary ─────────────────────────────────────────────

def validate_closed_vocab(llm_fields: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Reject any enum value not in the known set. Returns (clean, errors)."""
    clean: dict[str, Any] = {}
    errors: list[str] = []
    for field_name, field_data in llm_fields.items():
        if field_name in _ENUM_SETS and field_data is not None:
            val = field_data.get("value") if isinstance(field_data, dict) else None
            if val is not None and val not in _ENUM_SETS[field_name]:
                errors.append(f"{field_name}: '{val}' not in closed vocabulary")
                continue
        clean[field_name] = field_data
    return clean, errors


# ── 2. Span grounding ────────────────────────────────────────────────

def validate_spans(
    llm_fields: dict[str, Any], raw_text: str,
) -> tuple[dict[str, Any], list[str]]:
    """
    Check that every LLM span is a substring of *raw_text*.
    Ungrounded spans are labelled ``inferred`` and added to *needs_confirmation*.
    """
    result: dict[str, Any] = {}
    needs_confirmation: list[str] = []

    for field_name, field_data in llm_fields.items():
        if field_name in ("skills_must", "skills_nice"):
            result[field_name] = field_data
            continue
        if field_data is None or not isinstance(field_data, dict):
            result[field_name] = field_data
            continue

        span = field_data.get("span")
        value = field_data.get("value")

        if span and span in raw_text:
            idx = raw_text.index(span)
            result[field_name] = {
                "value": value,
                "span": span,
                "span_start": idx,
                "span_end": idx + len(span),
                "label": "stated",
            }
        else:
            result[field_name] = {
                "value": value,
                "span": span,
                "span_start": None,
                "span_end": None,
                "label": "inferred",
            }
            needs_confirmation.append(field_name)

    return result, needs_confirmation


# ── 3. Regex cross-check ─────────────────────────────────────────────

_NUMERIC_FIELDS = ("budget_lpa", "min_years", "need_by_days")


def cross_check_regex_llm(
    regex_fields: dict[str, Any],
    llm_fields: dict[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    """For budget / years / days: if regex and LLM disagree, regex wins."""
    merged = dict(regex_fields)
    flags: list[str] = []

    for field in _NUMERIC_FIELDS:
        rf = regex_fields.get(field)
        lf = llm_fields.get(field)
        if rf is None or lf is None:
            continue
        r_val = rf.get("value") if isinstance(rf, dict) else None
        l_val = lf.get("value") if isinstance(lf, dict) else None
        if l_val is not None and r_val is not None:
            try:
                if float(r_val) != float(l_val):
                    flags.append(
                        f"{field}: regex={r_val} vs llm={l_val}, using regex"
                    )
            except (TypeError, ValueError):
                pass

    return merged, flags


# ── 5. Numeric grounding for polish() ────────────────────────────────

_NUM_RE = re.compile(
    r"(?:₹\s?)?(\d+(?:\.\d+)?)\s*"
    r"(?:L|lakh|lakhs?|%|days?|weeks?|months?|years?)?",
    re.I,
)


def validate_polish_numbers(text: str, facts: FactsPayload) -> bool:
    """Every number in *text* must exist in the *facts* value set."""
    allowed: set[float] = set()
    for v in facts.values.values():
        if isinstance(v, (int, float)):
            allowed.add(float(v))
            if isinstance(v, float) and v == int(v):
                allowed.add(float(int(v)))

    for m in _NUM_RE.finditer(text):
        num_str = m.group(1)
        try:
            num = float(num_str)
        except ValueError:
            continue
        if num not in allowed:
            return False
    return True


# ── D. Merge function ────────────────────────────────────────────────

def merge_parse(
    regex_fields: dict[str, Any],
    llm_result: dict[str, Any] | None,
    raw_text: str,
) -> dict[str, Any]:
    """
    final_parse = regex parse, filled by validated LLM fields only where
    regex was empty.  Regex wins on numeric conflicts.
    """
    if llm_result is None:
        return regex_fields

    vocab_clean, vocab_errors = validate_closed_vocab(llm_result)
    span_clean, needs_confirmation = validate_spans(vocab_clean, raw_text)
    _, flags = cross_check_regex_llm(regex_fields, span_clean)

    merged = dict(regex_fields)
    for field, data in span_clean.items():
        if field in ("skills_must", "skills_nice"):
            continue
        if field not in merged or merged.get(field) is None:
            merged[field] = data

    if flags:
        merged.setdefault("_flags", []).extend(flags)
    if needs_confirmation:
        merged.setdefault("_needs_confirmation", []).extend(needs_confirmation)
    if vocab_errors:
        merged.setdefault("_vocab_errors", []).extend(vocab_errors)

    return merged
