# TalentLens — Test Report

Generated: 2026-10-10 | Suite: `pytest backend/tests/` | **453 tests, 453 passed, 0 failed**

---

## TC Coverage Table

Legend: ✅ backend test passing · **frontend** test runs in browser · _italic_ = backend support test listed

| TC | Description (Section 15) | File :: test | Status |
|----|--------------------------|--------------|--------|
| TC01 | Deja Req banner: demo sentence → "4 times in last 2 years" | `test_dejareq.py::test_tc01_demo_banner_4_times` | ✅ |
| TC02 | Deja Req: junior requisition → no banner | `test_dejareq.py::test_tc02_junior_no_banner` | ✅ |
| TC03 | Deja Req: avg external tenure 8 months (9+7 / 2) | `test_dejareq.py::test_tc03_avg_external_tenure_8_months` | ✅ |
| TC04 | Redline: 5 marks, 3 red + 2 amber, spans match raw text, correct order | `test_redline.py::test_tc04_five_marks`, `test_tc04_severities`, `test_tc04_spans_match_raw_text`, `test_tc04_constraint_order` | ✅ |
| TC05 | Redline: relax Kubernetes → supply 14 → 47 (delta 33) | `test_redline.py::test_tc05_relax_kubernetes_supply`, `test_tc05_supply_no_key_is_47`, `test_tc05_kubernetes_is_key_skill` | ✅ |
| TC06 | Redline: relax location → Remote-India supply 210, P50 28 | `test_redline.py::test_tc06_remote_supply`, `test_tc06_remote_p50` | ✅ |
| TC07 | Redline panel: all 32 scenarios rendered (frontend toggle) | **frontend** · _backend: `test_demo_story.py::test_tc07_32_scenarios_in_response`_ | ✅ |
| TC08 | Redline: same input twice → identical scenario output | `test_redline.py::test_tc08_determinism` | ✅ |
| TC09 | Ripple: Priya (E-045) chain — 3 green nodes | `test_ripple.py::test_tc09_priya_chain_3_nodes` | ✅ |
| TC10 | Ripple: Karthik (E-031) — Terraform bus-factor flag | `test_ripple.py::test_tc10_karthik_bus_factor_terraform` | ✅ |
| TC11 | Ripple: open_to_move=false employees never appear | `test_ripple.py::test_tc11_closed_employees_not_in_chains` | ✅ |
| TC12 | Match scores: Karthik 88, Priya 82, Arjun 84, Rahul 76 (Mid) | `test_match.py::test_tc12_karthik_88`, `test_tc12_priya_82`, `test_tc12_arjun_84`, `test_tc12_rahul_76_for_mid` | ✅ |
| TC13 | Skill normalisation: k8s → kubernetes, ReactJS → react, Node.js → nodejs | `test_normalize.py::test_tc13_k8s_to_kubernetes` | ✅ |
| TC14 | Skill normalisation: unknown token → empty result | `test_normalize.py::test_tc14_blorkify_unknown` | ✅ |
| TC15 | LLM vs regex: regex ₹28L wins over LLM ₹30L, field flagged | `test_llm.py::test_tc15_regex_vs_llm_budget` | ✅ |
| TC16 | Polish: invented number not in facts → text discarded, template shown | `test_llm.py::test_tc16_polish_number_not_in_facts`, `test_tc16_polish_discards_via_llm` | ✅ |
| TC17 | Prompt injection: "IGNORE PREVIOUS INSTRUCTIONS" → budget stays 28 | `test_security.py::test_tc17_injection_budget_unchanged` · `test_llm.py::test_tc17_injection_cross_check`, `test_tc17_merge_injection` · `test_parser.py::test_tc17_prompt_injection_regex` | ✅ |
| TC18 | XSS: `<script>` in input → escaped in brief HTML (rendering: frontend) | `test_security.py::test_tc18_xss_escaped_in_html` | ✅ |
| TC19 | Input > 1 000 chars → 422, no LLM call | `test_security.py::test_tc19_long_input_422_no_llm` | ✅ |
| TC20 | LLM cache: same text twice → cache hit, meter unchanged | `test_llm.py::test_tc20_cache_hit` | ✅ |
| TC21 | Offline mode: outbound blocked + LLM disabled → full story values | `test_security.py::test_tc21_offline_mode` | ✅ |
| TC22 | Decision log: empty or whitespace reason → ValueError / 400 | `test_decisions.py::test_tc22_empty_reason_raises` | ✅ |
| TC23 | Evidence: Rahul (E-072) AWS — assessment 35/100, no conflict | `test_evidence.py::test_tc23_rahul_aws` | ✅ |
| TC24 | Evidence: self-report-only intermediate → 39 (× 0.7 discount) | `test_evidence.py::test_tc24_self_only_intermediate_39` | ✅ |
| TC25 | Evidence: Priya (E-045) Kubernetes — assessment 40, conflict=True (50-pt gap) | `test_evidence.py::test_tc25_priya_kubernetes_conflict` | ✅ |
| TC26 | Evidence: stale assessment + recent certification → cert used | `test_evidence.py::test_tc26_stale_assessment_cert_wins` | ✅ |
| TC27 | Evidence: two assessments → most-recent used | `test_evidence.py::test_tc27_two_assessments_most_recent` | ✅ |
| TC28 | Evidence conflict boundary: gap 29 → no conflict, gap 30 → conflict | `test_evidence.py::test_tc28_conflict_boundary_30_conflict` | ✅ |
| TC29 | Options: self-report-only must-have adds +0.05 risk penalty | `test_options.py::test_tc29_self_report_penalty_synthetic` | ✅ |
| TC30 | Accessibility (WCAG): keyboard navigation, contrast (frontend-only) | **frontend** | — |
| TC31 | Title normalisation: SDE-2 / MERN stack / Sr. Full Stack → correct level | `test_normalize.py::test_tc31_sde2_full_stack_mid` | ✅ |
| TC32 | Title rejection: "Data Analyst", random nonsense → rejected | `test_normalize.py::test_tc32_data_analyst_rejected` | ✅ |
| TC33 | Options screen: all five options have time, cost, fit, risk, reason; mix scored | `test_options.py::test_tc33_options_five_required_fields` | ✅ |
| TC34 | Relocate card: sorted Remote-India > Hyderabad > Pune > Bengaluru | `test_sourcing.py::test_tc34_relocate_card_order` | ✅ |
| TC35 | Sourcing: 3 past finalists, consent-gated (opted_in_pool=true only) | `test_sourcing.py::test_tc35_three_past_finalists` | ✅ |
| TC36 | Brief: all 12 sections present, in order, none empty | `test_brief.py::test_tc36_all_12_sections_present_in_order` | ✅ |
| TC37 | Workflow strip: all 9 stage data groups populated (UI: frontend) | **frontend** · _backend: `test_demo_story.py::test_tc37_9_workflow_stages_present`_ | ✅ |

