# TalentLens

Requisition challenger for **Full Stack Developer** (4 levels, ~30 skills, 4 locations).
Three hero features — Deja Req · Requisition Redline · Ripple Effect — backed by a Skill Evidence layer.

---

## Backend

### Requirements

- Python 3.11+
- All dependencies pinned in `requirements.txt`

### Setup

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### Environment

```bash
cp .env.example .env
```

Edit `.env` and set at minimum:

| Variable | Description |
|---|---|
| `GEMINI_API_KEY` | Your Google Gemini API key |
| `GEMINI_MODEL` | Model name (default: `gemini-2.5-flash`) |
| `DEMO_TODAY` | Override today's date for demo (`YYYY-MM-DD`); leave blank to use system date |

### Reference data (prep, run once)

`backend/scripts/fetch_reference.py` is a **prep-only** script — never called at runtime.
It reads O\*NET skill/task data from locally downloaded database files (O\*NET database
xlsx files from the O\*NET Resource Center at [onetcenter.org](https://www.onetcenter.org/database.html),
not the O\*NET Web Services API) placed in `backend/data/onet_raw/`, and calls the live ESCO API.
Output goes to `backend/cache/reference.json`.

```bash
# After placing O*NET xlsx files in backend/data/onet_raw/:
python backend/scripts/fetch_reference.py
```

### Seed data

Generate 100% synthetic CSV data (Faker + NumPy seed 42):

```bash
python backend/data/seed.py
```

### Tests

```bash
pytest backend/tests/
```

### Run the API

```bash
python -m uvicorn backend.api.main:app --host 127.0.0.1 --port 8000
```

The server binds to `127.0.0.1` only (loopback). FastAPI automatically serves the compiled
frontend from `frontend/dist/` at `/` with a SPA fallback when that directory exists.
During development the frontend dev server runs separately (default `http://localhost:5173`).

---

## Architecture

> AI reads language; Python does arithmetic; a human decides.

- Gemini is called in exactly two functions: `llm.parse()` and `llm.polish()` (off by default).
- The LLM never produces a number that reaches the screen and never sees employee or candidate data.
- All scoring and arithmetic happens in pure Python (`engine/` — no I/O, deterministic).
- Every decision requires a human approver and a non-empty reason, written to an append-only Decision Log.
