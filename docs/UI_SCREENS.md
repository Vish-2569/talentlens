# TalentLens — Screen Map

## Navigation model

The UI uses a single 9-step `WorkflowStrip` as its only navigation. There are no tabs. Clicking a step shows **only** that step's section(s); all other sections are hidden. One step is active at a time (`aria-current="step"`). After a successful analysis the app opens on step 1. URL hash `#step-N` is kept in sync so the browser back button works.

Steps 2–9 are disabled before an analysis exists (rendered as `<span aria-disabled="true">`). Steps 8–9 are reachable before a decision is recorded and show a "pending" notice until one is approved.

Back / Next buttons appear at the bottom of every step. On step change, focus moves to the step heading (`tabIndex={-1}`) and the page scrolls to the top. State (mask, sliders, drawer cache, decision) is preserved across step changes.

## Step definitions

| Step | Label | Short label | Heading ID | Sections shown |
|------|-------|------------|------------|----------------|
| 1 | Workforce need | Need | step-1-heading | Request composer (textarea → `POST /api/analyze`), parsed field chips, Déjà Req banner, Requisition Redline (sentence + constraint cards + live panel) |
| 2 | Role / skill analysis | Skills | step-2-heading | Title normalisation panel, internal candidates skill bars + evidence tags, data quality line |
| 3 | Internal talent | Internal | step-3-heading | Ripple Effect trees, internal candidate cards, Person drawer |
| 4 | Contractor talent | Contractors | step-4-heading | Contractor cards (extend vs convert) |
| 5 | External market | Market | step-5-heading | Market card (supply, TTF, pay), sourcing channels table, past finalists |
| 6 | Location and compensation | Location | step-6-heading | Relocate card (location comparison), compensation guidance from brief |
| 7 | Five options | Options | step-7-heading | Recommended mix card, five-option table (Build / Buy / Borrow / Relocate / Automate), weight sliders, mask notice |
| 8 | Human decision | Decision | step-8-heading | Workforce Intelligence Brief, decision form (`POST /api/decisions`), pending notice until decision recorded |
| 9 | Recruiting action | Action | step-9-heading | Generated action list (from brief actions section), pending notice until decision recorded |

## Step lighting

A step "lights up" (filled badge + accent colour) when its data is present in the analysis result:

| Step | Lights when |
|------|------------|
| 1 | `parsed` is set |
| 2 | `redline.constraints.length > 0` |
| 3 | `ripple.candidates.length > 0` |
| 4 | `options.contractor_cards.length > 0` |
| 5 | `options.market_card` is set |
| 6 | `options.relocate_card.length > 0` |
| 7 | `options.five.length > 0` |
| 8 | Decision recorded |
| 9 | Decision recorded AND `brief.sections.length > 0` |

---

## Step 1 — Workforce need

### Sections (top to bottom)

1. **Requisition input box**
   - Textarea starts empty; submit button calls `POST /api/analyze`
   - Secondary "Use the example request" button fills the textarea with the exact demo sentence: *"Senior Full Stack Developer, Bengaluru, on-site, 5+ years, must know React, Node.js and Kubernetes, budget ₹28L, need in 30 days."*

2. **Request summary + parsed field chips** (shown after submit; `AnalysisResult.parsed`)
   - One-line summary: role, level, location, work_mode from parsed fields
   - Chip row: one chip per parsed field; each chip shows the value and a confidence label badge (stated / inferred / computed); `InfoTip` shows the span text that produced it

3. **Requisition Redline** — visual hero (`AnalysisResult.redline`)
   - `RedlineText` component: original sentence split at constraint spans; each constrained phrase in a `<mark>` with severity styling
   - Constraint cards below the sentence: kind, value, severity chip, Relax/Keep toggle
   - Toggle: client-side dictionary lookup into `redline.scenarios` (32 pre-computed entries keyed by 5-bit mask string); no network call
   - Live recommendation panel: updates on every toggle; shows `scenarios[mask].panel_text` and top option; `aria-live="polite"`

4. **Déjà Req evidence panel** (`AnalysisResult.dejareq`)
   - Beside the Redline on screens ≥ 1024 px; below it on narrower screens
   - Banner text, insight text, timeline table, averages by decision, patterns list
   - "See applied in option scores" link dispatches `SET_STEP(7)` to navigate to step 7

### Story values that must appear on step 1

| Fact | Source field | Expected |
|---|---|---|
| Raw titles → 1 role | `parsed.title_normalization.raw_titles_count` | 12 |
| Past matching reqs | `dejareq.match_count` | 4 |
| Avg external tenure | `dejareq.averages_by_decision` (buy row) `.avg_tenure_months` | 8 months |
| Bengaluru on-site Senior supply | Redline location constraint hover | 14 candidates |
| Without Kubernetes | Redline Kubernetes constraint hover | 47 candidates (removes 70%) |
| "need in 30 days" not achievable via Buy | Redline deadline constraint hover | Bengaluru P80 = 81 days |

---

## Step 2 — Role / skill analysis

