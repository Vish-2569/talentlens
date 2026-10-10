# TalentLens — Decision Log

Every interpretation or design choice not explicitly stated in `docs/DESIGN.pdf` is recorded here.

Format: `YYYY-MM-DD | Decision | Doc section`

## Known Errata (from design review)

- 2026-10-08 | ESCO software developer URI is `http://data.europa.eu/esco/occupation/f2b15a0e-e65a-438a-affb-29b9d50b77d1` — the PDF dropped the hyphen after "affb" in some places. Pin this exact URI everywhere. | Section 11
- 2026-10-08 | Bengaluru Senior P50=62, P80=81 and all other story TTF figures are the raw MarketStat lookup values (ttf_p50, ttf_p80). The Section 5 scarcity/budget formula produces a separate `ttf_adjusted` field used for hover text ("about 1.25x longer"). Redline and Relocate cards show the lookup values. | Sections 5, 13
- 2026-10-08 | Redline severity (red/amber/unmarked) is measured on EXTERNAL matching supply, P50 days, rupees, and option feasibility — not internal candidate counts. Internal count changes (e.g. "5+ years" widening Build from 1 to 4) appear in hover text only. This keeps "5+ years" as amber per the doc. | Section 5
- 2026-10-08 | If a Gemini structured-output response is cut off by max_output_tokens, `response.parsed` is None. Treat as invalid JSON: one retry, then fall back to regex-only parse. | Section 8

## LLM Provider Change

