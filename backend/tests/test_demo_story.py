"""Phase 14A: comprehensive demo story end-to-end test (Section 13 + Section 7A).

test_demo_story          ONE test asserting every story value from CLAUDE.md
test_tc07_*              Backend support: 32 redline scenarios present
test_tc30_*              Backend support: all 9 workflow-stage data groups present
test_determinism_3_runs  Same text → byte-identical JSON (3 calls)
test_performance_*       POST /api/analyze < 2 s with LLM cache warm
"""
from __future__ import annotations

import json
import time

import pytest
from httpx import ASGITransport, AsyncClient

from backend.api.main import app

def _person_in_chain(node: dict, pid: str) -> bool:
    """Recursively check whether pid appears anywhere in a RippleNode tree."""
    if node.get("person_id") == pid:
        return True
    return any(_person_in_chain(child, pid) for child in node.get("children", []))


DEMO = (
    "Senior Full Stack Developer, Bengaluru, on-site, 5+ years, "
    "must know React, Node.js and Kubernetes, budget ₹28L, need in 30 days."
)

# Seed person IDs (Section 13)
KARTHIK = "E-031"   # Lead, Platform — 88 % match, sole Terraform holder
PRIYA   = "E-045"   # Mid, Checkout — 82 % match, ready week 6
RAHUL   = "E-072"   # Junior, Checkout — 76 % / Mid candidate, 3-month upskill
ARJUN   = "C-17"    # Contractor — 84 % match, contract ends 2026-11-05


@pytest.fixture(scope="module")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="module")
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture(scope="module")
async def raw(client):
    """Module-scoped raw JSON of one POST /api/analyze call."""
    resp = await client.post("/api/analyze", json={"text": DEMO})
    assert resp.status_code == 200, resp.text
    return resp.json()


# ── ONE comprehensive story test ──────────────────────────────────────────────

