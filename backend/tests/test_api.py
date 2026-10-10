"""Phase 13A integration tests — real engine, story-value assertions."""
from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from backend.api.main import app
from backend.api.schemas import AnalysisResult

DEMO = (
    "Senior Full Stack Developer, Bengaluru, on-site, 5+ years, "
    "must know React, Node.js and Kubernetes, budget ₹28L, need in 30 days."
)


@pytest.fixture(scope="module")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="module")
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture(scope="module")
async def result(client):
    resp = await client.post("/api/analyze", json={"text": DEMO})
    assert resp.status_code == 200, resp.text
    return AnalysisResult.model_validate(resp.json())


@pytest.fixture(scope="module")
async def raw(client):
    resp = await client.post("/api/analyze", json={"text": DEMO})
    assert resp.status_code == 200
    return resp.json()


# ── Schema + title normalization ──────────────────────────────────────────────

@pytest.mark.anyio
async def test_analyze_real_validates_schema(result):
    assert result.parsed.title_normalization.raw_titles_count == 12


# ── Deja Req ──────────────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_analyze_dejareq(result):
    assert result.dejareq.match_count == 4


# ── Redline ───────────────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_analyze_redline(result):
    red = [c for c in result.redline.constraints if c.severity.value == "red"]
    amber = [c for c in result.redline.constraints if c.severity.value == "amber"]
    assert len(red) == 3, f"Expected 3 red, got {len(red)}: {[c.kind for c in red]}"
    assert len(amber) == 2, f"Expected 2 amber, got {len(amber)}: {[c.kind for c in amber]}"
    assert len(result.redline.scenarios) == 32


# ── Scenarios ─────────────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_analyze_scenario_00000(result):
    scen = result.redline.scenarios.get("00000")
    assert scen is not None
    text = scen.panel_text
    assert "Buy" in text
    assert "62" in text
    assert "32" in text


@pytest.mark.anyio
async def test_analyze_scenario_10100(result):
    scen = result.redline.scenarios.get("10100")
    assert scen is not None
    assert scen.top_option_id == "mix"
    mix_opt = next((o for o in scen.options if o.option_id == "mix"), None)
    assert mix_opt is not None
    cost = mix_opt.year_one_cost_lpa
    assert cost is not None
    assert abs(cost - 18) <= 1, f"Mix cost expected ~18L, got {cost}"


# ── Option scores ─────────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_analyze_option_scores(result):
    by_id = {o.id: o.score for o in result.options.five}
    assert set(by_id.keys()) == {"borrow", "build", "relocate", "buy", "automate"}
    assert by_id["borrow"] == 87.0, f"borrow score: {by_id['borrow']}"
    assert by_id["build"] == 73.0, f"build score: {by_id['build']}"
    assert by_id["relocate"] == 62.0, f"relocate score: {by_id['relocate']}"
    assert by_id["buy"] == 42.0, f"buy score: {by_id['buy']}"
    assert by_id["automate"] is None, f"automate score: {by_id['automate']}"
    assert result.options.mixes[0].score == 89.0, (
        f"top mix score: {result.options.mixes[0].score}"
    )


# ── Location scores ───────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_analyze_location_scores(result):
    card = result.options.relocate_card
    scores = [r.score for r in card]
    assert scores == sorted(scores, reverse=True), "Relocate card should be sorted by score desc"
    assert scores[0] == pytest.approx(0.79, abs=0.01), f"Remote-India score: {scores[0]}"
    assert scores[1] == pytest.approx(0.36, abs=0.01), f"Hyderabad score: {scores[1]}"
    assert scores[2] == pytest.approx(0.34, abs=0.01), f"Pune score: {scores[2]}"
    assert scores[3] == pytest.approx(0.00, abs=0.01), f"Bengaluru score: {scores[3]}"


# ── Ripple top-2 ──────────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_analyze_ripple_top2(result):
    cands = result.ripple.candidates
    assert len(cands) >= 2, f"Expected >=2 ripple candidates, got {len(cands)}"
    matches = sorted([c.match for c in cands], reverse=True)
    assert matches[0] == pytest.approx(88.0, abs=1.0), f"Top match: {matches[0]}"
    assert matches[1] == pytest.approx(82.0, abs=1.0), f"Second match: {matches[1]}"


# ── People/skills endpoint ────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_people_skills_known(client):
    resp = await client.get("/api/people/E-031/skills")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) > 0


@pytest.mark.anyio
async def test_people_skills_unknown(client):
    resp = await client.get("/api/people/ZZ-99/skills")
    assert resp.status_code == 404


# ── Idempotent double-submit ──────────────────────────────────────────────────

@pytest.mark.anyio
async def test_analyze_idempotent(client):
    """POST /api/analyze twice with same text → both 200, identical req_id and scores."""
    resp1 = await client.post("/api/analyze", json={"text": DEMO})
    resp2 = await client.post("/api/analyze", json={"text": DEMO})
    assert resp1.status_code == 200, resp1.text
    assert resp2.status_code == 200, resp2.text
    d1 = resp1.json()
    d2 = resp2.json()
    assert d1["parsed"]["req_id"] == d2["parsed"]["req_id"], "req_id must be deterministic"
    scores1 = {o["id"]: o["score"] for o in d1["options"]["five"]}
    scores2 = {o["id"]: o["score"] for o in d2["options"]["five"]}
    assert scores1 == scores2, f"Scores diverged: {scores1} vs {scores2}"
    assert d1["dejareq"]["match_count"] == d2["dejareq"]["match_count"]


# ── Round-trip decision ───────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_roundtrip_decision(client, raw):
    req_id = raw["parsed"]["req_id"]
    assert req_id.startswith("REQ-")

    resp = await client.post("/api/decisions", json={
        "req_id": req_id,
        "option_id": "mix",
        "verb": "Approve",
        "relaxed_mask": "00000",
        "decided_by": "Test Approver",
        "reason": "Phase 13A round-trip test",
    })
    assert resp.status_code == 201, resp.text
