from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException
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
from backend.db import Database
from backend.decisions import record_decision

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


_VALID_OPTIONS = ["mix", "build", "borrow", "relocate", "buy",
                  "mix-1", "mix-2", "mix-3", "automate"]


@app.post("/api/decisions", status_code=201)
def create_decision(req: DecisionRequest) -> dict:
    db = Database()
    try:
        req_row = db.get_requisition(req.req_id)
        if req_row is None:
            raise HTTPException(status_code=400,
                                detail=f"Requisition {req.req_id} not found")

        parsed_json = json.loads(req_row["raw_json"])

        scenarios = db.get_scenarios(req.req_id)
        scenario_row = next(
            (s for s in scenarios if s["relaxed_mask"] == req.relaxed_mask),
            None,
        )
        options_json = (
            json.loads(scenario_row["outputs_json"]) if scenario_row else {}
        )

        result = record_decision(
            db=db,
            req_id=req.req_id,
            option_id=req.option_id,
            verb=req.verb.value,
            relaxed_mask=req.relaxed_mask,
            decided_by=req.decided_by,
            reason=req.reason,
            valid_options=_VALID_OPTIONS,
            parsed_json=parsed_json,
            options_json=options_json,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()


_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"

if _DIST.is_dir():
    @app.get("/{full_path:path}")
    async def spa_fallback(full_path: str) -> FileResponse:
        file = _DIST / full_path
        if file.is_file():
            return FileResponse(file)
        return FileResponse(_DIST / "index.html")

    app.mount("/", StaticFiles(directory=str(_DIST), html=True), name="frontend")
