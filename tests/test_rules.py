"""Round 2 tests (PLAN.md section 4, round 2): one function per rule.

Each rule in ``riskid/rules.py`` gets a positive and a negative test, and the
three failing-field checks from SPEC.md section 5.5 each get a returned and an
accepted example. The golden recomputation of the 91 library lines lives in
``test_rules_golden.py``.
"""

from riskid.model import System
from riskid.rules import (
    ai_draft_quality,
    band,
    check_use_case,
    dominant,
    material,
    next_review,
    needs_reasoning,
    pilot_overdue,
    residual_allowed,
    score,
    version_mismatch,
)


# --- score (SPEC.md 5.1) ---------------------------------------------------

def test_score_positive():
    assert score(3, 4) == 12
    assert score(5, 5) == 25


def test_score_negative():
    # It is the product, not a band; it does not clamp and returns an int.
    result = score(1, 1)
    assert result == 1
    assert isinstance(result, int)
    assert result != "Low"


# --- band (SPEC.md 5.1) ----------------------------------------------------

def test_band_positive():
    assert band(4) == "Low"
    assert band(9) == "Moderate"
    assert band(14) == "High"
    assert band(15) == "Critical"


def test_band_negative():
    # Boundaries and out-of-range values still name a valid band.
    assert band(5) == "Moderate"
    assert band(0) == "Low"
    assert band(26) == "Critical"


# --- dominant (SPEC.md 5.2) ------------------------------------------------

def test_dominant_positive():
    impacts = {"FIN": 5, "REG": 2, "REP": 1, "IND": 1, "OPS": 3}
    assert dominant(impacts) == ("FIN", 5)


def test_dominant_negative():
    # Ties are broken by DIM_ORDER, so FIN (listed before IND) wins; an empty
    # mapping yields (None, 0) instead of crashing.
    assert dominant({"FIN": 5, "IND": 5}) == ("FIN", 5)
    assert dominant({}) == (None, 0)


# --- needs_reasoning (SPEC.md 5.2) -----------------------------------------

def test_needs_reasoning_positive():
    # Harm to individuals is 4 but the dominant dimension is FIN, so a
    # written reason is required.
    assert needs_reasoning({"FIN": 5, "IND": 4}) is True


def test_needs_reasoning_negative():
    # Harm to individuals is the dominant dimension, so no reason is forced.
    assert needs_reasoning({"FIN": 1, "IND": 5}) is False
    # An IND score below 4 never forces reasoning even when not dominant.
    assert needs_reasoning({"FIN": 5, "IND": 3}) is False


# --- material (SPEC.md 5.3) ------------------------------------------------

def test_material_positive():
    assert material(16, 4) is True
    assert material(8, 5) is True
    assert material(2, 2, {"prohibited_practice": True}) is True


def test_material_negative():
    assert material(12, 4) is False
    assert material(14, 4, {}) is False


# --- residual_allowed (SPEC.md 5.4) ----------------------------------------

def test_residual_allowed_positive():
    controls = [
        {"last_test_date": None, "last_test_result": None},
        {"last_test_date": "2026-03-31", "last_test_result": "pass"},
    ]
    assert residual_allowed(controls) is True


def test_residual_allowed_negative():
    # A control with only a date, or only a result, does not unlock the
    # residual picker; neither does an empty list.
    assert residual_allowed([{"last_test_date": "2026-03-31",
                              "last_test_result": None}]) is False
    assert residual_allowed([]) is False


# --- check_use_case (SPEC.md 5.5) -----------------------------------------

def test_check_use_case_positive():
    # A complete submission is accepted: no reasons returned.
    fields = {
        "drivers": "a vendor pushed an unvalidated model update",
        "controls": [
            {"name": "Human oversight", "evidence": "override rate 3.2% in Q1"},
        ],
        "data_quality": "High",
    }
    assert check_use_case(fields) == []


def test_check_use_case_negative():
    # An empty driver is sent back.
    assert check_use_case({"drivers": ""})


# Three failing-field checks, each with a returned and an accepted example.

