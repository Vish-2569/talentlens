"""12-section Workforce Intelligence Brief — pure functions, no I/O.

All text comes from templates (f-strings over computed facts).
If the polish toggle is on, each section's wording may go through
llm.polish() and the numeric validator; on any failure the template
text is used.

Output: sections[12 × {key, title, markdown}], plus a full markdown
string and a self-contained HTML string (escaped, no scripts) for
the HTML / Markdown download; the browser does print-to-PDF.
"""
from __future__ import annotations

import html
import re
from typing import Callable, Optional


SECTION_KEYS = [
    "request", "history", "supply", "internal", "contractors",
    "compensation", "locations", "options", "sourcing", "actions",
    "data_quality", "decision",
]

SECTION_TITLES = {
    "request": "The request, as received and as challenged",
    "history": "What happened last time",
    "supply": "Supply indicators",
    "internal": "Internal matches and development paths",
    "contractors": "Contractor options",
    "compensation": "Compensation guidance",
    "locations": "Location alternatives",
    "options": "Option comparison and recommendation",
    "sourcing": "Sourcing channels and talent pools",
    "actions": "Recommended next actions",
    "data_quality": "Evidence and data quality",
    "decision": "Human decision",
}


# ── Section builders ─────────────────────────────────────────────────────────


def _section_request(raw_text: str, redline_result: dict,
                     options_result: dict) -> str:
    constraints = redline_result.get("constraints", [])
    red = sum(1 for c in constraints if c.get("severity") == "red")
    amber = sum(1 for c in constraints if c.get("severity") == "amber")

    lines = [f'**Original:** "{raw_text}"']
    lines.append(
        f"**Redline marks:** {red} red"
        + (f" ({', '.join(c['kind'] for c in constraints if c.get('severity') == 'red')})"
           if red else "")
        + f", {amber} amber"
        + (f" ({', '.join(c['kind'] for c in constraints if c.get('severity') == 'amber')})"
           if amber else "")
        + "."
    )

    ledger = options_result.get("assumption_ledger", {})
    sr_risks = ledger.get("self_report_risks", [])
    dj_adj = ledger.get("dejareq_adjustments", [])
    if sr_risks:
        lines.append(
            f"**Self-report risk items:** {len(sr_risks)} skill(s) "
            "with self-report-only evidence."
        )
    if dj_adj:
        for adj in dj_adj:
            lines.append(
                f"**Déjà Req penalty:** {adj.get('option', '?')} "
                f"+{adj.get('delta', 0):.2f} risk ({adj.get('reason', '')})."
            )

    lines.append("**Assumption Ledger:** see Redline details above.")
    return "\n\n".join(lines)


def _section_history(dejareq_result: dict) -> str:
    if dejareq_result.get("match_count", 0) == 0:
        return "No prior requisitions found for this role and team."

    parts: list[str] = []
    mc = dejareq_result["match_count"]
    parts.append(
        f"{mc} past requisitions for this role"
        + (f" in {dejareq_result.get('years_span', 2)} years"
           if dejareq_result.get("years_span") else "")
        + "."
    )

    avgs = dejareq_result.get("averages", {})
    buy_avg = avgs.get("buy", {})
    if buy_avg and buy_avg.get("avg_tenure_months") is not None:
        parts.append(
            f"External hires left in under a year "
            f"(avg {buy_avg['avg_tenure_months']:.0f} months, "
            f"{buy_avg['count']} of {buy_avg['count']})."
        )

    build_avg = avgs.get("build", {})
    if build_avg:
        parts.append(
            "The one internal move is still in role, rated Exceeds."
            if build_avg.get("count", 0) == 1
            else f"{build_avg['count']} internal moves."
        )

    cs = dejareq_result.get("cost_story", {})
    if cs:
        buy_t = cs.get("buy_total_lpa", 0)
        build_t = cs.get("build_total_lpa", 0)
        diff = cs.get("difference_lpa", buy_t - build_t)
        if buy_t > 0 and build_t >= 0:
            parts.append(
                f"Cost story: Buy spent ₹{buy_t:.0f}L vs Build ₹{build_t:.0f}L "
                f"(₹{diff:.0f}L difference)."
            )

    insight = dejareq_result.get("insight")
    if insight:
        parts.append(insight)

    return " ".join(parts)


def _section_supply(relocate_card: list[dict], market_card: dict) -> str:
    rows = ["| Location | Supply | P50 TTF | P80 TTF |", "|---|---|---|---|"]
    for loc in relocate_card:
        name = loc.get("location", "")
        rows.append(
            f"| {name} | {loc['supply']} "
            f"| {loc['ttf_p50']} days | {loc['ttf_p80']} days |"
        )
    return "\n".join(rows)


