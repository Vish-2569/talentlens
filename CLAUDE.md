# TalentLens — CLAUDE.md

## 1. Mission

TalentLens is a requisition challenger for ONE role: **Full Stack Developer**, 4 levels (L1 Junior, L2 Mid, L3 Senior, L4 Lead), ~30 skills, 4 locations (Bengaluru, Hyderabad, Pune, Remote-India).
Three hero features — Deja Req, Requisition Redline, Ripple Effect — plus one trust layer (Skill Evidence Tags) under all three.

## 2. Architecture Rule (Section 3, verbatim)

> "AI reads language; Python does arithmetic; a human decides."

## 3. Hard Rules (non-negotiable)

- **LLM boundary**: Gemini is called in exactly two functions: `llm.parse()` and `llm.polish()` (optional, off by default). Nothing else calls it at runtime. M7 automation scoring calls it once OFFLINE in a prep script only.
- **No LLM numbers**: The LLM never produces a number that reaches the screen. The LLM never sees employee, contractor or candidate data.
- **Token budget**: <= 2 LLM calls and <= ~1,600 tokens per requisition. `temperature=0`. Hard `max_output_tokens` caps (parse 300, polish 350). Structured JSON output only.
- **Cache key**: SHA-256(normalized text + prompt version + model name), stored in SQLite.
- **Determinism**: Faker + NumPy seed 42; `engine/` holds pure functions with no I/O; same input -> same output, always.
- **Closed vocabularies**: ~30 skill IDs; level, location and work_mode enums; exit reasons from a fixed category list.
- **Synthetic data only**: 100% synthetic data; engine works on pseudonymous IDs (E-042, C-17); names are joined in only in API responses.
- **No protected attributes**: age, gender, religion, caste, disability do not exist as columns. Only `open_to_move = true` employees are ever scored or moved.
- **Human-in-the-loop**: Nothing auto-executes. Every decision needs approver + non-empty reason, written to an append-only Decision Log.
- **DO NOT BUILD** (Section 17): other job roles, real ATS/HRIS connectors, live scraping, fine-tuning, embeddings or model downloads, Monte Carlo, LightGBM, PuLP, authentication, resume parsing, automatic execution, a chat interface, Postgres, pgvector, JobBERT, SkillNER, Streamlit.

## 4. Backend Stack (Section 12)

Python 3.11, FastAPI + Uvicorn, Pydantic v2, pandas, NumPy, rapidfuzz, stdlib sqlite3, python-dotenv, Faker, requests (prep scripts only), google-genai, pytest, httpx (for FastAPI TestClient). All versions pinned in `requirements.txt`.

LLM provider: **Google Gemini** via the official `google-genai` SDK (`from google import genai`, `from google.genai import types`). Key: `GEMINI_API_KEY`. Model: `GEMINI_MODEL` (default `gemini-2.5-flash`). Never use the retired `google-generativeai` package.

## 5. Repository Layout (Section 12, backend)

```
talentlens/
  backend/
    api/main.py            # FastAPI routes, CORS, serves frontend/dist
    engine/                # pure functions, no I/O
      parser.py  normalize.py  evidence.py  match.py  build.py  borrow.py
      market.py  location.py  automate.py  options.py
      dejareq.py  redline.py  ripple.py  brief.py
    adapters/              # CSV readers: hris.py ats.py vms.py evidence.py market.py
    llm.py                 # parse() + polish(), cache, token meter (Gemini)
    data/seed.py           # generates data/*.csv with seed 42
    cache/                 # reference.json, automation_tasks.json, llm_cache.sqlite
    tests/                 # one file per engine module + test_demo_story.py
  .env.example  requirements.txt  README.md
```

## 6. Demo Story — Test Oracle

### Section 13: "Demo story the seed must produce" (verbatim, single source of truth)

| Fact | Value | Used in |
|------|-------|---------|
| Raw job titles across systems | 12 → 1 role (Full Stack Developer), 4 levels | Title normalization panel |
| Past matching requisitions | 4 (Nov 2024 Buy, Oct 2025 Buy, Mar 2026 Borrow, Jun 2026 Build) | Deja Req |
| Avg external tenure | 8 months (9 and 7) | Deja Req |
| Bengaluru on-site Senior supply (all constraints) | 14 candidates | Redline, Relocate card |
| Same, without Kubernetes | 47 candidates (Kubernetes removes 70%) | Redline |
| Remote-India Senior supply / P50 / P80 / pay | 210 / 28 days / 40 days / ₹29L | Redline, Relocate card |
| Hyderabad on-site Senior | 31 / 44 days / 58 days / ₹30L | Relocate card |
| Pune on-site Senior | 26 / 47 days / 62 days / ₹26L (18% below Bengaluru) | Redline, Relocate card |
| Bengaluru Senior P50 / P80 time-to-fill / pay | 62 / 81 days / ₹32L | Redline, Ripple, Relocate card |
| Internal: Karthik (Lead, Platform) | 88% match, sole Terraform holder on critical project | Ripple |
| Internal: Priya (Mid, Checkout, 4 yrs) | 82% match, ready week 6 | Ripple, Redline, five-option table |
| Internal: Rahul (Junior, Checkout) | 76% ready for Mid, 3-month upskill | Ripple |
| Contractor Arjun (C-17) | 84% match, has Kubernetes, contract ends in 4 weeks, 12-month cost ₹24L, 3-month bridge ₹6L | Redline, Borrow, five-option table |
| Junior external hire | P50 21 days, ₹7L | Ripple |
| External Lead (Platform backfill) | P50 76 days | Ripple |
| Build chain year-one cost | ₹12L (₹7L junior + ₹4.5L raises + ₹0.5L upskill) | Ripple, five-option table |
| Recommended mix | Arjun 3-month bridge (₹6L) + Build chain (₹12L) = ₹18L; score 84 | Redline panel, five-option table |
| Option scores | Mix 84, Build 78, Borrow 71, Relocate 64, Buy 41, Automate add-on | Five-option table |
| Sourcing channels | Past finalists 3 (2 remote-ready); referral 38% / 34 days; supplier A 45% / 9 days; job board 22% / 52 days | Section 7B |
| Rahul - AWS evidence | Assessment 35/100 on 12 Mar 2026; self-reported "intermediate" (ignored) → 35%, solid tag, no warning | Skill Evidence Tags |
| Priya - Kubernetes evidence | Assessment 40/100 on 18 Aug 2026; self-reported "expert" → 40%, warning (50 points apart) | Skill Evidence Tags, Ripple |
| Karthik - Terraform evidence | Certification (Terraform Associate, 2025) + 30 months project history → certification used | Skill Evidence Tags, Ripple |
| A self-report-only skill (GraphQL) | "intermediate" Feb 2025 → 39% (x 0.7), outlined tag | Skill Evidence Tags |