def test_check_use_case_driver_returned_and_accepted():
    # Returned: each of the three stock phrases, in at least two casings,
    # is sent back (case-insensitive match).
    returned_casings = (
        "model error", "Model Error",
        "AI risk", "ai risk",
        "the model is wrong", "THE MODEL IS WRONG",
    )
    for drivers in returned_casings:
        reasons = check_use_case({"drivers": drivers})
        assert any("driver" in reason for reason in reasons), drivers
    # Accepted: a concrete driver clears that check.
    accepted = check_use_case({"drivers": "a vendor pushed an unvalidated update"})
    assert not any("driver" in reason for reason in accepted)


def test_check_use_case_human_control_returned_and_accepted():
    base = {"drivers": "a vendor pushed an unvalidated model update",
            "data_quality": "High"}
    # Returned: a "human in the loop" control with no override figure.
    returned = check_use_case({**base, "controls": [
        {"name": "Human in the loop", "evidence": "weekly spot checks"}]})
    assert any("override figure" in reason for reason in returned)
    # Accepted: the same control carrying a figure clears that check.
    accepted = check_use_case({**base, "controls": [
        {"name": "Human oversight", "evidence": "override rate 4.1% in Q2"}]})
    assert not any("override figure" in reason for reason in accepted)


def test_check_use_case_data_quality_returned_and_accepted():
    base = {"drivers": "a vendor pushed an unvalidated model update"}
    # Returned: a Medium data-quality rating without a basis.
    returned = check_use_case({**base, "data_quality": "Medium"})
    assert any("basis" in reason for reason in returned)
    # Accepted: the same Medium rating with a stated basis clears the check.
    accepted = check_use_case(
        {**base, "data_quality": "Medium",
         "data_quality_basis": "structured judgement over 200 samples"})
    assert not any("basis" in reason for reason in accepted)


# --- next_review (SPEC.md 5.7) --------------------------------------------

def test_next_review_positive():
    # The earlier of the cycle review date and the next trigger date wins.
    assert next_review("2026-09-30", "2026-08-15") == "2026-08-15"


def test_next_review_negative():
    # An absent cycle date falls back to the trigger date; both absent gives
    # None rather than a crash.
    assert next_review(None, "2026-08-15") == "2026-08-15"
    assert next_review(None, None) is None


# --- version_mismatch (SPEC.md 5.8) ----------------------------------------

def test_version_mismatch_positive():
    system = System(model_version="2.1",
                    last_risk_assessment={"version": "2.0"})
    assert version_mismatch(system) is True


def test_version_mismatch_negative():
    # The running version matches the assessed version, and a missing assessed
    # version never flags a mismatch.
    assert version_mismatch(
        System(model_version="2.0",
               last_risk_assessment={"version": "2.0"})) is False
    assert version_mismatch(
        System(model_version="2.0", last_risk_assessment={})) is False


# --- pilot_overdue (SPEC.md 5.10) -----------------------------------------

def test_pilot_overdue_positive():
    # Still in verification and validation after the end date: flagged.
    assert pilot_overdue(
        System(pilot_end_date="2026-01-31",
               lifecycle_stage="verification and validation"),
        "2026-06-30") is True
    # Assessed during the pilot and still before deployment after the end
    # date: the assessment does not clear the flag.
    assert pilot_overdue(
        System(pilot_end_date="2026-01-31",
               lifecycle_stage="design and development",
               last_risk_assessment={"date": "2026-01-31"}),
        "2026-06-30") is True


def test_pilot_overdue_negative():
    # Moved to deployment: the gate decision has been made, so not flagged.
    assert pilot_overdue(
        System(pilot_end_date="2026-01-31",
               lifecycle_stage="deployment"),
        "2026-06-30") is False
    # Before the end date: not flagged.
    assert pilot_overdue(
        System(pilot_end_date="2026-09-30",
               lifecycle_stage="verification and validation"),
        "2026-06-30") is False


# --- ai_draft_quality (SPEC.md 5.9) ----------------------------------------

def test_ai_draft_quality_positive():
    # An unaccepted assistant draft counts as Very Low regardless of rating.
    field = {"ai_draft": {"model": "local", "version": "1"},
             "data_quality": "High"}
    assert ai_draft_quality(field) == "Very Low"


def test_ai_draft_quality_negative():
    # Once accepted, the field's own data quality counts; with no draft at all
    # the rating passes straight through.
    field = {"ai_draft": {"model": "local", "version": "1"},
             "accepted": True, "data_quality": "High"}
    assert ai_draft_quality(field) == "High"
    assert ai_draft_quality({"data_quality": "Medium"}) == "Medium"