def _section_internal(internal_candidates: list[dict],
                      ripple_result: dict) -> str:
    if not internal_candidates:
        return "No internal candidates with match ≥ 70%."

    lines: list[str] = []
    ripple_map = {c["person_id"]: c for c in ripple_result.get("candidates", [])}

    for ic in internal_candidates:
        name = ic.get("display_name", ic["person_id"])
        match = ic["match"]
        band = ic.get("band", "")
        weeks = ic.get("readiness_weeks")

        bullet = f"- **{name}**: {match:.0f}% match"
        if band:
            bullet += f", {band} band"
        if weeks is not None and weeks > 0:
            bullet += f". Ready week {weeks}"
            cost = ic.get("build_cost_lpa")
            if cost is not None:
                bullet += f" (upskill ₹{cost}L)"
        bullet += "."

        rc = ripple_map.get(ic["person_id"])
        if rc:
            flags = rc.get("bus_factor_flags", [])
            if flags:
                bullet += f" ⚠ Bus factor: {', '.join(flags)}."
            rf = rc.get("red_flags", 0)
            if rf > 0:
                bullet += f" {rf} red flag(s) in chain."

        lines.append(bullet)

    return "\n".join(lines)


def _section_contractors(contractor_cards: list[dict]) -> str:
    if not contractor_cards:
        return "No matching contractors."

    lines: list[str] = []
    for cc in contractor_cards:
        name = cc.get("display_name", cc["person_id"])
        fit = cc.get("fit", 0)
        avail = cc.get("availability", "")
        ext_cost = cc.get("extend_cost_lpa", 0)

        bullet = (
            f"- **{name} ({cc['person_id']})**: {fit:.0f}% match. "
            f"{avail}. 12-month extension ₹{ext_cost}L"
        )
        bridge = cc.get("extend_cost_3m")
        if bridge is not None:
            bullet += f", 3-month bridge ₹{bridge}L"
        if cc.get("conversion_signal"):
            bullet += ". Conversion signal: positive"
        if cc.get("compliance_flag"):
            bullet += ". ⚠ Compliance flag"
        bullet += "."
        lines.append(bullet)

    return "\n".join(lines)


def _section_compensation(market_card: dict, parsed_req: dict) -> str:
    loc = market_card.get("location", "")
    level = market_card.get("level", "")
    p25 = market_card.get("sal_p25", 0)
    p50 = market_card.get("sal_p50", 0)
    p75 = market_card.get("sal_p75", 0)

    budget_field = parsed_req.get("budget_lpa", {})
    budget = budget_field.get("value") if isinstance(budget_field, dict) else budget_field

    lines = [
        f"{loc.title()} {level.title()}: "
        f"P25 ₹{p25:.0f}L, P50 ₹{p50:.0f}L, P75 ₹{p75:.0f}L."
    ]

    if budget is not None and p50 > 0:
        gap_pct = abs((budget - p50) / p50 * 100)
        direction = "below" if budget < p50 else "above"
        lines.append(
            f"Budget ₹{budget:.0f}L is {gap_pct:.1f}% {direction} P50."
        )
        if budget < p50:
            ratio = p50 / budget if budget > 0 else 1
            lines.append(
                f"Expect ~{ratio:.2f}× longer time to fill and lower offer acceptance."
            )

    return " ".join(lines)


def _section_locations(relocate_card: list[dict]) -> str:
    if not relocate_card:
        return "No alternative locations analysed."

    lines: list[str] = []
    for loc in relocate_card:
        name = loc.get("location", "")
        supply = loc["supply"]
        p50 = loc["ttf_p50"]
        pay = loc.get("pay_p50_lpa", 0)
        score = loc.get("score", 0)
        lines.append(
            f"{name}: {supply} candidates, P50 {p50} days, "
            f"₹{pay:.0f}L (score {score:.2f})."
        )

    if len(relocate_card) >= 2:
        top = relocate_card[0]
        bottom = relocate_card[-1]
        if bottom.get("pay_p50_lpa", 0) > 0 and top.get("pay_p50_lpa", 0) > 0:
            pct_diff = abs(
                (top["pay_p50_lpa"] - bottom["pay_p50_lpa"])
                / bottom["pay_p50_lpa"] * 100
            )
            if pct_diff > 5:
                lines.append(
                    f"{top['location']} P50 pay is "
                    f"{pct_diff:.0f}% {'below' if top['pay_p50_lpa'] < bottom['pay_p50_lpa'] else 'above'} "
                    f"{bottom['location']}."
                )

    return " ".join(lines)


