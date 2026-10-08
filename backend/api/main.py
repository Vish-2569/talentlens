from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.api.schemas import (
    AnalysisResult,
    AnalyzeRequest,
    DecisionRequest,
    Health,
)
from backend.config import settings

app = FastAPI(title="TalentLens", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_methods=["*"],
    allow_headers=["*"],
)

_STUB_PATH = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "analyze_stub.json"
_stub_data: dict | None = None


def _load_stub() -> dict:
    global _stub_data
    if _stub_data is None:
        _stub_data = json.loads(_STUB_PATH.read_text(encoding="utf-8"))
    return _stub_data


@app.get("/api/health", response_model=Health)
def health() -> Health:
    cache_dir = Path(__file__).resolve().parent.parent / "cache"
    return Health(
        ok=True,
        cache_loaded=(cache_dir / "reference.json").exists(),
        llm_configured=bool(settings.gemini_api_key),
    )


@app.post("/api/analyze", response_model=AnalysisResult)
def analyze(req: AnalyzeRequest) -> AnalysisResult:
    stub = _load_stub()
    return AnalysisResult.model_validate(stub)


@app.post("/api/decisions", status_code=201)
def create_decision(req: DecisionRequest) -> dict:
    return {"status": "recorded", "req_id": req.req_id}


_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"

if _DIST.is_dir():
    @app.get("/{full_path:path}")
    async def spa_fallback(full_path: str) -> FileResponse:
        file = _DIST / full_path
        if file.is_file():
            return FileResponse(file)
        return FileResponse(_DIST / "index.html")

    app.mount("/", StaticFiles(directory=str(_DIST), html=True), name="frontend")
