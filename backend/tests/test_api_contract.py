"""API contract tests: stub validation, health, and input-length enforcement (TC-19)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from backend.api.main import app
from backend.api.schemas import AnalysisResult

STUB_PATH = Path(__file__).resolve().parent / "fixtures" / "analyze_stub.json"


# ── Stub validates against the schema ──────────────────────────────────

def test_stub_validates():
    raw = json.loads(STUB_PATH.read_text(encoding="utf-8"))
    result = AnalysisResult.model_validate(raw)
    assert result.parsed.title_normalization.raw_titles_count == 12
    assert result.dejareq.match_count == 4
    assert len(result.redline.scenarios) == 32
    assert len(result.options.five) == 5


def test_stub_has_all_brief_sections():
    raw = json.loads(STUB_PATH.read_text(encoding="utf-8"))
    result = AnalysisResult.model_validate(raw)
    assert len(result.brief.sections) == 12


def test_stub_demo_story_numbers():
    raw = json.loads(STUB_PATH.read_text(encoding="utf-8"))
    r = AnalysisResult.model_validate(raw)

    by_id = {o.id: o for o in r.options.five}
    assert by_id["mix"].score == 89.0
    assert by_id["borrow"].score == 87.0
    assert by_id["build"].score == 73.0
    assert by_id["relocate"].score == 62.0
    assert by_id["buy"].score == 42.0

    relocate = r.options.relocate_card
    assert relocate[0].location == "Remote-India"
    assert relocate[0].supply == 210
    assert relocate[0].ttf_p50 == 28
    assert relocate[3].location == "Bengaluru (on-site, as requested)"
    assert relocate[3].ttf_p80 == 81


# ── API endpoint tests ─────────────────────────────────────────────────

@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.anyio
async def test_health(client):
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True


@pytest.mark.anyio
async def test_analyze_returns_valid(client):
    resp = await client.post("/api/analyze", json={"text": "Senior Full Stack Developer, Bengaluru"})
    assert resp.status_code == 200
    AnalysisResult.model_validate(resp.json())


@pytest.mark.anyio
async def test_analyze_rejects_1001_chars(client):
    resp = await client.post("/api/analyze", json={"text": "x" * 1001})
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_analyze_rejects_5000_chars(client):
    resp = await client.post("/api/analyze", json={"text": "x" * 5000})
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_analyze_rejects_empty(client):
    resp = await client.post("/api/analyze", json={"text": ""})
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_decision_requires_reason(client):
    resp = await client.post("/api/decisions", json={
        "req_id": "REQ-001", "option_id": "mix", "verb": "Approve",
        "relaxed_mask": "00000", "decided_by": "someone", "reason": ""
    })
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_decision_requires_verb(client):
    resp = await client.post("/api/decisions", json={
        "req_id": "REQ-001", "option_id": "mix",
        "relaxed_mask": "00000", "decided_by": "someone", "reason": "good"
    })
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_decision_rejects_unknown_verb(client):
    resp = await client.post("/api/decisions", json={
        "req_id": "REQ-001", "option_id": "mix", "verb": "Destroy",
        "relaxed_mask": "00000", "decided_by": "someone",
        "reason": "good reason"
    })
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_decision_requires_decided_by(client):
    resp = await client.post("/api/decisions", json={
        "req_id": "REQ-001", "option_id": "mix", "verb": "Approve",
        "relaxed_mask": "00000", "reason": "good reason"
    })
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_decision_rejects_blank_decided_by(client):
    resp = await client.post("/api/decisions", json={
        "req_id": "REQ-001", "option_id": "mix", "verb": "Approve",
        "relaxed_mask": "00000", "decided_by": "", "reason": "good reason"
    })
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_decision_requires_relaxed_mask(client):
    resp = await client.post("/api/decisions", json={
        "req_id": "REQ-001", "option_id": "mix", "verb": "Approve",
        "decided_by": "someone", "reason": "good reason"
    })
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_decision_rejects_invalid_relaxed_mask(client):
    resp = await client.post("/api/decisions", json={
        "req_id": "REQ-001", "option_id": "mix", "verb": "Approve",
        "relaxed_mask": "abc", "decided_by": "someone",
        "reason": "good reason"
    })
    assert resp.status_code == 422
