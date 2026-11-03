"""The method's rules, one function each (PLAN.md section 4, round 2).

This module implements `SPEC.md` section 5 and nothing else: the scoring,
banding, materiality, residual lock, the three failing use-case fields,
review dates, version and pilot checks, and AI-draft data quality. Each rule
is a single function with a positive and a negative test in ``tests`` (rule 6
of `PLAN.md` section 1); none special-cases a test to make it pass.

The scoring, banding and score-derived materiality here reproduce the book's
reference implementation exactly; ``tests/test_rules_golden.py`` recomputes
all 91 library lines and must match the committed golden file 91/91.
"""

import re

# The five consequence dimensions, in the order SPEC.md section 4 lists them.
# Ties for the dominant dimension are broken by this order (the first listed
# dimension that reaches the maximum is named), so the result is deterministic.
DIM_ORDER = ("FIN", "REG", "REP", "IND", "OPS")

# Stock driver phrases that a B.2 submission must not use (SPEC.md 5.5).
STOCK_DRIVER_PHRASES = ("model error", "AI risk", "the model is wrong")

# Control names that, when present, must carry an override figure in their
# evidence (SPEC.md 5.5, "human in the loop" / "human oversight").
_HUMAN_CONTROL_NAMES = ("human in the loop", "human oversight")

# Flag names a library line may carry for the materiality rules above the
# score (SPEC.md 5.3).
_FLAG_MATERIAL_ON_IMPACT_ALONE = "material_on_impact_alone"
_FLAG_PROHIBITED_PRACTICE = "prohibited_practice"


def _field(obj, name, default=None):
    """Read ``name`` from a dict or an object (e.g. a dataclass)."""
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _flag_on(flags, name):
    """True if the flag ``name`` is set; ``flags`` is a mapping or a set."""
    if not flags:
        return False
    if isinstance(flags, dict):
        return bool(flags.get(name))
    return name in flags


def _later(left, right):
    """True if ``left`` is a later date than ``right`` (ISO strings or dates)."""
    if left is None or right is None:
        return False
    if isinstance(left, str) and isinstance(right, str):
        return left > right
    return left > right


def score(L, I):
    """Inherent score: likelihood times impact (SPEC.md 5.1)."""
    return L * I


def band(score_value):
    """Name the band for an L x I score (SPEC.md 5.1).

    1-4 Low, 5-9 Moderate, 10-14 High, 15 and above Critical.
    """
    if score_value <= 4:
        return "Low"
    if score_value <= 9:
        return "Moderate"
    if score_value <= 14:
        return "High"
    return "Critical"


def dominant(impacts):
    """Return ``(dim, value)`` for the dominant dimension (SPEC.md 5.2).

    ``impacts`` maps the five dimensions to a 1-5 value. The dimension with
    the highest value is dominant; ties are broken by :data:`DIM_ORDER`, so
    the result is deterministic. An empty or all-zero mapping yields
    ``(None, 0)``.
    """
    best_dim, best_value = None, 0
    for dim in DIM_ORDER:
        value = impacts.get(dim, 0) if isinstance(impacts, dict) else 0
        if value > best_value:
            best_dim, best_value = dim, value
    return best_dim, best_value


def needs_reasoning(impacts):
    """True when the assessor must explain the dominant dimension (5.2).

    Harm to individuals (IND) scoring 4 or 5 that is *not* the dominant
    dimension forces a written reason; an IND score below 4, or one that is
    dominant, does not.
    """
    dim, _ = dominant(impacts)
    ind = impacts.get("IND", 0) if isinstance(impacts, dict) else 0
    return ind in (4, 5) and dim != "IND"


def material(inherent, I, flags=None):
    """Whether a line is material (SPEC.md 5.3).

    A line is material when its inherent score is 15 or more or its impact is
    5. The rules above the score also make a line material when it carries
    the ``material_on_impact_alone`` flag (the library's LEG-08) or when it
    is a prohibited practice (Article 5); those are read from ``flags``.
    """
    if inherent >= 15:
        return True
    if I == 5:
        return True
    if _flag_on(flags, _FLAG_MATERIAL_ON_IMPACT_ALONE):
        return True
    if _flag_on(flags, _FLAG_PROHIBITED_PRACTICE):
        return True
    return False