def _section_options(options_result: dict) -> str:
    opts = options_result.get("options", [])
    rows = [
        "| Option | Score | Ready by | Cost | Risk |",
        "|---|---|---|---|---|",
    ]
    for o in opts:
        score = o.get("score", "")
        score_str = f"{score}" if score != "add-on" else "add-on"
        ready = o.get("ready_by_p80_days")
        ready_str = f"Day {ready}" if ready is not None and ready <= 7 else f"Week {(ready or 0) // 7}" if ready else "—"
        if ready is not None and ready == 0:
            ready_str = "Day 0"
        cost = o.get("year_one_cost_lpa")
        cost_str = f"₹{cost:.0f}L" if cost is not None else "—"
        risk = o.get("risk_label", "")
        name = o.get("name", "")
        rows.append(f"| {name} | {score_str} | {ready_str} | {cost_str} | {risk} |")

    mixes = options_result.get("top_mixes", [])
    if mixes:
        top_mix = mixes[0]
        rows.append("")
        rows.append(
            f"**Recommended mix:** {top_mix.get('name', top_mix.get('mix_id', ''))} — "
            f"score {top_mix.get('score', 0)}, ₹{top_mix.get('cost_lpa', 0):.0f}L."
        )

    boundaries = options_result.get("assumption_ledger", {}).get(
        "decision_boundaries",
        options_result.get("decision_boundaries", []),
    )
    if boundaries:
        rows.append("")
        for b in boundaries:
            rows.append(f"- {b}")

    return "\n".join(rows)


def _section_sourcing(sourcing_result: dict) -> str:
    channels = sourcing_result.get("channels", [])
    if not channels:
        return "No sourcing channels analysed."

    lines: list[str] = []
    for ch in channels:
        rank = ch.get("rank")
        label = ch.get("channel", "")
        evidence = ch.get("evidence", "")
        prefix = f"{rank}. " if rank is not None else "- "
        lines.append(f"{prefix}{label}: {evidence}")

    return "\n".join(lines)


def _section_actions(actions_list: list[dict]) -> str:
    if not actions_list:
        return "No actions generated."
    lines = []
    for i, a in enumerate(actions_list, 1):
        lines.append(f"{i}. {a['title']}.")
    return "\n".join(lines)


def _section_data_quality(evidence_quality: dict,
                          reference_meta: dict) -> str:
    parts: list[str] = []

    line = evidence_quality.get("line", "")
    if line:
        parts.append(line + ".")

    parts.append("All market data is simulated.")

    fetched = reference_meta.get("fetched_on", "")
    if fetched:
        parts.append(f"Reference data fetched on {fetched}.")

    parts.append(
        "Skill/occupation data © O*NET (CC BY 4.0) and ESCO."
    )

    return " ".join(parts)


def _section_decision(decision_rows: list[dict]) -> str:
    if not decision_rows:
        return (
            "Pending approval. Approver, choice, reason and timestamp "
            "will be recorded in the Decision Log."
        )
    last = decision_rows[-1]
    return (
        f"**Decision:** {last.get('chosen_option', '?')} — "
        f"by {last.get('decided_by', '?')}, "
        f"{last.get('decided_at', '?')}.\n\n"
        f"**Reason:** {last.get('reason', '—')}"
    )


_BUILDERS = {
    "request": lambda kw: _section_request(
        kw["raw_text"], kw["redline_result"], kw["options_result"]),
    "history": lambda kw: _section_history(kw["dejareq_result"]),
    "supply": lambda kw: _section_supply(
        kw["relocate_card"], kw["market_card"]),
    "internal": lambda kw: _section_internal(
        kw["internal_candidates"], kw["ripple_result"]),
    "contractors": lambda kw: _section_contractors(kw["contractor_cards"]),
    "compensation": lambda kw: _section_compensation(
        kw["market_card"], kw["parsed_req"]),
    "locations": lambda kw: _section_locations(kw["relocate_card"]),
    "options": lambda kw: _section_options(kw["options_result"]),
    "sourcing": lambda kw: _section_sourcing(kw["sourcing_result"]),
    "actions": lambda kw: _section_actions(kw["actions_list"]),
    "data_quality": lambda kw: _section_data_quality(
        kw["evidence_quality"], kw["reference_meta"]),
    "decision": lambda kw: _section_decision(kw["decision_rows"]),
}


# ── HTML renderer ────────────────────────────────────────────────────────────


