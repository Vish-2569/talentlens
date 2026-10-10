from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


# ── Enums ──────────────────────────────────────────────────────────────

class Level(str, Enum):
    junior = "junior"
    mid = "mid"
    senior = "senior"
    lead = "lead"


class Location(str, Enum):
    bengaluru = "bengaluru"
    hyderabad = "hyderabad"
    pune = "pune"
    remote_india = "remote_india"
    other = "other"


class WorkMode(str, Enum):
    onsite = "onsite"
    hybrid = "hybrid"
    remote = "remote"


class SkillImportance(str, Enum):
    must = "must"
    nice = "nice"


class ConfidenceLabel(str, Enum):
    stated = "stated"
    inferred = "inferred"
    computed = "computed"
    simulated = "simulated"


class Severity(str, Enum):
    red = "red"
    amber = "amber"
    none = "none"


class RippleStatus(str, Enum):
    green = "green"
    red = "red"
    pending = "pending"


class EvidenceSource(str, Enum):
    assessment = "assessment"
    certification = "certification"
    project = "project"
    self_report = "self"


class TitleMethod(str, Enum):
    esco_alt = "esco_alt"
    onet = "onet"
    manual = "manual"
    fuzzy = "fuzzy"


class ConstraintSource(str, Enum):
    stated = "stated"
    inferred = "inferred"


class DecisionType(str, Enum):
    build = "build"
    buy = "buy"
    borrow = "borrow"


class ConstraintKind(str, Enum):
    location = "location"
    years = "years"
    skill = "skill"
    budget = "budget"
    deadline = "deadline"


# ── Request models ─────────────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(..., min_length=1, max_length=1000)


class DecisionVerb(str, Enum):
    approve = "Approve"
    modify = "Modify"
    reject = "Reject"


class DecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    req_id: str
    option_id: str
    verb: DecisionVerb
    relaxed_mask: str = Field(..., pattern=r"^[01]{5}$")
    decided_by: str = Field(..., min_length=1)
    reason: str = Field(..., min_length=1)


# ── Parsed requisition ─────────────────────────────────────────────────

class ParsedSkill(BaseModel):
    model_config = ConfigDict(extra="forbid")
    skill_id: str
    importance: SkillImportance
    confidence: float


class ParsedField(BaseModel):
    model_config = ConfigDict(extra="forbid")
    value: Optional[str | int | float] = None
    span: Optional[str] = None
    span_start: Optional[int] = None
    span_end: Optional[int] = None
    label: ConfidenceLabel


class TitleMapping(BaseModel):
    model_config = ConfigDict(extra="forbid")
    raw_title: str
    source_system: str
    role: str
    level: Optional[Level] = None
    method: TitleMethod
    confidence: float
    esco_uri: Optional[str] = None
    onet_code: Optional[str] = None


class TitleNormalization(BaseModel):
    model_config = ConfigDict(extra="forbid")
    raw_titles_count: int
    role: str
    levels: list[Level]
    mappings: list[TitleMapping]


class ParsedRequisition(BaseModel):
    model_config = ConfigDict(extra="forbid")
    req_id: str
    level: ParsedField
    headcount: ParsedField
    location: ParsedField
    work_mode: ParsedField
    min_years: ParsedField
    budget_lpa: ParsedField
    need_by_days: ParsedField
    duration_months: ParsedField
    criticality: ParsedField
    skills: list[ParsedSkill]
    title_normalization: TitleNormalization


# ── Deja Req ───────────────────────────────────────────────────────────

class TimelineEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")
    req_id: str
    opened: str
    decision: str
    time_to_fill_days: Optional[int] = None
    ramp_note: Optional[str] = None
    first_year_cost_lpa: float
    outcome_text: str
    evidence_ids: list[str]


class AverageByDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision: str
    count: int
    avg_tenure_months: Optional[float] = None
    avg_cost_lpa: float
    avg_time_to_fill_days: Optional[float] = None


