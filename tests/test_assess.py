"""Round 9: the assessment's method (PLAN.md round 9; chapter 9; B.6; SPEC.md 5.1 to 5.4).

The computed fields follow `riskid.rules`; the residual stays at the inherent
L and I until a control has a test date and a result, and a lower residual's
data-quality basis must then cite that test (SPEC.md 5.4, second half);
LEG-08 is material on impact alone from the flags pack; a prohibited system's
lines are material; vulnerability or speed of 5 escalates. The heat map
places each line in its cell and draws a PNG.
"""

from riskid import importers, rules
from riskid.assess import parse_assessment
from riskid.documents.heatmap import placements, render

TESTED = [{"name": "Override-rate monitoring", "last_test_date": "2026-10-01",
           "last_test_result": "passed: overrides 4.1% of decisions"}]
UNTESTED = [{"name": "Override-rate monitoring", "last_test_date": None, "last_test_result": None}]

FORM = {"harm_scored": "wrongful refusals of credit", "unit_of_exposure": "applications per year",
        "impact_FIN": "2", "impact_REG": "3", "impact_REP": "2", "impact_IND": "4", "impact_OPS": "1",
        "likelihood": "3", "vulnerability": "3", "speed": "2", "data_quality": "Medium",
        "data_quality_basis": "partial test results on our own applications"}


def test_residual_basis_must_cite_the_test():
    assert rules.residual_basis_cites_test("Override-rate monitoring test of 1 October", TESTED)
    assert rules.residual_basis_cites_test("re-checked 2026-10-01", TESTED)
    assert not rules.residual_basis_cites_test("our own judgement", TESTED)
    assert not rules.residual_basis_cites_test("Override-rate monitoring", UNTESTED)


def test_computed_fields_follow_the_rules():
    assessment, reasons, _ = parse_assessment(FORM, "HUM-01", TESTED, {}, {})
    assert reasons == []
    assert assessment.dominant_dimension == "IND" and assessment.inherent == rules.score(3, 4) == 12
    assert assessment.inherent_band == rules.band(12) == "High"
    assert assessment.material is rules.material(12, 4) is False
    assert (assessment.residual_L, assessment.residual_I, assessment.residual) == (3, 4, 12)


def test_reasoning_is_required_when_harm_to_individuals_is_not_dominant():
    form = dict(FORM, impact_FIN="5", impact_IND="4")
    _, reasons, _ = parse_assessment(form, "HUM-01", TESTED, {}, {})
    assert any("give the reasoning" in r for r in reasons)
    assessment, reasons, _ = parse_assessment(dict(form, dominant_reasoning="the loss is to the lender first"),
                                              "HUM-01", TESTED, {}, {})
    assert reasons == [] and assessment.dominant_dimension == "FIN"


def test_the_residual_is_locked_until_a_control_is_tested():
    lowered = dict(FORM, residual_L="2", residual_I="4")
    _, reasons, _ = parse_assessment(lowered, "HUM-01", UNTESTED, {}, {})
    assert any("locked at the inherent" in r for r in reasons)
    _, reasons, _ = parse_assessment(lowered, "HUM-01", TESTED, {}, {})
    assert any("cite the control test" in r for r in reasons)
    cited = dict(lowered, data_quality_basis="Override-rate monitoring test, 2026-10-01")
    assessment, reasons, _ = parse_assessment(cited, "HUM-01", TESTED, {}, {})
    assert reasons == [] and assessment.residual == 8
    _, reasons, _ = parse_assessment(dict(FORM, residual_L="4"), "HUM-01", TESTED, {}, {})
    assert any("cannot be above the inherent" in r for r in reasons)


def test_materiality_rules_above_the_score():
    flags = importers.load_flags()
    low = dict(FORM, impact_IND="3", likelihood="1")
    leg08, _, _ = parse_assessment(low, "LEG-08", TESTED, flags, {})
    assert leg08.material and "LEG-08" in leg08.material_rule
    hum01, _, _ = parse_assessment(low, "HUM-01", TESTED, flags, {})
    assert not hum01.material
    banned, _, _ = parse_assessment(low, "HUM-01", TESTED, flags, {"article_6_outcome": "prohibited"})
    assert banned.material and "Article 5" in banned.material_rule
    five, _, _ = parse_assessment(dict(low, impact_IND="5"), "HUM-01", TESTED, flags, {})
    assert five.material and five.material_rule == "impact 5"


def test_acceptance_names_who_and_the_disagreement_goes_to_the_log():
    _, reasons, _ = parse_assessment(dict(FORM, acceptable="yes"), "HUM-01", TESTED, {}, {})
    assert any("by whom" in r for r in reasons)
    form = dict(FORM, minority_holder="Ola, overseer", minority_score="5", minority_dimension="IND",
                minority_evidence="complaints doubled in Q3")
    assessment, reasons, disagreement = parse_assessment(form, "HUM-01", TESTED, {}, {})
    assert reasons == []
    assert disagreement == {"holder": "Ola, overseer", "minority_score": 5, "majority_score": 4,
                            "dimension": "IND", "evidence": "complaints doubled in Q3"}
    assert assessment.disagreement["minority_score"] == 5


def test_bad_scores_are_refused():
    for change in ({"impact_REG": "6"}, {"likelihood": ""}, {"speed": "²"}, {"data_quality": "Okay"},
                   {"data_quality_basis": ""}):
        _, reasons, _ = parse_assessment(dict(FORM, **change), "HUM-01", TESTED, {}, {})
        assert reasons, change


def test_heat_map_places_each_line_in_its_cell_and_draws_a_png():
    rows = [{"id": "HUM-01", "L": 3, "I": 4}, {"id": "MOD-05", "L": 4, "I": 4},
            {"id": "TRA-02", "L": 3, "I": 4}]
    cells = placements(rows, "L", "I")
    assert cells[(3, 4)] == ["HUM-01", "TRA-02"] and cells[(4, 4)] == ["MOD-05"]
    assert sum(len(v) for v in cells.values()) == 3
    png = render(rows, "L", "I", "Inherent risk")
    assert png[:8] == b"\x89PNG\r\n\x1a\n" and len(png) > 10_000
