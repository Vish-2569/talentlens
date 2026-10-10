# TalentLens — Screen Map

## Workflow Strip (top of every screen)

A 9-step progress bar. Each step lights up as its data arrives in the analysis result. Steps are clickable.

| Step | Label | Shown in | Engine |
|---|---|---|---|
| 1 | Workforce need | Tab 1: requisition box, parsed fields, Déjà Req banner | Parser, Déjà Req |
| 2 | Role / skill analysis | Tab 1: title normalization panel, Redline sentence | M1, Redline |
| 3 | Internal talent | Tab 2: internal candidates, skill bars + evidence tags, Ripple trees | M2, M3, Ripple |
| 4 | Contractor talent | Tab 2: contractor card (extend vs convert) | M4 |
| 5 | External market | Tab 2: supply and time-to-fill card | M5 |
| 6 | Location and compensation | Tab 2: relocate card + pay bands | M5, M6 |
| 7 | Build / Buy / Borrow / Automate / Relocate | Tab 2: five-option table | M7, M8 |
| 8 | Human decision | Tab 3: Approve / Modify / Reject + reason | Decision Log |
| 9 | Recruiting or development action | Tab 3: generated actions + sourcing channels | M9 |

---

## Tab 1 — "Challenge the request"

**State:** default tab (no URL routing; tab state in React context only)

### Sections (top to bottom)

1. **Requisition input box**
   - Textarea starts empty; submit button calls `POST /api/analyze`
   - Secondary "Use the example request" button (keyboard shortcut F3) fills the textarea with the exact demo sentence: *"Senior Full Stack Developer, Bengaluru, on-site, 5+ years, must know React, Node.js and Kubernetes, budget ₹28L, need in 30 days."*

2. **Request summary + parsed field chips** (shown immediately after submit; `AnalysisResult.parsed`)
   - One-line summary: role, level, location, work_mode from parsed fields
   - Chip row: one chip per parsed field (level, headcount, location, work_mode, min_years, budget_lpa, need_by_days, criticality); each chip shows the value and a confidence label badge (stated / inferred / computed); `InfoTip` shows the span text that produced it

3. **Requisition Redline** — visual hero (`AnalysisResult.redline`)
   - `RedlineText` component: the original sentence, split at `constraint.span_start` / `span_end`; each constrained phrase wrapped in a `<mark>` with severity styling
   - Red mark = solid double underline + ▲ "High cost" label; Amber mark = dotted underline + ◆ "Moderate cost" label; each mark also has `InfoTip` showing `constraint.hover_text` (supply_delta, days_delta, rupees_delta_lpa)
   - Constraint cards below the sentence: one card per constraint — kind, value, severity chip, Relax/Keep toggle
   - Relax/Keep toggle: client-side dictionary lookup into `redline.scenarios` (32 pre-computed entries keyed by 5-bit mask string); no network call
   - Live recommendation panel (right of / below the sentence): updates on every toggle; shows `scenarios[mask].panel_text` and top option name, score, cost from `scenarios[mask].options[]`; `aria-live="polite"` on the panel

4. **Déjà Req evidence panel** (`AnalysisResult.dejareq`)
   - Layout: beside the Redline on screens ≥ 1024 px; below it on narrower screens
   - Chip + banner text when `match_count > 0`; hidden when `match_count = 0`
   - `insight_text` paragraph
   - Timeline table (`dejareq.timeline[]`): req_id, opened, decision, time_to_fill_days, first_year_cost_lpa, outcome_text
   - Averages by decision (`dejareq.averages_by_decision[]`): avg_tenure_months, avg_cost_lpa
   - Patterns list (`dejareq.patterns[]`): only fired patterns; show risk_penalty

5. **Title normalization panel** (`AnalysisResult.parsed.title_normalization`) — collapsed by default
   - Native `<details>`/`<summary>` element (no additional dependency); `<summary>` shows the `raw_titles_count` → `role` summary line
   - Expanded: mappings table — raw_title, source_system, method, confidence