class Pattern(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    fired: bool
    text: str
    risk_option: Optional[str] = None
    risk_penalty: float


class DejaReq(BaseModel):
    model_config = ConfigDict(extra="forbid")
    match_count: int
    banner_text: Optional[str] = None
    chip: Optional[str] = None
    timeline: list[TimelineEntry]
    averages_by_decision: list[AverageByDecision]
    patterns: list[Pattern]
    insight_text: Optional[str] = None


# ── Redline ────────────────────────────────────────────────────────────

class ConstraintCost(BaseModel):
    model_config = ConfigDict(extra="forbid")
    supply_delta: Optional[int] = None
    days_delta: Optional[float] = None
    rupees_delta_lpa: Optional[float] = None


class Constraint(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    kind: ConstraintKind
    value: str
    phrase: str
    span_start: int
    span_end: int
    source: ConstraintSource
    severity: Severity
    hover_text: str
    cost: ConstraintCost
    relaxed_value: Optional[str] = None


class OptionSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")
    option_id: str
    name: str
    score: Optional[float] = None
    ready_by_p80_days: Optional[int] = None
    year_one_cost_lpa: Optional[float] = None
    panel_line: str


class ScenarioResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    top_option_id: str
    panel_text: str
    options: list[OptionSummary]


class Redline(BaseModel):
    model_config = ConfigDict(extra="forbid")
    constraints: list[Constraint]
    constraint_order: list[ConstraintKind]
    scenarios: dict[str, ScenarioResult]


# ── Ripple ─────────────────────────────────────────────────────────────

class RippleNode(BaseModel):
    model_config = ConfigDict(extra="forbid")
    seat: str
    person_id: Optional[str] = None
    display_name: Optional[str] = None
    status: RippleStatus
    reason: str
    children: list[RippleNode] = Field(default_factory=list)


class NetImpact(BaseModel):
    model_config = ConfigDict(extra="forbid")
    days_to_fill_last_gap: Optional[int] = None
    total_cost_lpa: float
    promotions: int
    red_flags: int


class RippleCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    person_id: str
    display_name: str
    match: float
    chain: RippleNode
    net_impact: NetImpact


class Ripple(BaseModel):
    model_config = ConfigDict(extra="forbid")
    candidates: list[RippleCandidate]


# ── Options ────────────────────────────────────────────────────────────

class OptionCard(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    name: str
    what_it_means: str
    ready_by_p80_days: Optional[int] = None
    year_one_cost_lpa: Optional[float] = None
    fit: Optional[str] = None
    risk_label: str
    risk_value: float
    score: Optional[float] = None
    reason: str
    evidence_ids: list[str]


class RelocateRow(BaseModel):
    model_config = ConfigDict(extra="forbid")
    location: str
    supply: int
    ttf_p50: int
    ttf_p80: int
    pay_p50_lpa: float
    score: float


class MarketCard(BaseModel):
    model_config = ConfigDict(extra="forbid")
    location: str
    level: str
    supply: int
    demand: int
    sal_p25: float
    sal_p50: float
    sal_p75: float
    ttf_p50: int
    ttf_p80: int


class ContractorCard(BaseModel):
    model_config = ConfigDict(extra="forbid")
    person_id: str
    display_name: str
    fit: float
    availability: str
    extend_cost_lpa: float
    convert_saving_lpa: Optional[float] = None
    conversion_signal: bool
    compliance_flag: bool
    evidence_ids: list[str]


class InternalCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    person_id: str
    display_name: str
    match: float
    band: str
    readiness_weeks: Optional[int] = None
    build_cost_lpa: Optional[float] = None
    evidence_ids: list[str]


class SourcingChannel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rank: Optional[int] = None
    channel: str
    evidence: str
    use_for: str


class PastFinalist(BaseModel):
    model_config = ConfigDict(extra="forbid")
    candidate_id: str
    stage_reached: str
    outcome: str
    decided_on: str
    open_to_remote: bool


class SupplierRanking(BaseModel):
    model_config = ConfigDict(extra="forbid")
    supplier_id: str
    name: str
    fill_rate: float
    median_days_to_submit: int
    avg_bill_rate: Optional[float] = None


class Sourcing(BaseModel):
    model_config = ConfigDict(extra="forbid")
    channels: list[SourcingChannel]
    past_finalists: list[PastFinalist]
    suppliers: list[SupplierRanking]


class OptionWeights(BaseModel):
    model_config = ConfigDict(extra="forbid")
    speed: float
    cost: float
    fit: float
    risk: float
    strategic: float


class MixOption(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    name: str
    atoms: list[str]
    score: float
    ready_by_p80_days: int
    year_one_cost_lpa: float
    reason: str


class Options(BaseModel):
    model_config = ConfigDict(extra="forbid")
    five: list[OptionCard]
    mixes: list[MixOption]
    relocate_card: list[RelocateRow]
    market_card: MarketCard
    contractor_cards: list[ContractorCard]
    internal_candidates: list[InternalCandidate]
    sourcing: Sourcing
    decision_boundaries: list[str]
    weights: OptionWeights


# ── Brief ──────────────────────────────────────────────────────────────

class BriefSection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    key: str
    title: str
    markdown: str


class Brief(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sections: list[BriefSection]
    markdown: str
    html: str


# ── Data quality ───────────────────────────────────────────────────────

class DataQuality(BaseModel):
    model_config = ConfigDict(extra="forbid")
    conflicts: int
    stale: int
    self_report_only: int
    line: str


# ── Tokens ─────────────────────────────────────────────────────────────

class Tokens(BaseModel):
    model_config = ConfigDict(extra="forbid")
    calls: int
    input_tokens: int
    output_tokens: int
    cache_hit: bool
    est_cost: float


# ── Top-level analysis result ──────────────────────────────────────────

class AnalysisResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    parsed: ParsedRequisition
    dejareq: DejaReq
    redline: Redline
    ripple: Ripple
    options: Options
    brief: Brief
    data_quality: DataQuality
    tokens: Tokens


# ── Skill score (GET /api/people/{id}/skills) ──────────────────────────

class IgnoredSource(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source: str
    value: float
    reason: str


class SkillScore(BaseModel):
    model_config = ConfigDict(extra="forbid")
    skill: str
    value: float
    source: str
    observed_on: str
    confidence: float
    stale: bool
    conflict: bool
    tooltip: str
    ignored: list[IgnoredSource]


# ── Health ─────────────────────────────────────────────────────────────

class Health(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ok: bool
    cache_loaded: bool
    llm_configured: bool