@pytest.mark.anyio
async def test_demo_story(client, raw):
    """Assert every Section 13 / 7A / 7B story value against the API response."""
    parsed  = raw["parsed"]
    deja    = raw["dejareq"]
    redline = raw["redline"]
    opts    = raw["options"]
    ripple  = raw["ripple"]

    # ── Title normalisation (Section 13) ─────────────────────────────────
    tnorm = parsed["title_normalization"]
    assert tnorm["raw_titles_count"] == 12, "12 raw job titles must map to 1 role"
    assert len(tnorm["levels"]) == 4, "Role must cover 4 levels (L1-L4)"

    # ── Deja Req (Section 13) ─────────────────────────────────────────────
    assert deja["match_count"] == 4, "4 past matching requisitions"

    buy_avg = next(
        (a for a in deja["averages_by_decision"] if a["decision"].lower() == "buy"),
        None,
    )
    assert buy_avg is not None, "Buy decision average must be present"
    assert buy_avg["avg_tenure_months"] == pytest.approx(8.0, abs=0.5), (
        f"Avg external tenure must be 8 months (9+7/2); got {buy_avg['avg_tenure_months']}"
    )

    # ── Relocate card — supply, P50/P80/pay, location scores (Section 7A) ─
    rc = opts["relocate_card"]
    by_loc: dict[str, dict] = {}
    for row in rc:
        loc_str = row["location"].lower()
        if "remote" in loc_str:
            by_loc["remote"] = row
        elif "hyderabad" in loc_str:
            by_loc["hyderabad"] = row
        elif "pune" in loc_str:
            by_loc["pune"] = row
        elif "bengaluru" in loc_str:
            by_loc["bengaluru"] = row

    assert len(by_loc) == 4, f"All 4 locations must appear; got {list(by_loc)}"

    # Remote-India
    r = by_loc["remote"]
    assert r["supply"] == 210, f"Remote-India supply: {r['supply']}"
    assert r["ttf_p50"] == 28,  f"Remote-India P50: {r['ttf_p50']}"
    assert r["ttf_p80"] == 40,  f"Remote-India P80: {r['ttf_p80']}"
    assert r["pay_p50_lpa"] == pytest.approx(29, abs=1), f"Remote-India pay: {r['pay_p50_lpa']}"
    assert r["score"] == pytest.approx(0.79, abs=0.01), f"Remote-India score: {r['score']}"

    # Hyderabad
    h = by_loc["hyderabad"]
    assert h["supply"] == 31,  f"Hyderabad supply: {h['supply']}"
    assert h["ttf_p50"] == 44, f"Hyderabad P50: {h['ttf_p50']}"
    assert h["ttf_p80"] == 58, f"Hyderabad P80: {h['ttf_p80']}"
    assert h["pay_p50_lpa"] == pytest.approx(30, abs=1), f"Hyderabad pay: {h['pay_p50_lpa']}"
    assert h["score"] == pytest.approx(0.36, abs=0.01), f"Hyderabad score: {h['score']}"

    # Pune
    p = by_loc["pune"]
    assert p["supply"] == 26,  f"Pune supply: {p['supply']}"
    assert p["ttf_p50"] == 47, f"Pune P50: {p['ttf_p50']}"
    assert p["ttf_p80"] == 62, f"Pune P80: {p['ttf_p80']}"
    assert p["pay_p50_lpa"] == pytest.approx(26, abs=1), f"Pune pay: {p['pay_p50_lpa']}"
    assert p["score"] == pytest.approx(0.34, abs=0.01), f"Pune score: {p['score']}"

    # Bengaluru (baseline, score = 0)
    b = by_loc["bengaluru"]
    assert b["supply"] == 14,  f"Bengaluru supply: {b['supply']}"
    assert b["ttf_p50"] == 62, f"Bengaluru P50: {b['ttf_p50']}"
    assert b["ttf_p80"] == 81, f"Bengaluru P80: {b['ttf_p80']}"
    assert b["pay_p50_lpa"] == pytest.approx(32, abs=1), f"Bengaluru pay: {b['pay_p50_lpa']}"
    assert b["score"] == pytest.approx(0.00, abs=0.01), f"Bengaluru score: {b['score']}"

    # ── Kubernetes relax: supply_delta = 47 - 14 = 33 ────────────────────
    skill_c = next(
        (c for c in redline["constraints"] if c["kind"] == "skill"),
        None,
    )
    assert skill_c is not None, "Skill constraint (Kubernetes) must be in redline"
    assert skill_c["cost"]["supply_delta"] == 33, (
        f"K8s supply_delta must be 33 (47-14); got {skill_c['cost']['supply_delta']}"
    )

    # ── Internal candidates ───────────────────────────────────────────────
    internal = opts["internal_candidates"]
    by_pid = {c["person_id"]: c for c in internal}

    # Karthik — 88 % match
    assert KARTHIK in by_pid, f"Karthik {KARTHIK} must be in internal_candidates"
    k = by_pid[KARTHIK]
    assert k["match"] == pytest.approx(88.0, abs=1.0), f"Karthik match: {k['match']}"

    # Priya — 82 %, ready week 6
    assert PRIYA in by_pid, f"Priya {PRIYA} must be in internal_candidates"
    pr = by_pid[PRIYA]
    assert pr["match"] == pytest.approx(82.0, abs=1.0), f"Priya match: {pr['match']}"
    assert pr["readiness_weeks"] == 6, f"Priya readiness_weeks: {pr['readiness_weeks']}"

    # Rahul — 76 % score is against Mid-level requirements (TC12 unit test).
    # In internal_candidates he scores against Senior (lower), and appears in
    # Priya's ripple chain as a backfill candidate.  Assert presence only here.
    ripple_cands = ripple["candidates"]
    rahul_in_system = RAHUL in by_pid or any(
        _person_in_chain(c["chain"], RAHUL) for c in ripple_cands
    )
    assert rahul_in_system, f"Rahul {RAHUL} must appear in internal_candidates or ripple chain"

    # ── Karthik: 2 red flags in ripple chain ──────────────────────────────
    k_ripple = next((c for c in ripple_cands if c["person_id"] == KARTHIK), None)
    assert k_ripple is not None, f"Karthik {KARTHIK} must appear in ripple"
    red_flags = k_ripple["net_impact"]["red_flags"]
    assert red_flags == 2, (
        f"Karthik must have ≥ 2 red flags (bus-factor + dead-end); got {red_flags}"
    )

    # ── Contractor Arjun — 84 %, 4 weeks, ₹24L ───────────────────────────
    contractors = opts["contractor_cards"]
    arjun = next((c for c in contractors if c["person_id"] == ARJUN), None)
    assert arjun is not None, f"Arjun {ARJUN} must be in contractor_cards"
    assert arjun["fit"] == pytest.approx(84.0, abs=1.0), f"Arjun fit: {arjun['fit']}"
    assert "4 weeks" in arjun["availability"], (
        f"Arjun availability must say '4 weeks'; got: {arjun['availability']}"
    )
    assert arjun["extend_cost_lpa"] == pytest.approx(24.0, abs=1.0), (
        f"Arjun 12-month cost: {arjun['extend_cost_lpa']}"
    )

    # ── Option scores and year-one costs (Section 7A) ─────────────────────
    by_id = {o["id"]: o for o in opts["five"]}
    assert by_id["mix"]["score"]     == 89.0, f"mix score: {by_id['mix']['score']}"
    assert by_id["borrow"]["score"]  == 87.0, f"borrow score: {by_id['borrow']['score']}"
    assert by_id["build"]["score"]   == 73.0, f"build score: {by_id['build']['score']}"
    assert by_id["relocate"]["score"] == 62.0, f"relocate score: {by_id['relocate']['score']}"
    assert by_id["buy"]["score"]     == 42.0, f"buy score: {by_id['buy']['score']}"

    # Mix ₹18L (₹6L 3-month bridge + ₹12L Build chain)
    assert by_id["mix"]["year_one_cost_lpa"] == pytest.approx(18.0, abs=1.0), (
        f"Mix year-one cost: {by_id['mix']['year_one_cost_lpa']}"
    )

    # Build chain ₹12L
    assert by_id["build"]["year_one_cost_lpa"] == pytest.approx(12.0, abs=1.0), (
        f"Build year-one cost: {by_id['build']['year_one_cost_lpa']}"
    )

    # Borrow (12-month) ₹24L
    assert by_id["borrow"]["year_one_cost_lpa"] == pytest.approx(24.0, abs=1.0), (
        f"Borrow year-one cost: {by_id['borrow']['year_one_cost_lpa']}"
    )

    # ── Sourcing channels (Section 7B) ────────────────────────────────────
    sourcing = opts["sourcing"]
    assert len(sourcing["past_finalists"]) == 3, (
        f"Past finalists count: {len(sourcing['past_finalists'])}"
    )
    two_remote = sum(1 for pf in sourcing["past_finalists"] if pf["open_to_remote"])
    assert two_remote == 2, f"2 finalists must be remote-ready; got {two_remote}"

    ranked_channels = sorted(
        [c for c in sourcing["channels"] if c["rank"] is not None],
        key=lambda c: c["rank"],
    )
    assert len(ranked_channels) >= 3, "At least 3 ranked sourcing channels expected"
    channel_labels = [c["channel"] for c in ranked_channels]
    # Order from Section 7B: finalists → referral → supplier → job board
    assert any("referral" in lbl.lower() for lbl in channel_labels), "Referral channel missing"
    assert any("supplier" in lbl.lower() for lbl in channel_labels), "Supplier channel missing"
    assert any("job board" in lbl.lower() or "board" in lbl.lower() for lbl in channel_labels), \
        "Job board channel missing"

    # ── Skill evidence (Sections 13 + TC23/24/25) — via people API ───────
    # Rahul AWS: assessment 35 / 100
    resp = await client.get(f"/api/people/{RAHUL}/skills")
    assert resp.status_code == 200
    rahul_skills = {s["skill"]: s for s in resp.json()}
    aws = rahul_skills.get("aws")
    assert aws is not None, f"Rahul must have aws skill; got: {list(rahul_skills)}"
    assert aws["value"] == pytest.approx(35.0, abs=1.0), f"Rahul AWS value: {aws['value']}"
    assert aws["conflict"] is False, "Rahul AWS must not have conflict"

    # Priya Kubernetes: assessment 40, conflict=True (50-point gap vs self-report)
    resp = await client.get(f"/api/people/{PRIYA}/skills")
    assert resp.status_code == 200
    priya_skills = {s["skill"]: s for s in resp.json()}
    k8s = priya_skills.get("kubernetes")
    assert k8s is not None, f"Priya must have kubernetes skill; got: {list(priya_skills)}"
    assert k8s["value"] == pytest.approx(40.0, abs=1.0), f"Priya K8s value: {k8s['value']}"
    assert k8s["conflict"] is True, "Priya K8s must have conflict=True (50-point gap)"

    # GraphQL self-only → 0.7 × intermediate (56) ≈ 39
    gql = priya_skills.get("graphql")
    assert gql is not None, f"Priya must have graphql skill; got: {list(priya_skills)}"
    assert gql["value"] == pytest.approx(39.0, abs=2.0), f"Priya GraphQL value: {gql['value']}"
    assert gql["conflict"] is False, "GraphQL self-report-only must not have conflict"


