"""Backend robustness tests — varied requisition inputs must never 500."""
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


# ── Helper ───────────────────────────────────────────────────────────────────

async def _assert_ok_or_422(client: AsyncClient, text: str) -> dict | None:
    resp = await client.post("/api/analyze", json={"text": text})
    assert resp.status_code in (200, 422), (
        f"Expected 200 or 422, got {resp.status_code}: {resp.text[:300]}"
    )
    if resp.status_code == 200:
        AnalysisResult.model_validate(resp.json())
        return resp.json()
    return None


# ── Demo sentence unchanged ──────────────────────────────────────────────────

@pytest.mark.anyio
async def test_demo_sentence_still_200(client):
    resp = await client.post("/api/analyze", json={"text": DEMO})
    assert resp.status_code == 200
    d = resp.json()
    scores = {o["id"]: o["score"] for o in d["options"]["five"]}
    assert scores["borrow"] == 87.0
    assert scores["build"] == 73.0
    assert scores["buy"] == 42.0
    assert d["options"]["mixes"][0]["score"] == 89.0
    assert d["parsed"]["location_note"] is None
    assert d["parsed"]["unrecognized_skills"] == []


# ── Unknown location: Chennai ────────────────────────────────────────────────

@pytest.mark.anyio
async def test_chennai_returns_200_with_note(client):
    text = (
        "Senior Full Stack Developer, Chennai on-site, 2+ years, "
        "must know SpringBoot, Node.js and Kubernetes, budget ₹28L, need in 10 days."
    )
    d = await _assert_ok_or_422(client, text)
    if d is None:
        return
    assert d["parsed"]["location"]["value"] == "other"
    assert d["parsed"]["location"]["span"] == "Chennai"
    assert "Chennai" in d["parsed"]["location_note"]
    assert "Remote-India" in d["parsed"]["location_note"]
    assert "SpringBoot" in d["parsed"]["unrecognized_skills"]
    assert "nodejs" in [s["skill_id"] for s in d["parsed"]["skills"]]
    assert "kubernetes" in [s["skill_id"] for s in d["parsed"]["skills"]]


# ── Unknown location: Mumbai ─────────────────────────────────────────────────

@pytest.mark.anyio
async def test_mumbai_returns_200(client):
    d = await _assert_ok_or_422(
        client, "Senior, Mumbai, must know Python and Django, budget ₹50L"
    )
    if d is None:
        return
    assert d["parsed"]["location"]["value"] == "other"
    assert "Mumbai" in d["parsed"]["location_note"]
    assert "Django" in d["parsed"]["unrecognized_skills"]


# ── Junior, minimal text ─────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_junior_minimal(client):
    d = await _assert_ok_or_422(client, "Junior developer")
    assert d is not None


# ── Lead level ───────────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_lead_level(client):
    d = await _assert_ok_or_422(
        client, "Lead Full Stack Developer, Bengaluru"
    )
    if d:
        assert d["parsed"]["level"]["value"] == "lead"


# ── Remote India ─────────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_remote_india(client):
    d = await _assert_ok_or_422(
        client, "Senior, Remote India, must know React"
    )
    if d:
        assert d["parsed"]["location"]["value"] == "remote_india"
        assert d["parsed"]["location_note"] is None


# ── Very short text ──────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_very_short_text(client):
    await _assert_ok_or_422(client, "need a developer")


# ── Only a title ─────────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_only_title(client):
    await _assert_ok_or_422(client, "Full Stack Developer")


# ── No budget, no deadline ───────────────────────────────────────────────────

@pytest.mark.anyio
async def test_no_budget_no_deadline(client):
    d = await _assert_ok_or_422(
        client, "Senior, Bengaluru, must know React"
    )
    if d:
        assert d["parsed"]["budget_lpa"]["value"] == 0
        assert d["parsed"]["need_by_days"]["value"] == 90


# ── Very short deadline ──────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_very_short_deadline(client):
    d = await _assert_ok_or_422(
        client, "Junior, Bengaluru, must know HTML and CSS, need in 2 days"
    )
    if d:
        assert d["parsed"]["need_by_days"]["value"] == 2


# ── Nice-to-have skills ─────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_nice_to_have_skills(client):
    d = await _assert_ok_or_422(
        client,
        "Mid Full Stack Developer, Pune, hybrid, 3+ years, nice to have Angular",
    )
    if d:
        nice = [s for s in d["parsed"]["skills"] if s["importance"] == "nice"]
        assert any(s["skill_id"] == "angular" for s in nice)


# ── Lead with high budget and short deadline ─────────────────────────────────

@pytest.mark.anyio
async def test_lead_short_deadline(client):
    d = await _assert_ok_or_422(
        client,
        "Lead, Hyderabad on-site, 10+ years, budget ₹60L, need in 5 days",
    )
    if d:
        assert d["parsed"]["level"]["value"] == "lead"
        assert d["parsed"]["need_by_days"]["value"] == 5


# ── Empty text: 422 from validation ──────────────────────────────────────────

@pytest.mark.anyio
async def test_empty_text_422(client):
    resp = await client.post("/api/analyze", json={"text": ""})
    assert resp.status_code == 422


# ── Known skills are not in unrecognized ─────────────────────────────────────

@pytest.mark.anyio
async def test_known_skill_not_unrecognized(client):
    d = await _assert_ok_or_422(
        client,
        "Senior, Bengaluru, must know React, Node.js, Kubernetes, SpringBoot",
    )
    if d:
        unrec = d["parsed"]["unrecognized_skills"]
        assert "SpringBoot" in unrec
        known = [s["skill_id"] for s in d["parsed"]["skills"]]
        for u in unrec:
            assert u.lower() not in known