### Section 7A: Five-option comparison table (verbatim)

| Option | What it means here | Ready by (P80) | Year-one cost | Fit | Risk | Score /100 | One-line reason |
|--------|--------------------|----------------|---------------|-----|------|------------|-----------------|
| Recommended mix | Borrow Arjun as a 3-month bridge + Build Priya | Day 0 | ₹18L | 82-84% | Low | 84 | Covers the 30-day deadline now; keeps the skill in-house after week 6 |
| Build | Priya moves up; Rahul backfills; 1 junior hire (Ripple chain) | Week 6 | ₹12L | 82% | Low | 78 | Cheapest and stays; misses the 30-day deadline on its own |
| Borrow | Extend contractor Arjun (C-17) for 12 months | Day 0 | ₹24L | 84% | Medium | 71 | Fastest; past Borrow lost knowledge (Deja Req +0.10 risk) |
| Relocate | Hire Senior in Remote-India instead of Bengaluru on-site | Day 40 | ₹29L | Market | Medium-high | 64 | 15x the supply of Bengaluru; still an external hire (churn pattern) |
| Buy | Hire Senior in Bengaluru on-site, as requested | Day 81 | ₹32L | Market | High | 41 | Misses deadline; budget below P50; two past external hires left < 12 months |
| Automate | AI coding-assistant seats for the team (add-on) | Day 7 | ~₹1L (simulated) | -- | Low | add-on | Absorbs ~25-35% of routine hours (test writing, boilerplate, docs); does not replace the hire |

### Section 7A: Relocate card (verbatim)

| Location | Matching supply | P50 / P80 time-to-fill | P50 pay | Location score |
|----------|----------------|------------------------|---------|----------------|
| Remote-India | 210 | 28 / 40 days | ₹29L | 0.79 |
| Hyderabad (on-site) | 31 | 44 / 58 days | ₹30L | 0.36 |
| Pune (on-site) | 26 | 47 / 62 days | ₹26L | 0.34 |
| Bengaluru (on-site, as requested) | 14 | 62 / 81 days | ₹32L | 0.00 |

### Section 7B: Sourcing channels table (verbatim)

| Rank | Channel / pool | Evidence (seeded ATS / VMS history, last 24 months) | Use for |
|------|---------------|------------------------------------------------------|---------|
| 1 | Past finalists (ATS rediscovery) | 3 candidates reached the final round for this role in the last 12 months and were not hired (offer declined or headcount closed); 2 open to remote; all opted in to the talent pool | Buy / Relocate |
| 2 | Employee referral | Fill rate 38%, median 34 days to hire | Buy / Relocate |
| 3 | Staffing supplier A (via MSP) | Fill rate 45%, median 9 days to first submission, bill rate within budget | Borrow |
| 4 | Job board | Fill rate 22%, median 52 days | Buy |
| -- | Campus | Not applicable for Senior level | -- |

## 7. How to Work in Every Phase

a. Read the doc sections named in the phase prompt before coding.

b. Write tests first with expected values taken from the doc (they fail first).

c. Implement until `pytest` is green. Never move on with a failing test.

d. NEVER change an expected value to make a test pass and NEVER hard-code a story number in engine code. Fix the seed data or the logic instead. If a story number truly cannot be reached with the documented formula, stop and tell me.

e. Every function that returns a number also returns the evidence row IDs it used.

f. Record every interpretation in `docs/DECISIONS.md` (one line: date, decision, doc section).

## 8. Known Errata

- ESCO software developer URI must be `http://data.europa.eu/esco/occupation/f2b15a0e-e65a-438a-affb-29b9d50b77d1` (the PDF dropped the hyphen after "affb").
- Bengaluru Senior P50 62 / P80 81 and the other story time-to-fill figures are the MarketStat lookup values (ttf_p50, ttf_p80). The Section 5 scarcity/budget formula is implemented exactly and returned as a separate "ttf_adjusted" field used for the budget hover ("about 1.25x longer").
- Redline severity is measured on EXTERNAL matching supply, P50 days and rupees, and option feasibility. Internal candidate count changes (e.g. Build 1 -> 4 for years) are reported in hover text only. This keeps "5+ years" amber as the doc requires.
- If a Gemini structured-output response is cut off by max_output_tokens, `response.parsed` is None: treat as invalid JSON (one retry, then regex-only parse).