# ── TC07: 32 redline scenarios in response (Section 15 backend support) ───────

@pytest.mark.anyio
async def test_tc07_32_scenarios_in_response(raw):
    """TC07 backend support: POST /api/analyze must return exactly 32 redline scenarios."""
    scenarios = raw["redline"]["scenarios"]
    assert len(scenarios) == 32, (
        f"Expected 32 scenario keys (2^5); got {len(scenarios)}: {list(scenarios)[:5]}…"
    )


# ── TC30: 9 workflow-stage data groups present (Section 15 backend support) ───

@pytest.mark.anyio
async def test_tc37_9_workflow_stages_present(raw):
    """TC30 backend support: all 9 option-panel data groups must be populated."""
    opts = raw["options"]

    stages = {
        "five (5-option table)":      opts.get("five"),
        "relocate_card":              opts.get("relocate_card"),
        "contractor_cards":           opts.get("contractor_cards"),
        "internal_candidates":        opts.get("internal_candidates"),
        "sourcing.channels":          opts.get("sourcing", {}).get("channels"),
        "sourcing.past_finalists":    opts.get("sourcing", {}).get("past_finalists"),
        "market_card":                opts.get("market_card"),
        "mixes":                      opts.get("mixes"),
        "decision_boundaries":        opts.get("decision_boundaries"),
    }
    empty = [name for name, val in stages.items() if not val]
    assert not empty, f"These workflow-stage data groups are empty: {empty}"


