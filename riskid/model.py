"""The data model: one dataclass per entity in SPEC.md section 4.

Round 1 (PLAN.md section 4, round 1) introduces the model. Every entity is a
``@dataclass`` that mixes in :class:`Model`, which gives it ``to_dict`` and
``from_dict`` (PLAN.md round 1 requires both). ``to_dict`` uses
``dataclasses.asdict`` so nested dataclasses serialise too; ``from_dict``
reconstructs from a dict, keeping only the fields the dataclass declares so
that a stale or foreign dict cannot set attributes that do not exist.

The structured fields the book keeps as a list, dict or pair are left as
plain ``list`` / ``dict`` / ``str`` here; later rounds populate and validate
them. An optional field left untouched carries ``None`` ("not set") rather
than a fake default value, except the structured collections which default to
an empty container.
"""

from dataclasses import asdict, dataclass, fields
from dataclasses import field as dfield
from typing import Any


class Model:
    """Base mixin for every data-model entity (SPEC.md section 4)."""

    def to_dict(self) -> dict:
        """Serialise this entity (and any nested dataclass) to a plain dict."""
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict):
        """Rebuild an entity from a dict, ignoring keys it does not declare."""
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in d.items() if k in known})


# --- Organisation ---------------------------------------------------------

@dataclass
class Organisation(Model):
    name: str = None
    sector: str = None
    jurisdictions: list = dfield(default_factory=list)
    risk_criteria: str = None          # the acceptable-risk statement (ch 5)
    accountable_executive: str = None
    ai_officer: str = None
    facilitator: str = None


# --- System (B.1, 18 fields) ---------------------------------------------

@dataclass
class System(Model):
    id: str = None
    name: str = None
    function: str = None
    components: list = dfield(default_factory=list)
    vendor_or_built: str = None
    supplier: str = None
    contract_ref: str = None
    model_provider: str = None
    model_name: str = None
    model_version: str = None
    version_pinned: bool = None
    last_change_notice: str = None
    purpose_stated: str = None
    purpose_in_use: str = None
    users: list = dfield(default_factory=list)          # (role, number)
    persons_affected: list = dfield(default_factory=list)  # (group, vulnerable flag)
    data: dict = dfield(default_factory=dict)            # training, inputs, personal, ...
    role_under_act: str = None          # provider | deployer | both
    article_25_check: str = None
    article_5_screen: str = None
    article_6_outcome: str = None
    article_6_record_ref: str = None
    article_50_duty: str = None
    owner: str = None
    model_owner: str = None
    data_owner: str = None
    lifecycle_stage: str = None       # one of seven
    jurisdictions: list = dfield(default_factory=list)
    period_and_frequency: str = None
    impact_assessments: dict = dfield(default_factory=dict)  # DPIA, FRIA, 42005
    last_risk_assessment: dict = dfield(default_factory=dict)  # date, version
    discovery_source: str = None      # declared | procurement | scan | audit | incident
    pilot_end_date: str = None
    logs: dict = dfield(default_factory=dict)            # location, retention


# --- Taxonomy (43 rows, versioned with the library) ----------------------

@dataclass
class TaxonomyLine(Model):
    l1_code: str = None
    l1: str = None
    l2_code: str = None
    l2: str = None
    owner_function: str = None


# --- Library (Appendix A, 91 rows, read-only) ----------------------------

@dataclass
class LibraryLine(Model):
    id: str = None
    l1: str = None
    l2: str = None
    title: str = None
    description: str = None
    lifecycle: str = None
    role: str = None
    harmed: str = None
    exposure: str = None
    event: str = None
    L: int = 0
    I: int = 0
    dim: str = None                   # dominant impact dimension (FIN/REG/REP/IND/OPS)
    V: int = 0                        # vulnerability
    S: int = 0                        # speed of onset
    dq: str = None                    # data quality (High | Medium | Low | Very Low)
    controls: str = None
    rL: int = 0                       # residual likelihood
    rI: int = 0                      # residual impact
    owner: str = None
    kri: str = None
    reg: str = None
    sources: str = None


# --- Register (B.3, 14 + 5) ----------------------------------------------

@dataclass
class RegisterLine(Model):
    id: str = None
    system_id: str = None
    l1: str = None
    l2: str = None
    definition: str = None
    coso_category: str = None
    owner: str = None
    status: str = None                # candidate | active | retired
    retired_reason: str = None
    source: str = None                # top-down | bottom-up | library | event
    trend: str = None
    last_review: str = None
    next_review: str = None
    lifecycle_stages: list = dfield(default_factory=list)
    role: str = None
    persons_affected: list = dfield(default_factory=list)
    regulatory_hooks: list = dfield(default_factory=list)
    annex_a_controls: list = dfield(default_factory=list)
    interaction_summary: str = None


# --- Assessment (B.6) -----------------------------------------------------