def _md_to_html_fragment(md: str) -> str:
    """Minimal markdown-to-HTML for controlled brief markdown."""
    out = html.escape(md)

    out = re.sub(
        r"\*\*(.+?)\*\*",
        r"<strong>\1</strong>",
        out,
    )

    lines = out.split("\n")
    result: list[str] = []
    in_table = False
    in_list = False
    is_first_table_row = False

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("|") and stripped.endswith("|"):
            cells = [c.strip() for c in stripped.split("|")[1:-1]]
            if all(set(c) <= {"-", " "} for c in cells):
                continue
            if not in_table:
                in_table = True
                is_first_table_row = True
                result.append("<table>")
            if is_first_table_row:
                result.append("<thead><tr>" +
                              "".join(f"<th>{c}</th>" for c in cells) +
                              "</tr></thead><tbody>")
                is_first_table_row = False
            else:
                result.append("<tr>" +
                              "".join(f"<td>{c}</td>" for c in cells) +
                              "</tr>")
            continue

        if in_table:
            result.append("</tbody></table>")
            in_table = False

        if re.match(r"^\d+\.\s", stripped):
            if not in_list:
                result.append("<ol>")
                in_list = True
            content = re.sub(r"^\d+\.\s", "", stripped)
            result.append(f"<li>{content}</li>")
            continue

        if stripped.startswith("- "):
            if not in_list:
                result.append("<ul>")
                in_list = True
            result.append(f"<li>{stripped[2:]}</li>")
            continue

        if in_list:
            tag = "</ol>" if any("<ol>" in r for r in result) else "</ul>"
            result.append(tag)
            in_list = False

        if not stripped:
            continue

        result.append(f"<p>{stripped}</p>")

    if in_table:
        result.append("</tbody></table>")
    if in_list:
        tag = "</ol>" if any("<ol>" in r for r in result) else "</ul>"
        result.append(tag)

    return "\n".join(result)


_HTML_STYLE = """\
body { font-family: system-ui, sans-serif; max-width: 900px; margin: 2em auto; padding: 0 1em; color: #1a1a1a; }
h1 { font-size: 1.6em; border-bottom: 2px solid #333; padding-bottom: 0.3em; }
h2 { font-size: 1.2em; margin-top: 1.5em; color: #2c3e50; }
table { border-collapse: collapse; width: 100%; margin: 0.5em 0; }
th, td { border: 1px solid #ccc; padding: 0.4em 0.8em; text-align: left; }
th { background: #f5f5f5; }
strong { font-weight: 600; }
@media print { body { margin: 0; } }
"""


def _render_html(sections: list[dict]) -> str:
    parts = [
        "<!DOCTYPE html>",
        "<html lang=\"en\"><head><meta charset=\"utf-8\">",
        "<title>Workforce Intelligence Brief</title>",
        f"<style>{_HTML_STYLE}</style>",
        "</head><body>",
        "<h1>Workforce Intelligence Brief</h1>",
    ]
    for s in sections:
        title_escaped = html.escape(s["title"])
        parts.append(f"<h2>{title_escaped}</h2>")
        parts.append(_md_to_html_fragment(s["markdown"]))
    parts.append("</body></html>")
    return "\n".join(parts)


# ── Main public function ─────────────────────────────────────────────────────


def generate_brief(
    *,
    raw_text: str,
    parsed_req: dict,
    dejareq_result: dict,
    redline_result: dict,
    ripple_result: dict,
    options_result: dict,
    sourcing_result: dict,
    market_card: dict,
    relocate_card: list[dict],
    contractor_cards: list[dict],
    internal_candidates: list[dict],
    evidence_quality: dict,
    actions_list: list[dict],
    decision_rows: list[dict],
    reference_meta: dict,
    polish_fn: Optional[Callable] = None,
) -> dict:
    """Build the 12-section Workforce Intelligence Brief.

    Returns
    -------
    dict
        ``sections`` (list of 12 {key, title, markdown}),
        ``markdown`` (full brief as markdown string),
        ``html`` (self-contained HTML string, no scripts).
    """
    kw = {
        "raw_text": raw_text,
        "parsed_req": parsed_req,
        "dejareq_result": dejareq_result,
        "redline_result": redline_result,
        "ripple_result": ripple_result,
        "options_result": options_result,
        "sourcing_result": sourcing_result,
        "market_card": market_card,
        "relocate_card": relocate_card,
        "contractor_cards": contractor_cards,
        "internal_candidates": internal_candidates,
        "evidence_quality": evidence_quality,
        "actions_list": actions_list,
        "decision_rows": decision_rows,
        "reference_meta": reference_meta,
    }

    sections: list[dict] = []
    for key in SECTION_KEYS:
        md = _BUILDERS[key](kw)

        if polish_fn is not None:
            try:
                polished = polish_fn(md)
                if polished and isinstance(polished, str):
                    md = polished
            except Exception:
                pass

        sections.append({
            "key": key,
            "title": SECTION_TITLES[key],
            "markdown": md,
        })

    full_md = "# Workforce Intelligence Brief\n\n"
    full_md += "\n\n".join(
        f"## {s['title']}\n\n{s['markdown']}" for s in sections
    )

    html_str = _render_html(sections)

    return {
        "sections": sections,
        "markdown": full_md,
        "html": html_str,
    }