### Story values that must appear on this tab

| Fact | Source field | Expected |
|---|---|---|
| Raw titles → 1 role | `parsed.title_normalization.raw_titles_count` | 12 |
| Past matching reqs | `dejareq.match_count` | 4 |
| Avg external tenure | `dejareq.averages_by_decision` (buy row) `.avg_tenure_months` | 8 months |
| Bengaluru on-site Senior supply | Redline location constraint hover | 14 candidates |
| Without Kubernetes | Redline Kubernetes constraint hover | 47 candidates (removes 70%) |
| "need in 30 days" not achievable via Buy | Redline deadline constraint hover | Bengaluru P80 = 81 days |

---

## Tab 2 — "Weigh the options"

### Sections (top to bottom)

1. **Ripple Effect** (`AnalysisResult.ripple`)
   - Two candidate cards for top 2 internal candidates: display_name, match %, net_impact
   - Ripple tree: nested flex cards per `RippleNode`; green = filled, red = gap/risk, pending = open
   - Skill bars with evidence tags per person (click name → `GET /api/people/{id}/skills`)
   - `SkillBar` component: value as filled bar + Mono numeral
   - `SourceTag` component: solid / half-filled / outlined per source; icon + text label; `InfoTip` with full tooltip

2. **Five-option table** (`AnalysisResult.options.five[]`)
   - Columns: name, ready_by_p80_days, year_one_cost_lpa, fit, risk_label, score, reason
   - Recommended mix row highlighted (highest score)
   - Mixes panel (`options.mixes[]`): atoms list, score, ready_by_p80_days, year_one_cost_lpa

3. **Weight sliders** (`options.weights`) — **conditional**
   - Built only if each `OptionCard` in `options.five[]` exposes its five per-dimension values (speed, cost, fit, risk, strategic) so the client can recompute a weighted sum.
   - **If those per-dimension values are absent from the API response: STOP. Propose the smallest backend change** (add a `dim_scores: {speed, cost, fit, risk, strategic}` field to `OptionCard` in `schemas.py` + a test + a DECISIONS.md entry) before building this component.
   - When the values are present: Radix Slider ×5, default weights from `options.weights`; client-side weighted sum must reproduce the backend `score` exactly at default weights before any slider is moved.

4. **Contractor card** (`options.contractor_cards[]`)
   - display_name, fit %, availability, extend_cost_lpa, conversion_signal, compliance_flag
   - Evidence tags via `SkillBar` + `SourceTag`

5. **Relocate card** (`options.relocate_card[]`)
   - Table: location, supply, ttf_p50, ttf_p80, pay_p50_lpa, score
   - Bengaluru row shown as baseline (score 0.00)

6. **Sourcing channels** (`options.sourcing`)
   - Ranked table: channel, evidence, use_for
   - Past finalists list: stage_reached, outcome, open_to_remote
   - Supplier rankings: name, fill_rate, median_days_to_submit

### Story values that must appear on this tab

| Fact | Source field | Expected |
|---|---|---|
| Karthik match | `ripple.candidates[0].match` | 88% |
| Priya match | `ripple.candidates[1].match` | 82% |
| Priya ready by | `ripple.candidates[1]` readiness_weeks (via net_impact / internal_candidates) | Week 6 |
| Arjun fit | `options.contractor_cards[0].fit` | 84% |
| Arjun 3-month bridge cost | `options.contractor_cards[0]` / mixes | ₹6L |
| Mix score | `options.mixes[0].score` | 89 |
| Borrow score | `options.five` (borrow row) `.score` | 87 |
| Build score | `options.five` (build row) `.score` | 73 |
| Relocate score | `options.five` (relocate row) `.score` | 62 |
| Buy score | `options.five` (buy row) `.score` | 42 |
| Remote-India supply | `options.relocate_card` (remote_india row) `.supply` | 210 |
| Remote-India P50 TTF | `options.relocate_card` (remote_india row) `.ttf_p50` | 28 days |
| Remote-India P80 TTF | `options.relocate_card` (remote_india row) `.ttf_p80` | 40 days |
| Remote-India pay | `options.relocate_card` (remote_india row) `.pay_p50_lpa` | ₹29L |
| Bengaluru P50 TTF | `options.market_card.ttf_p50` | 62 days |
| Bengaluru P80 TTF | `options.market_card.ttf_p80` | 81 days |
| Bengaluru pay P50 | `options.market_card.sal_p50` | ₹32L |
| Priya Kubernetes ⚠ | `SkillScore.conflict = true` | Assessment 40/100 vs self-reported expert → ⚠ |
| Karthik Terraform cert | `SkillScore.source = "certification"` | Terraform Associate 2025 |
| GraphQL self-report only | `SkillScore.source = "self"` | 39% (×0.7 discount) |
| Past finalists | `options.sourcing.past_finalists.length` | 3 (2 open to remote) |