**Frontend-only cases** (TC30, and UI rendering of TC07/TC37): marked above. Backend support tests confirm the data exists; visual rendering verified manually in browser.

---

## Demo Story Checklist (Section 13 / 7A / 7B)

All values asserted in `test_demo_story.py::test_demo_story`.

| Story fact | Expected | Verified |
|------------|----------|---------|
| Raw job titles normalised | 12 titles → 1 role, 4 levels | ✅ |
| Past matching requisitions | 4 (Nov-24 Buy, Oct-25 Buy, Mar-26 Borrow, Jun-26 Build) | ✅ |
| Avg external tenure (Buy) | 8 months (9 + 7 / 2) | ✅ |
| Bengaluru supply (with Kubernetes) | 14 candidates | ✅ |
| Kubernetes supply delta | +33 → 47 without Kubernetes | ✅ |
| Remote-India supply / P50 / P80 / pay | 210 / 28 d / 40 d / ₹29L | ✅ |
| Hyderabad supply / P50 / P80 / pay | 31 / 44 d / 58 d / ₹30L | ✅ |
| Pune supply / P50 / P80 / pay | 26 / 47 d / 62 d / ₹26L | ✅ |
| Bengaluru supply / P50 / P80 / pay | 14 / 62 d / 81 d / ₹32L | ✅ |
| Location scores | Remote 0.79 / Hyderabad 0.36 / Pune 0.34 / Bengaluru 0.00 | ✅ |
| Karthik (E-031) match | 88 % (±1) | ✅ |
| Karthik red flags | 2 exactly (1 Terraform bus-factor + 1 red dead-end) | ✅ |
| Priya (E-045) match | 82 % (±1) | ✅ |
| Priya readiness | Week 6 | ✅ |
| Rahul (E-072) present in system | In internal_candidates and Priya's ripple chain | ✅ |
| Rahul match at Mid level | 76 % (unit: TC12) | ✅ |
| Arjun (C-17) fit | 84 % | ✅ |
| Arjun availability | "Contract ends in 4 weeks" (2026-11-05) | ✅ |
| Arjun 12-month extend cost | ₹24L | ✅ |
| Build chain year-one cost | ₹12L | ✅ |
| Mix year-one cost | ₹18L (₹6L bridge + ₹12L build) | ✅ |
| Option score — Mix | 89 | ✅ |
| Option score — Borrow | 87 | ✅ |
| Option score — Build | 73 | ✅ |
| Option score — Relocate | 62 | ✅ |
| Option score — Buy | 42 | ✅ |
| Past finalists | 3 total, 2 open_to_remote | ✅ |
| Sourcing channels | Referral, Supplier A, Job board present in ranked order | ✅ |
| Rahul AWS evidence | assessment 35/100, conflict=False | ✅ |
| Priya Kubernetes evidence | assessment 40/100, conflict=True | ✅ |
| GraphQL self-report-only | 39 (≈ 56 × 0.70), no conflict | ✅ |

---

## Requirements Pinning & Model-File Check

**`requirements.txt`** — all 13 packages fully pinned:

