"""The assessment record (chapter 9; template B.6; SPEC.md 5.1 to 5.4).

:func:`parse_assessment` reads the scores, computes what `riskid.rules`
computes (dominant dimension, inherent score and band, materiality and the
rule that made it, residual), and returns the reasons for refusing the record:
a score outside 1 to 5, the dominant-dimension reasoning missing when harm to
individuals scores 4 or 5 and is not dominant, data quality without its
evidence, a residual lowered before a control has a test date and a result
or without citing that test, a residual above the inherent, an acceptance
without the person who accepts.
"""

from __future__ import annotations

import re
from datetime import date

from riskid import importers, rules
from riskid.model import Assessment
from riskid.reconcile import DIMENSIONS

WHOLE_NUMBER = re.compile(r"[0-9]+")      # ASCII digits only; str.isdigit() also takes "²"

SCALES = importers.load_scales()
DATA_QUALITY = tuple(level["rating"] for level in SCALES["data_quality"]["levels"])
DIMS = rules.DIM_ORDER


def _score(form, name, label, reasons):
    raw = str(form.get(name, "") or "").strip()
    if WHOLE_NUMBER.fullmatch(raw) and 1 <= int(raw) <= 5:
        return int(raw)
    reasons.append(f"{label}: choose 1 to 5.")
    return 0


def _material_rule(inherent, impact, flags) -> str:
    """Every rule that makes the line material, joined; or why it is not."""
    found = [text for test, text in (
        (inherent >= 15, "inherent 15 or more"), (impact == 5, "impact 5"),
        (bool(flags.get("material_on_impact_alone")), flags.get("material_on_impact_alone")),
        (bool(flags.get("prohibited_practice")), "prohibited practice (Article 5)")) if test]
    return "; ".join(found) or "not material: inherent under 15 and impact under 5"


def parse_assessment(form, line_id: str, controls: list, flags: dict, system: dict):
    """Return ``(Assessment, reasons, disagreement or None)`` for one line's scores."""
    reasons: list = []
    impacts = {d: _score(form, f"impact_{d}", f"Impact, {SCALES[d]['name']}", reasons) for d in DIMS}
    likelihood = _score(form, "likelihood", "Likelihood", reasons)
    vulnerability = _score(form, "vulnerability", "Vulnerability", reasons)
    speed = _score(form, "speed", "Speed of onset", reasons)
    text = {k: str(form.get(k, "") or "").strip() for k in (
        "harm_scored", "unit_of_exposure", "dominant_reasoning", "data_quality", "data_quality_basis",
        "acceptable", "acceptable_by", "model_vendor_dependency", "minority_holder", "minority_score",
        "minority_dimension", "minority_evidence", "residual_L", "residual_I")}
    dim, impact = rules.dominant(impacts)
    if not reasons and rules.needs_reasoning(impacts) and not text["dominant_reasoning"]:
        reasons.append(f"Harm to individuals scores {impacts['IND']} but {dim} is dominant: give the "
                       "reasoning (chapter 9; SPEC 5.2).")
    if text["data_quality"] not in DATA_QUALITY:
        reasons.append("Data quality: choose High, Medium, Low or Very Low.")
    if not text["data_quality_basis"]:
        reasons.append("Data quality: state the evidence behind the rating (B.6 field 4).")
    residual_l, residual_i = likelihood, impact
    for key, label in (("residual_L", "Residual likelihood"), ("residual_I", "Residual impact")):
        if text[key]:
            value = _score(form, key, label, reasons)
            residual_l, residual_i = (value, residual_i) if key == "residual_L" else (residual_l, value)
    lowered = (residual_l, residual_i) != (likelihood, impact)
    if residual_l > likelihood or residual_i > impact:
        reasons.append("Residual: it cannot be above the inherent likelihood or impact.")
    elif lowered and not rules.residual_allowed(controls):
        reasons.append("Residual: locked at the inherent likelihood and impact until a control on the "
                       "line has a test date and a result (SPEC 5.4).")
    elif lowered and not rules.residual_basis_cites_test(text["data_quality_basis"], controls):
        reasons.append("Data quality basis: cite the control test that supports the lower residual "
                       "(SPEC 5.4).")
    if text["acceptable"] not in ("", "yes", "no"):
        reasons.append("Acceptable: yes or no.")
    if text["acceptable"] == "yes" and not text["acceptable_by"]:
        reasons.append("Acceptable: say by whom the residual risk is accepted (Article 9(5); clause 6.1.3).")
    disagreement = None
    if text["minority_score"] or text["minority_holder"]:
        minority = _score(form, "minority_score", "Disagreement, the minority score", reasons)
        if text["minority_dimension"] not in DIMENSIONS:
            reasons.append("Disagreement: choose the dimension the views differ on.")
        if not text["minority_holder"]:
            reasons.append("Disagreement: name who holds the minority view.")
        majority = {"likelihood": likelihood, **impacts}.get(text["minority_dimension"])
        disagreement = {"holder": text["minority_holder"], "minority_score": minority,
                        "majority_score": majority, "dimension": text["minority_dimension"],
                        "evidence": text["minority_evidence"] or None}
    line_flags = {}
    if line_id in flags.get("material_on_impact_alone", []):
        line_flags["material_on_impact_alone"] = f"{line_id}: material on impact alone"
    if (system or {}).get("article_6_outcome") == "prohibited":
        line_flags["prohibited_practice"] = True
    inherent = rules.score(likelihood, impact)
    assessment = Assessment(
        line_id=line_id, date=date.today().isoformat(), harm_scored=text["harm_scored"] or None,
        unit_of_exposure=text["unit_of_exposure"] or None, impact=impacts, dominant_dimension=dim,
        dominant_reasoning=text["dominant_reasoning"] or None, likelihood=likelihood,
        vulnerability=vulnerability, speed=speed, inherent=inherent,
        inherent_band=rules.band(inherent) if inherent else None,
        material=rules.material(inherent, impact, line_flags),
        material_rule=_material_rule(inherent, impact, line_flags),
        data_quality=text["data_quality"] or None, data_quality_basis=text["data_quality_basis"] or None,
        residual_L=residual_l, residual_I=residual_i, residual=rules.score(residual_l, residual_i),
        acceptable=text["acceptable"] or None, acceptable_by=text["acceptable_by"] or None,
        model_vendor_dependency=text["model_vendor_dependency"] or None,
        disagreement=disagreement or {})
    return assessment, reasons, disagreement


def escalates(assessment: dict) -> bool:
    """Chapter 9: a speed of 5 or a vulnerability of 5 puts a line in front of the owner this week."""
    return assessment.get("speed") == 5 or assessment.get("vulnerability") == 5
