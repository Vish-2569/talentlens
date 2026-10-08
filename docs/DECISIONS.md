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