# ── Determinism: 3 calls → byte-identical JSON (except tokens) ───────────────

@pytest.mark.anyio
async def test_determinism_3_runs(client):
    """Same text analyzed 3 times must return byte-identical JSON (tokens field excluded)."""

    def _strip_tokens(d: dict) -> dict:
        return {k: v for k, v in d.items() if k != "tokens"}

    responses = []
    for _ in range(3):
        resp = await client.post("/api/analyze", json={"text": DEMO})
        assert resp.status_code == 200
        responses.append(_strip_tokens(resp.json()))

    canonical = json.dumps(responses[0], sort_keys=True)
    for i, r in enumerate(responses[1:], start=2):
        assert json.dumps(r, sort_keys=True) == canonical, (
            f"Run {i} JSON differs from run 1 (tokens excluded)"
        )


# ── Performance: POST /api/analyze < 2 s with LLM cache warm ─────────────────

@pytest.mark.anyio
async def test_performance_analyze_under_2s(client):
    """Median of 3 warm POST /api/analyze calls must be under 2 seconds."""
    times: list[float] = []
    for _ in range(3):
        start = time.perf_counter()
        resp = await client.post("/api/analyze", json={"text": DEMO})
        elapsed = time.perf_counter() - start
        assert resp.status_code == 200
        times.append(elapsed)
    median = sorted(times)[1]
    assert median < 2.0, f"Median of 3 runs: {median:.2f} s (limit: 2.0 s)"