def residual_allowed(line_controls):
    """Whether the residual picker may be lowered (SPEC.md 5.4).

    ``rL`` and ``rI`` stay locked at ``L`` and ``I`` until at least one
    control on the line has both a test date and a test result; only then can
    a lower residual be entered. ``line_controls`` is a list of control
    records (dicts or :class:`~riskid.model.Control`).
    """
    for control in line_controls or []:
        has_date = bool(_field(control, "last_test_date"))
        has_result = bool(_field(control, "last_test_result"))
        if has_date and has_result:
            return True
    return False


def check_use_case(fields):
    """Return the reasons a B.2 use-case submission is sent back (5.5).

    An empty list means the submission is accepted. ``fields`` is a mapping
    with the B.2 fields the three checks read:

    - ``drivers``: the driver text; empty or a stock phrase is returned.
    - ``controls``: a list of ``{"name": ..., "evidence": ...}``; a control
      named "human in the loop" or "human oversight" must carry an override
      figure (a number) in its evidence.
    - ``data_quality`` / ``data_quality_basis``: a Medium rating needs a basis.

    Each of the three failing-field checks adds its own reason, so a
    submission can be returned for more than one of them at once.
    """
    reasons = []

    drivers = (fields.get("drivers") or "").strip()
    if not drivers or drivers.lower() in STOCK_DRIVER_PHRASES:
        reasons.append(
            "the driver is empty or a stock phrase; name the specific driver"
        )

    for control in fields.get("controls") or []:
        name = (control.get("name") or "").lower()
        if any(n in name for n in _HUMAN_CONTROL_NAMES):
            evidence = control.get("evidence") or ""
            if not re.search(r"\d", evidence):
                reasons.append(
                    "the "
                    f"{control.get('name')!r} control has no override figure "
                    "in its evidence"
                )

    data_quality = fields.get("data_quality")
    if data_quality == "Medium" and not fields.get("data_quality_basis"):
        reasons.append(
            "a Medium data-quality rating needs its basis stated"
        )

    return reasons


def next_review(cycle_date, trigger_date):
    """The next review date (SPEC.md 5.7).

    The earlier of the calendar date set by the review cycle and the next
    trigger date. Either may be absent (``None``); the earlier of the two
    present dates wins, and ``None`` is returned when neither is present.
    ISO dates and date objects are both accepted.
    """
    candidates = [d for d in (cycle_date, trigger_date) if d is not None]
    if not candidates:
        return None
    return min(candidates)


def version_mismatch(system):
    """Whether a system's running version differs from its assessed version.

    The dashboard and B.8 step 4 flag a material system when the version it
    is running differs from the version it was last risk-assessed at
    (SPEC.md 5.8). This detects the difference itself; the caller applies it
    to the material systems.
    """
    assessed = _field(system, "last_risk_assessment") or {}
    assessed_version = _field(assessed, "version")
    running_version = _field(system, "model_version")
    if assessed_version is None or running_version is None:
        return False
    return running_version != assessed_version


def pilot_overdue(system, today):
    """Whether a system is past its pilot end date with no gate record.

    A system past its pilot end date without a deployment-gate record is
    flagged (OPS-08, SPEC.md 5.10). A deployment-gate record is taken to be
    a dated last risk assessment; systems that never ran a pilot (no end
    date) are not overdue. ``pilot_end_date`` and ``today`` are ISO dates or
    date objects.
    """
    end = _field(system, "pilot_end_date")
    if end is None:
        return False
    gate = _field(system, "last_risk_assessment") or {}
    if _field(gate, "date"):
        return False
    return _later(today, end)


def ai_draft_quality(field):
    """The data-quality rating that counts for an assistant-drafted field.

    An unaccepted AI draft counts as Very Low data quality (chapter 14,
    SPEC.md 5.9) even though the field may carry a higher rating; once a
    person accepts it, the field's own ``data_quality`` counts. ``field`` is
    a mapping with optional ``ai_draft``, ``data_quality`` and ``accepted``.
    """
    ai_draft = field.get("ai_draft") if isinstance(field, dict) else None
    accepted = field.get("accepted") if isinstance(field, dict) else False
    if ai_draft and not accepted:
        return "Very Low"
    if isinstance(field, dict):
        return field.get("data_quality")
    return None