---

## Tab 3 — "Decide"

### Sections (top to bottom)

1. **Workforce Intelligence Brief** (`AnalysisResult.brief`)
   - Renders `brief.sections[]` as collapsible sections (key, title, markdown)
   - Markdown rendered as safe HTML via a markdown library — `dangerouslySetInnerHTML` is banned; use a sanitising renderer
   - Assumption Ledger: constraints kept/relaxed and their costs (from redline state)
   - Decision boundaries list (`options.decision_boundaries[]`)

2. **Data quality line** (`AnalysisResult.data_quality`)
   - `data_quality.line` string displayed prominently
   - Breakdown: conflicts, stale, self_report_only counts

3. **Decision form** → `POST /api/decisions`
   - Fields: req_id (from analysis), option_id (radio from five options), verb (Approve / Modify / Reject), decided_by (text, required), reason (textarea, min 1 char)
   - relaxed_mask: 5-bit string built from current Relax/Keep toggle state (carried from Tab 1 via context)
   - Submit disabled until decided_by and reason are non-empty

4. **Generated actions** (shown after successful POST /api/decisions)
   - Workflow step 9 lights up
   - Action list rendered from brief sections (backfill request, contract extension, ATS requisition, development plan)

5. **Token meter** (`AnalysisResult.tokens`)
   - calls, cache_hit, est_cost
   - Shows "0 live tokens, cached" when cache_hit = true

---

## Component Index

| Component | Used in | Notes |
|---|---|---|
| `WorkflowStrip` | All tabs | 9 steps; lights up per analysis result fields |
| `RedlineText` | Tab 1 | Splits text at char spans; `<mark>` per constraint |
| `ConstraintCard` | Tab 1 | Relax/Keep toggle; 32-scenario dictionary lookup |
| `DejaReqBanner` | Tab 1 | Chip + insight + timeline table |
| `TitleNormPanel` | Tab 1 | raw_titles_count → role; mappings table |
| `SkillBar` | Tab 2 | Value as filled bar + IBM Plex Mono numeral |
| `SourceTag` | Tab 2 | solid/half/outlined; icon + text label; `InfoTip` |
| `RippleTree` | Tab 2 | Nested flex cards per RippleNode; colour + text status |
| `OptionTable` | Tab 2 | Five options + mixes; recommended row highlighted |
| `WeightSliders` | Tab 2 | Radix Slider ×5; client-side re-rank at default weights |
| `ContractorCard` | Tab 2 | Fit, availability, extend cost, conversion signal |
| `RelocateCard` | Tab 2 | Location comparison table with baseline row |
| `SourcingPanel` | Tab 2 | Channels table + past finalists + supplier rankings |
| `InfoTip` | All | Radix Tooltip (hover/focus) + Popover (tap) in one wrapper |
| `BriefViewer` | Tab 3 | Collapsible sections; markdown → safe HTML |
| `DecisionForm` | Tab 3 | POST /api/decisions; disabled until valid |
| `TokenMeter` | Tab 3 | calls, cache_hit, est_cost display |
