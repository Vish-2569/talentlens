# TalentLens

Requisition challenger for **Full Stack Developer** (4 levels, ~30 skills, 4 locations).
Three hero features — Deja Req · Requisition Redline · Ripple Effect — backed by a Skill Evidence layer.

---

## Quick start (demo)

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env          # then set GEMINI_API_KEY

python backend/data/seed.py   # generate synthetic data (once)

cd frontend && npm install && npm run build && cd ..
python -m uvicorn backend.api.main:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/` — the backend serves the built frontend with SPA fallback.

## Development

Start the backend and frontend dev server separately:

```bash
# Terminal 1 — backend
python -m uvicorn backend.api.main:app --host 127.0.0.1 --port 8000 --reload

# Terminal 2 — frontend (Vite proxies /api to :8000)
cd frontend && npm run dev
```

### Environment

```bash
cp .env.example .env
```

| Variable | Description |
|---|---|
| `GEMINI_API_KEY` | Your Google Gemini API key |
| `GEMINI_MODEL` | Model name (default: `gemini-2.5-flash`) |
| `DEMO_TODAY` | Override today's date for demo (`YYYY-MM-DD`); leave blank to use system date |

### Reference data (prep, run once)

`backend/scripts/fetch_reference.py` reads O\*NET skill/task data from locally downloaded
database files placed in `backend/data/onet_raw/` and calls the live ESCO API. Output goes
to `backend/cache/reference.json`.

```bash
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
cd frontend && npm test && npm run lint
```

### Regenerate API types

After any backend schema change:

```bash
python -c "from backend.api.main import app; import json; open('openapi.json','w').write(json.dumps(app.openapi(),indent=2))"
cd frontend && npm run gen:types
npm run check:contract   # fails if openapi.json is newer than types.ts
```

---

## Architecture

> AI reads language; Python does arithmetic; a human decides.

- Gemini is called in exactly two functions: `llm.parse()` and `llm.polish()` (off by default).
- The LLM never produces a number that reaches the screen and never sees employee or candidate data.
- All scoring and arithmetic happens in pure Python (`engine/` — no I/O, deterministic).
- Every decision requires a human approver and a non-empty reason, written to an append-only Decision Log.