- 2026-10-08 | LLM provider is Google Gemini (not the doc's generic "Flash/Haiku-class tier"). SDK: `google-genai` (`from google import genai`). Key env var: `GEMINI_API_KEY`. Model env var: `GEMINI_MODEL`, default `gemini-2.5-flash`. Never use the retired `google-generativeai` package. | Section 8

## Design Decisions

- 2026-10-09 | `_count_internal_build` excludes the key upskill skill (the must-have that removes the most external supply when required) when counting Build-eligible employees. Build candidates are expected to be upskilled on that specific skill; the count is therefore against the remaining must-skills only. This gives the correct story numbers: 1 at 5+ years, 4 at 3+ years. The key skill is chosen dynamically — it is not hard-coded as Kubernetes. | Section 5, Section 13
- 2026-10-09 | `DEMO_TODAY` setting added to `config.py` (default `2026-10-08`, overridable via `DEMO_TODAY` env var). The API passes `settings.demo_today` as the `today` argument to every engine function. Engine functions keep `today` as an explicit parameter with no `date.today()` calls — the demo story never depends on the real calendar date. `redline.py` was the only engine module using `date.today()`; now uses `settings.demo_today` as fallback. | Section 12

- 2026-10-08 | Redline `scenarios` dict uses a 5-char string of 0/1 as the mask key (constraint_order: location, years, skill, budget, deadline; 1 = relaxed). 32 keys total. | Section 5
- 2026-10-08 | ConstraintKind enum covers the 5 demo constraints: location, years, skill, budget, deadline. Additional kinds can be added if the parser finds other constraint types. | Section 5
- 2026-10-08 | `OptionCard.fit` is a string (not float) because the doc uses both percentage values ("82%") and qualitative labels ("Market"). | Section 7A
- 2026-10-08 | `Automate` option has `score: null` (not a number) since the doc says "add-on" — it is not ranked alongside the other five. | Section 7A
- 2026-10-08 | `AnalyzeRequest.text` enforced at max_length=1000 via Pydantic, matching the Section 8/9 "1,000-character cap". | Sections 8, 9
- 2026-10-08 | `DecisionRequest.reason` has min_length=1 so an empty reason is rejected server-side (Section 12 contract: "400 if reason is empty"). | Section 12
- 2026-10-08 | Async tests use pytest-anyio (not pytest-asyncio) since httpx AsyncClient + ASGITransport is the idiomatic FastAPI test pattern. | Section 12
- 2026-10-08 | `RippleNode` includes an optional `display_name` field for UI convenience; the doc shows names in the tree nodes. | Section 6
- 2026-10-08 | Stub analyze_stub.json uses placeholder person IDs (E-031, E-045, E-072, C-17) that match the doc's pseudonymous ID convention. Final IDs will come from seed.py. | Section 13
- 2026-10-08 | O*NET data is from the Database download (Excel format, version db_31_0), not the Web Services API (no key). Files read: Task Statements.xlsx, Software Skills.xlsx (was "Technology Skills"), Job Titles.xlsx (was "Alternate Titles"), Sample of Reported Titles.xlsx. | Section 11
- 2026-10-08 | O*NET renamed "Technology Skills" to "Software Skills" in db_31_0. The fetch_reference script handles both .xlsx and .txt extensions. | Section 11
- 2026-10-08 | ESCO `/resource/occupation?uri=...` endpoint now returns 200 (doc said 400). Using it for alternative labels; `/resource/related` for essential/optional skills. | Section 11
- 2026-10-08 | ESCO user interface developer URI pinned as `http://data.europa.eu/esco/occupation/866c7813-2c03-47d7-9bdc-192cfbace57c` (found via search, confirmed as 2512.4). | Section 11
- 2026-10-08 | No ESCO-O*NET crosswalk file present; canonical_role.json sets esco_uri and onet_codes from pinned constants. | Section 11
- 2026-10-08 | ESCO has 11 alternative labels for software developer (application developer, programmer, software engineer, etc.). These feed title_alias.csv rows with method=esco_alt. | Section 11
- 2026-10-08 | `gemini-2.5-flash` returns 404 for this API key ("no longer available to new users"). Used `gemini-3.5-flash` for automation scoring. Config default stays `gemini-2.5-flash` per user spec; override via GEMINI_MODEL env var. | Section 8
- 2026-10-08 | Automation scoring raw LLM output yields ~19% (adoption=0.5). The doc targets ~25-35%. All tasks have `reviewed: false`; human review should adjust test-writing, boilerplate, and docs tasks upward to hit the target range. | Section 7 (M7)
- 2026-10-09 | Random employees with open_to_move=true have nodejs excluded from their skill set if they also drew react. This prevents random employees from polluting the Build pool (react+nodejs+open_to_move), keeping at_5==1 (Karthik only) and at_3==4 (four named characters only). | Section 13
- 2026-10-09 | Adapters refactored to pandas-based classes (HRIS, ATS, VMS, EvidenceAdapter, MarketAdapter). Each loads CSVs once into DataFrames; all accessors return copies. Boolean columns use a `_to_bool()` helper that handles both string "true"/"false" and pandas-auto-detected bools. | Section 12
- 2026-10-09 | ReferenceCache adapter reads taxonomy CSVs + cache JSONs at init. Never calls network. Exposed via DataStore alongside all other adapters. | Section 12
- 2026-10-09 | DataStore is the single immutable entry point for all data. Engine modules receive DataFrames/dicts from DataStore only; they never import adapters or open files. `display_names(ids)` joins names onto pseudonymous IDs at the API layer only. | Section 12
- 2026-10-09 | db.py uses stdlib sqlite3 with parameterized queries only (? placeholders). Decision table is append-only: only `append_decision()` and `get_decisions()` exist — no update or delete methods. File: `backend/data/talentlens.sqlite`. | Section 12, 13
- 2026-10-09 | normalize_title: exact alias lookup first (case-insensitive), then rapidfuzz token_set_ratio (>=90 accept, 75-89 accept as inferred, <75 reject). Level extraction: SDE-1→junior, SDE-2→mid, SDE-3→senior, Sr./Senior→senior, Lead→lead, III→senior, II→mid. Anything not resolving to Full Stack Developer is rejected. | Section 6A, 7 M1
- 2026-10-09 | normalize_skill: exact match on skills.csv id, then exact match on skill_alias.csv, then rapidfuzz with same 90/75 thresholds. Output ONLY one of ~30 known IDs; anything else returned as unknown. | Section 6A
- 2026-10-09 | Evidence self-only discount uses `int(value * 0.70 + 0.5)` for traditional rounding (not Python's banker's rounding), matching doc's "intermediate 55 → 39%" (55 × 0.7 = 38.5 → 39). | Section 6A
- 2026-10-09 | Evidence conflict: compared on normalized 0-100 values. Self-reports use their UNDISCOUNTED normalized value (e.g., expert=90 not 63) for conflict comparison. Threshold: abs(diff) >= 30. | Section 6A
- 2026-10-09 | Priya docker evidence date moved from 2024-11-15 to 2024-09-15 to ensure >24 months staleness from default today (2026-10-08). Not a doc-specified value; seed design choice for data quality targets. | Section 6A
- 2026-10-09 | 12 demo titles for title_normalization_panel are hardcoded as DEMO_TITLES constant (design doc specification). The panel normalizes each one and reports role, level, method, confidence, ESCO URI. | Section 7 M1
- 2026-10-09 | M6 location formula: weights supply=0.35, speed(1/P50)=0.30, cost(1/(P50_pay×col_index))=0.25, remote_viability=0.10; all four dimensions min–max normalised: (x−min)/(max−min) across the candidate set. Penalty = (reloc_package_lpa / max_reloc_in_set) × PENALTY_WEIGHT where PENALTY_WEIGHT=0.05; when all packages are zero max_reloc defaults to 1.0 (no penalty applied). Expresses the relocation package on the same 0–1 scale: a location carrying the largest package in the comparison loses at most 0.05 from its score. | Section 7 M6
- 2026-10-09 | Deja Req Jaccard uses hired person's skills (emp_skills or ctr_skills) as proxy for past req's required skills, since requisitions.csv has no per-req skill columns. Incoming parsed_req.skill_ids compared against person_skills via standard Jaccard (|A∩B|/|A∪B|) ≥ 0.5. | Section 4
- 2026-10-09 | Deja Req cost_story compares Buy-total (sum of first_year_cost_lpa for buy decisions) vs Build-total (same for build decisions). Borrow costs excluded per doc's "₹64L vs ₹4L → ₹60L" example which sums only the 2 buys. | Section 4, 10
- 2026-10-09 | Deja Req outcome "still_in_role" maps to "Still in role, rated {label}" where the label comes from the `rating` column on employees.csv (5=Exceeds, 4=Meets+, 3=Meets, 2=Below, 1=Needs improvement). E-010 (Vikram, Jun 2026 build hire) has rating=5, producing "rated Exceeds" from data rather than narrative. | Section 4, 13
- 2026-10-09 | Section 7A Relocate card scores (0.86/0.52/0.49/0.18) are not reachable with the Section 7 M6 min–max formula given the fixed story supply/TTF values: Bengaluru is the minimum on all four dimensions (smallest supply 14, slowest TTF 1/62, highest effective cost col=1.00 × sal=32, lowest remote_share 0.05) and therefore scores 0 on every normalised axis regardless of seed tuning. Formula kept exactly as specified; scores recomputed to 0.79/0.36/0.34/0.00 with seed col_index remote=1.00, reloc_package_lpa blr=2L/hyd=1L/pune=1L/remote=0L. | Section 7A, 7 M6, 13

## Phase 11A: Options Engine

- 2026-10-10 | Ripple red flags (bus-factor flags + red dead-end nodes) add +0.05 risk per flag to build/redeploy atoms in the options scorer. Section 7 M8 names "Ripple red flags" as a risk input but gives no explicit weight; 0.05 chosen to match the self-report-only penalty, keeping the two risks on the same scale. Implemented in `_generate_atoms()` (propagates `red_flags` from ripple candidates) and `_score_mixes()` (adds `0.05 × red_flags` to `risk_raw`). | Section 7 M8

## Phase 10: Ripple Effect

- 2026-10-10 | Promotion raise = (sal_p75 − sal_p50) / 2 at the mover's CURRENT level and location. Derived from market_stats; reproduces the story's ₹3L (Priya mid Bengaluru: (24−18)/2) and ₹1.5L (Rahul junior Bengaluru: (10−7)/2) without hardcoding. Implemented as `_promotion_raise_lpa()` in ripple.py. | Section 6, 13
- 2026-10-10 | Backfill threshold is >= 70 (not strictly > 70). Section 6 stopping rule: stop RED when no backfill scores >= 70. A candidate scoring exactly 70 qualifies as an internal backfill. Boundary tests added. | Section 6
- 2026-10-10 | `redline.py` no longer imports `backend.config.settings`. The `today` parameter is now required (no default), keeping engine/ free of I/O and config dependencies. The API layer passes `settings.demo_today`. | Section 12

## Phase 8: Parser, LLM, Guardrails

- 2026-10-09 | Regex pre-parser (engine/parser.py) runs FIRST before any LLM call. Extracts budget (₹NL), years, deadline (days), city (fixed 4-city list), work_mode (onsite/hybrid/remote with negative lookahead to exclude "Remote India"), level (including Sr./Jr. abbreviations), and skills via scanning all known skill names/aliases in the text (longest-first, with overlap protection). | Section 8
- 2026-10-09 | Skill extraction uses a scanning approach: build a lookup of all skill aliases + IDs, sort longest-first, search for each in the text with word-boundary regex. This avoids delimiter-based splitting issues (e.g., "Node.js" not split at the period). Overlap protection ensures "Node.js" is matched before "Node" or "js". | Section 8
- 2026-10-09 | Must/nice importance determined by nearest preceding cue word position: "must know/have", "required", "essential", "mandatory" → must; "nice to have", "good to have", "bonus", "plus", "preferred" → nice. Default (no preceding cue) = must. | Section 8
- 2026-10-09 | REQUIRED_FIELDS = (level, location, work_mode). Only these trigger LLM fallback when empty or ambiguous. Budget, years, deadline are useful but optional. | Section 8
- 2026-10-09 | ThinkingConfig(thinking_budget=0) wrapped in _thinking_config() helper with try/except so future Gemini model generations that change the thinking API don't break the call. | Section 8
- 2026-10-09 | .env.example key name fixed: GCP_API_KEY → GEMINI_API_KEY to match config.py's os.getenv("GEMINI_API_KEY"). | Section 8, 12
- 2026-10-09 | FactsPayload (validate.py) uses Pydantic model_validator to reject keys containing person-related substrings (person, employee, name, display, candidate, contractor). This is the structural assertion that polish() never receives employee data. | Section 8
- 2026-10-09 | Numeric grounding for polish: _NUM_RE extracts all numbers from generated text (with optional ₹/L/lakh/%/days/weeks/months/years units), checks each against the FactsPayload.values set. Any ungrounded number → discard text, show template. | Section 8
- 2026-10-09 | LLM cache key = SHA-256(normalized_text | PROMPT_VERSION | model_name). Normalization: lowercase + collapse whitespace. Stored in backend/cache/llm_cache.sqlite. | Section 8