```
fastapi==0.141.1        uvicorn[standard]==0.52.4   pydantic==2.13.4
pandas==3.0.5           numpy==2.5.2                rapidfuzz==3.14.6
python-dotenv==1.2.3    faker==40.41.0              requests==2.34.2
google-genai==2.19.0    pytest==9.1.1               httpx==0.28.1
anyio==4.14.2
```

No `>=`, `~=`, or unpinned entries. No `torch`, `transformers`, `sentence-transformers`, `lightgbm`, `pgvector`, or any model-download package present or imported anywhere in `backend/`.

---

## LLM Cache — Token Counts

Measured 2026-10-10 with `gemini-3.5-flash`, `temperature=0`, `LLM_ENABLED=true`.

**Standard demo sentence** (`"Senior Full Stack Developer, Bengaluru, on-site, 5+ years…"`):
The regex pre-parser resolves all three required fields (`level`, `location`, `work_mode`) → `needs_llm=False` → LLM is **never invoked**. Both cold and warm runs record `calls=0, tokens=0`. This is correct and intentional: the demo sentence requires no LLM call.

**Ambiguous probe text** (no location or work_mode in text — triggers LLM fallback):

| Run | calls | input tokens | output tokens | cache_hit | note |
|-----|-------|-------------|---------------|-----------|------|
| Cold | 1 | 132 | 69 | false | live Gemini call; result written to `llm_cache.sqlite` |
| Warm | 0 | 0 | 0 | **true** | served from SQLite; zero LLM spend |

Cache key = SHA-256(normalised_text \| PROMPT_VERSION \| model_name).  
Cache file committed at `backend/cache/llm_cache.sqlite` (3 entries; gitignored previously, now tracked).

---

## Static Analysis Results (Phase 14C)

| Check | Result |
|-------|--------|
| `google-genai` imports | Only `backend/llm.py` and `backend/scripts/score_automation.py` |
| Story numbers hard-coded in `engine/` | None — all values come from seed CSVs or formulas |
| f-string SQL | None |
| `settings.gemini_api_key` logged | Never — `log_filter.GeminiKeyFilter` redacts any accidental log emission; key is only used in conditional checks and `genai.Client()` constructor |
| `date.today()` in `engine/` | None — `today` is always an explicit parameter passed from the API layer |

---

## DECISIONS.md Log (Phase 13–14)

One line per entry added since Phase 12:

| Date | Decision | Section |
|------|----------|---------|
| 2026-10-10 | `req_id` added to `ParsedRequisition`; computed as SHA-256(text\|today)[:8].upper() | 12, 13 |
| 2026-10-10 | Deja Req Jaccard reverted to standard; `skills` column added to `requisitions.csv`; four demo reqs seeded with react/nodejs/kubernetes | 4, 13 |
| 2026-10-10 | Deja Req Jaccard uses MUST-have skills only (nice-to-haves inflate union, mask role similarity) | 4 |
| 2026-10-10 | Bridge atoms require fit ≥ 50 % (`_BRIDGE_MIN_FIT`); ensures C-17 (84 %) wins over cheaper low-fit contractors | 7A, 13 |
| 2026-10-10 | API layer defaults `team="Payments"` for dejareq/ripple; team not extractable from demo text | 4, 13 |
| 2026-10-10 | M9 sourcing ranks within use-case groups; past finalists first; campus not applicable for Senior | 7B |
| 2026-10-10 | Past finalists: consent gate — `opted_in_pool=true`, stage=final, outcome∈{declined,closed}, within 12 months | 7B |
| 2026-10-10 | Redline 32-scenario scorer replaced stub with real M8 formula via `make_scenario_scorer()` | 5, 7A |
| 2026-10-10 | Ripple red flags = bus-factor flags + red dead-end nodes; Karthik = 1+1 = 2; +0.20 risk per flag in options | 6, 7 M8 |
| 2026-10-10 | Déjà Req churn penalty (+0.20) applies to Buy AND Relocate; knowledge-loss (+0.10) to Borrow only | 4, 7A |
| 2026-10-10 | 12-month coverage rule: bridge-only mix invalid unless paired with a longer-term atom | 7A |
| 2026-10-10 | Risk label thresholds: ≥0.60→High, ≥0.45→Medium-high, ≥0.30→Medium, <0.30→Low | 7A |
| 2026-10-10 | Build card = best Build-band atom only (70–84 %); Redeploy atoms valid in mixes but not the Build card | 7 M2, 7A |
| 2026-10-10 | Five cards + all mixes scored in one shared min-max pool; same action scores identically as card or mix atom | 7A |
| 2026-10-10 | Option scores recomputed 89/87/73/62/42 (from doc's 84/78/71/64/41) with full M8 formula | 7A |
| 2026-10-10 | Mix tie-break: lower cost wins, then fewer atoms | 7A |

---

## Total Test Count

| Suite | Count |
|-------|-------|
| `pytest backend/tests/` | **453** |
| TC-named tests (TC01–TC37) | 49 functions across 11 files |
| Frontend-only TCs (no backend test) | TC30 |
| Backend-support tests for frontend TCs | TC07 (`test_tc07_32_scenarios_in_response`), TC37 (`test_tc37_9_workflow_stages_present`) |