@dataclass
class Assessment(Model):
    line_id: str = None
    date: str = None
    assessor: str = None
    harm_scored: str = None
    unit_of_exposure: str = None
    impact: dict = dfield(default_factory=dict)   # {FIN, REG, REP, IND, OPS}: 1-5
    dominant_dimension: str = None
    dominant_reasoning: str = None               # required when IND in {4,5} and not dominant
    likelihood: int = 0
    vulnerability: int = 0
    speed: int = 0
    inherent: int = 0
    inherent_band: str = None                     # Low | Moderate | High | Critical
    material: bool = False
    material_rule: str = None
    data_quality: str = None                      # High | Medium | Low | Very Low
    data_quality_basis: str = None
    residual_L: int = 0
    residual_I: int = 0
    residual: int = 0
    acceptable: str = None                        # yes | no
    acceptable_by: str = None
    model_vendor_dependency: str = None
    ai_draft: dict = dfield(default_factory=dict)  # model, version, date
    disagreement: dict = dfield(default_factory=dict)  # minority score, dimension, evidence


# --- Control ----------------------------------------------------------------

@dataclass
class Control(Model):
    line_id: str = None
    name: str = None
    type: str = None                    # preventive | detective | corrective
    owner: str = None
    last_test_date: str = None
    last_test_result: str = None
    evidence_ref: str = None
    annex_a_ref: str = None


# --- Indicator (KRI) --------------------------------------------------------

@dataclass
class Indicator(Model):
    line_id: str = None
    name: str = None
    unit: str = None
    current_value: Any = None
    thresholds: dict = dfield(default_factory=dict)  # green/amber/red
    read_by: str = None
    history: list = dfield(default_factory=list)       # dated values


# --- Use case (B.2) ---------------------------------------------------------

@dataclass
class UseCase(Model):
    system_id: str = None
    headers: dict = dfield(default_factory=dict)   # headers 1-5
    fields_: dict = dfield(default_factory=dict)   # fields 1-11
    submitted_by: str = None
    date: str = None
    status: str = None                   # returned | accepted
    return_reason: str = None
    source: str = None                   # the template or one of the ten sub-processes (ch 7)
    line_id: str = None                  # the register line it created or supports


# --- Workshop (B.5) ---------------------------------------------------------

@dataclass
class Workshop(Model):
    system_ids: list = dfield(default_factory=list)
    date: str = None
    facilitator: str = None
    seats: list = dfield(default_factory=list)      # (role, person, present)
    pre_lists: dict = dfield(default_factory=dict)   # per participant, hidden until stage 2
    swift_answers: dict = dfield(default_factory=dict)  # prompt_id -> covered/not known, control, evidence
    emerging_risks: list = dfield(default_factory=list)
    votes: dict = dfield(default_factory=dict)       # per participant, per candidate
    gap_review: str = None
    record: str = None


# --- Interaction / Bow-tie --------------------------------------------------

@dataclass
class Interaction(Model):
    from_line: str = None
    to_line: str = None
    kind: str = None                    # triggers | amplifies | shared driver
    note: str = None


@dataclass
class BowTie(Model):
    line_id: str = None
    causes: list = dfield(default_factory=list)
    preventive_controls: list = dfield(default_factory=list)
    event: str = None
    recovery_controls: list = dfield(default_factory=list)
    consequences: list = dfield(default_factory=list)


# --- Trigger / Cycle / Contract --------------------------------------------

@dataclass
class Trigger(Model):
    date: str = None
    source: str = None
    text: str = None
    lines_touched: list = dfield(default_factory=list)
    significance: str = None            # significant | not
    decision: str = None
    decided_by: str = None
    resulting_changes: list = dfield(default_factory=list)


@dataclass
class CycleRun(Model):
    kind: str = None                   # monthly | quarterly | annual | event | audit | management review
    date: str = None
    steps: dict = dfield(default_factory=dict)   # B.8 step -> done, evidence, owner, date
    signed_by: str = None
    signed_date: str = None
    next_due: str = None


@dataclass
class Contract(Model):
    system_id: str = None
    clauses: dict = dfield(default_factory=dict)  # clause 1-17 -> present | absent | partial
    reference: str = None
    gap_note: str = None


# --- Document / Event / DataPack -------------------------------------------

@dataclass
class Document(Model):
    kind: str = None
    generated_at: str = None
    inputs_hash: str = None
    file_path: str = None


@dataclass
class Event(Model):
    timestamp: str = None
    actor: str = None
    entity: str = None
    entity_id: str = None
    field: str = None
    old: Any = None
    new: Any = None
    reason: str = None
    evidence_ref: str = None
    ai_draft: dict = dfield(default_factory=dict)  # model, version


@dataclass
class DataPack(Model):
    name: str = None                   # library | regulatory calendar | indicator presets
    version: str = None
    date: str = None
    source: str = None
    signature: str = None


# The entities, in the order SPEC.md section 4 lists them, so tests and
# later rounds can iterate over the model.
ENTITIES = (
    Organisation, System, TaxonomyLine, LibraryLine, RegisterLine, Assessment,
    Control, Indicator, UseCase, Workshop, Interaction, BowTie, Trigger,
    CycleRun, Contract, Document, Event, DataPack,
)