- **Title normalisation panel** (`AnalysisResult.parsed.title_normalization`) — collapsed by default; native `<details>`/`<summary>`; expanded shows mappings table
- **Internal candidates skill bars + evidence tags** — `SkillBar` + `SourceTag`; assessment, project, certification, self sources
- **Data quality line** (`AnalysisResult.data_quality`) — conflicts, stale, self_report_only counts

---

## Step 3 — Internal talent

- **Ripple Effect** (`AnalysisResult.ripple`) — candidate cards, match %, net impact, promotions, cost, days_to_fill_last_gap
- **Ripple trees** — nested flex cards per `RippleNode`; green = filled, red = gap/risk
- **Person drawer** — click name → `GET /api/people/{id}/skills`

### Story values

| Fact | Expected |
|---|---|
| Karthik match | 88% |
| Priya match | 82% |
| Priya ready by | Week 6 |

---

## Step 4 — Contractor talent

- **Contractor cards** (`options.contractor_cards[]`) — display_name, fit %, availability, extend_cost_lpa, conversion_signal, compliance_flag

### Story values

| Fact | Expected |
|---|---|
| Arjun fit | 84% |
| Arjun 3-month bridge cost | ₹6L |

---

## Step 5 — External market

- **Market card** (`options.market_card`) — supply, TTF P50/P80, salary P50
- **Sourcing channels** (`options.sourcing`) — ranked table, past finalists list, supplier rankings

### Story values

| Fact | Expected |
|---|---|
| Bengaluru P50 TTF | 62 days |
| Bengaluru P80 TTF | 81 days |
| Bengaluru pay P50 | ₹32L |
| Past finalists | 3 (2 open to remote) |

---

## Step 6 — Location and compensation

- **Relocate card** (`options.relocate_card[]`) — location comparison table with Bengaluru as baseline (score 0.00)
- **Compensation guidance** — from `brief.sections[key="compensation"]`

### Story values

| Fact | Expected |
|---|---|
| Remote-India supply | 210 |
| Remote-India P50/P80 TTF | 28 / 40 days |
| Remote-India pay | ₹29L |
| Pune pay (18% below Bengaluru) | ₹26L |

---

## Step 7 — Five options

- **Recommended mix card** (`options.mixes[]`) — top mix highlighted; atoms list, score, cost, ready-by
- **Five-option table** (`options.five[]`) — columns: name, ready_by_p80_days, year_one_cost_lpa, fit, risk_label, score, reason
- **Weight sliders** (`options.weights`) — Radix Slider ×5; client-side re-rank at default weights must reproduce backend scores exactly
- **Mask notice** — which constraints are assumed relaxed/kept for these options

### Story values

| Fact | Expected |
|---|---|
| Mix score | 89 |
| Borrow score | 87 |
| Build score | 73 |
| Relocate score | 62 |
| Buy score | 42 |

---

## Step 8 — Human decision

- **Workforce Intelligence Brief** (`AnalysisResult.brief`) — collapsible sections (key, title, markdown); Assumption Ledger; decision boundaries list
- **Decision form** → `POST /api/decisions` — verb (Approve / Modify / Reject), decided_by (required), reason (required), relaxed_mask (from current toggle state)
- **Pending notice** — shown until a decision is recorded

---

## Step 9 — Recruiting action

- **Generated action list** — from `brief.sections[key="actions"]`; each item shown as a draft action card ("Draft, not sent")
- **Pending notice** — shown until a decision is recorded

---

## Component Index

| Component | Used in step | Notes |
|---|---|---|
| `WorkflowStrip` | All | 9 steps; lights up per analysis result fields; sole navigation |
| `RedlineText` | 1 | Splits text at char spans; `<mark>` per constraint |
| `RedlineCards` | 1 | Relax/Keep toggle; 32-scenario dictionary lookup |
| `DejaReq` | 1 | Chip + insight + timeline table |
| `TitleNormPanel` | 2 | raw_titles_count → role; mappings table |
| `SkillBar` | 2, 3 | Value as filled bar + IBM Plex Mono numeral |
| `SourceTag` | 2, 3 | solid/half/outlined; icon + text label; `InfoTip` |
| `RippleComparison` | 3 | Candidate cards + Ripple trees |
| `PersonDrawer` | 3 | Slide-in drawer; `GET /api/people/{id}/skills` |
| `ContractorCards` | 4 | Fit, availability, extend cost, conversion signal |
| `MarketCard` | 5 | Supply, TTF P50/P80, salary |
| `SourcingPanel` | 5 | Channels table + past finalists + supplier rankings |
| `RelocateCard` | 6 | Location comparison table with baseline row |
| `RecommendedMix` | 7 | Top mix; atoms list, score, cost |
| `FiveOptionTable` | 7 | All five options; recommended row highlighted |
| `WeightSliders` | 7 | Radix Slider ×5; client-side re-rank |
| `BriefView` | 8 | Collapsible sections; markdown rendered as safe text |
| `DecisionPanel` | 8 | POST /api/decisions; disabled until valid |
| `ActionsPanel` | 9 | Draft action list from brief.sections[actions] |
| `InfoTip` | All | Radix Tooltip (hover/focus) + Popover (tap) in one wrapper |
| `LiveRegion` | All | `aria-live="polite"` for recommendation announcements |
