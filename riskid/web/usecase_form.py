"""The Use-case form: template B.2 as fields, with the checks that return a submission.

Five header lines and eleven fields, in the book's order, with the MOD-05
example of B.2 as each field's placeholder (SPEC.md 6.5). A submission is
returned for the three failing fields of SPEC.md 5.5, checked by
:func:`riskid.rules.check_use_case`, and for an incomplete template: no
taxonomy node, no definition, no named owner, no data quality rating, or a
control row that cannot be read (chapter 7: the AI officer sends back a
submission that classifies in its own categories).
"""

from __future__ import annotations

from datetime import date

from riskid import rules
from riskid.rules import LIFECYCLE_STAGES
from riskid.web.system_form import ROLES

TEMPLATE_SOURCE = "General template (B.2)"
# Chapter 7, the ten specialist sub-processes: each risk records where it came from.
SUB_PROCESSES = (
    "Data protection (DPIA)", "Security (OWASP)", "Fairness testing", "Model validation",
    "Third-party due diligence", "Content and intellectual property",
    "Safety for physical systems", "Accessibility", "Environmental", "Human factors",
)
SOURCES = (TEMPLATE_SOURCE,) + SUB_PROCESSES

DATA_QUALITY = ("High", "Medium", "Low", "Very Low")
CONTROL_TYPES = ("preventive", "detective", "corrective")
CONTROL_ROWS = 4

# (name, label, record, note) for the five header lines of B.2.
HEADERS = (
    ("system_and_version", "1. System and version",
     "The system, the model version, the application version and the date of the last change",
     "The assessment applies to this version only"),
    ("role", "2. Role", "Provider, deployer or both, for this use case",
     "Decides which obligations of the Act apply"),
    ("lifecycle_stage", "3. Lifecycle stage", "One of the seven stages", "Controls and evidence differ by stage"),
    ("purpose_and_users", "4. Intended purpose and users",
     "The purpose as the provider states it, the purpose in use, who operates the system and who "
     "relies on its output", "Compare the two purposes (HUM-03)"),
    ("persons_affected", "5. Persons affected", "Who the output affects, and whether they know",
     "Feeds harm to individuals and Article 27(1)(c)"),
)

# (number, name, label, what to write, MOD-05 example) for the eleven fields of B.2.
FIELDS = (
    (1, "risk_id", "Risk ID", "A unique ID from the central function; keep the register ID where "
     "you adopt a line. Leave it empty for a new line, which gets an ORG number.", "MOD-05"),
    (2, "taxonomy", "Taxonomy classification", "Level 1 and Level 2 code", "MOD, 2.3"),
    (3, "definition", "Risk definition", "What could happen, in plain words, not the category",
     "The supplier replaces the model behind the interface without notice and our thresholds stop holding"),
    (4, "drivers_direct", "Underlying drivers, direct", "What directly causes or triggers the risk",
     "The contract allows changes without notice; the version is not pinned"),
    (5, "drivers_indirect", "Underlying drivers, indirect", "What amplifies or enables it",
     "One supplier; no regression suite; nobody reads supplier notices"),
    (6, "metrics", "Quantitative metrics", "Measured values and limits, with the date and the sample",
     "Version changes per quarter; regression pass rate per version"),
    (7, "qualitative", "Qualitative information",
     "Narrative where numbers do not exist, with the source of each statement",
     "Overseers report that the style of answers has changed"),
    (8, "controls", "Current controls (type and effectiveness)",
     "Each control, its type (preventive, detective or corrective), its last test date and its evidence",
     "Version pinning (preventive), tested at the last release; weekly regression run (detective)"),
    (9, "owner", "Risk owner", "One named person", "Name and role, not a team"),
    (10, "indicators", "Emerging risk indicators", "Early signals that the risk is rising",
     "A supplier deprecation notice; a change in the refusal rate"),
    (11, "data_quality", "Data quality rating", "High, Medium, Low or Very Low, with the basis stated",
     "Medium: our own regression results exist, the supplier's change history does not"),
)
_TEXT_FIELDS = ("risk_id", "taxonomy", "definition", "drivers_direct", "drivers_indirect", "metrics",
                "qualitative", "owner", "indicators", "data_quality", "data_quality_basis")
CONTROL_EXAMPLES = (("Version pinning", "preventive", "tested at the last release"),
                    ("Weekly regression run", "detective", ""))


def header_defaults(system: dict) -> dict:
    """Header lines 1 to 5 pre-filled from the system's inventory entry (B.1)."""
    version = " ".join(p for p in (system.get("model_name"), system.get("model_version")) if p)
    notice = system.get("last_change_notice")
    first = ", ".join(p for p in (system.get("name"), f"model {version}" if version else "",
                                  f"last change notice {notice}" if notice else "") if p)
    purposes = [f"Stated: {system['purpose_stated']}" if system.get("purpose_stated") else "",
                f"In use: {system['purpose_in_use']}" if system.get("purpose_in_use") else "",
                "Users: " + ", ".join(u["role"] for u in system.get("users") or []) if system.get("users") else ""]
    persons = ", ".join(p["group"] + (" (vulnerable)" if p.get("vulnerable") else "")
                        for p in system.get("persons_affected") or [])
    return {"system_and_version": first, "role": system.get("role_under_act") or "",
            "lifecycle_stage": system.get("lifecycle_stage") or "",
            "purpose_and_users": "; ".join(p for p in purposes if p), "persons_affected": persons}


def parse_usecase(form, taxonomy: dict, known_lines: dict) -> tuple[dict, list[str]]:
    """Read a B.2 submission; return ``(record, reasons)``. No reasons means accepted.

    ``taxonomy`` maps each Level 2 code to its Level 1 code; ``known_lines`` maps
    the IDs of library and register lines to their Level 2 code.
    """
    get = lambda name: str(form.get(name, "") or "").strip()  # noqa: E731
    headers = {name: get(f"header_{name}") for name, *_ in HEADERS}
    fields = {name: get(name) for name in _TEXT_FIELDS}
    source = get("source") or TEMPLATE_SOURCE
    reasons = []
    if headers["role"] and headers["role"] not in ROLES:
        reasons.append("Header 2, Role: choose provider, deployer or both.")
    if headers["lifecycle_stage"] and headers["lifecycle_stage"] not in LIFECYCLE_STAGES:
        reasons.append("Header 3, Lifecycle stage: choose one of the seven stages.")
    risk_id = fields["risk_id"]
    if risk_id and risk_id not in known_lines:
        reasons.append("Risk ID: use a library or register ID, or leave it empty for a new ORG line "
                       "(B.2 field 1).")
    elif risk_id:
        filed = known_lines[risk_id]
        if not fields["taxonomy"]:
            fields["taxonomy"] = filed
        elif fields["taxonomy"] != filed:
            reasons.append(f"Taxonomy classification: {risk_id} is filed under {filed} (B.2 field 2).")
    if fields["taxonomy"] not in taxonomy:
        reasons.append("Taxonomy classification: choose the Level 2 code (B.2 field 2).")
    if not fields["definition"]:
        reasons.append("Risk definition: say what could happen, in plain words (B.2 field 3).")
    if not fields["owner"]:
        reasons.append("Risk owner: name one person (B.2 field 9).")
    if fields["data_quality"] not in DATA_QUALITY:
        reasons.append("Data quality rating: choose High, Medium, Low or Very Low (B.2 field 11).")
    if source not in SOURCES:
        reasons.append("Source: choose the general template or one of the ten sub-processes.")
    controls = []
    for i in range(1, CONTROL_ROWS + 1):
        row = {key: get(f"control_{i}_{key}") for key in ("name", "type", "test_date", "evidence")}
        if not any(row.values()):
            continue
        if not row["name"]:
            reasons.append(f"Control {i}: name the control.")
        if row["type"] and row["type"] not in CONTROL_TYPES:
            reasons.append(f"Control {i}: the type is preventive, detective or corrective.")
        if row["test_date"]:
            try:
                row["test_date"] = date.fromisoformat(row["test_date"]).isoformat()
            except ValueError:
                reasons.append(f"Control {i}: give the last test date as YYYY-MM-DD.")
        controls.append(row)
    fields["controls"] = controls
    reasons += rules.check_use_case({
        "drivers": fields["drivers_direct"], "controls": controls,
        "data_quality": fields["data_quality"], "data_quality_basis": fields["data_quality_basis"]})
    return {"headers": headers, "fields_": fields, "source": source}, reasons


def form_values(record: dict) -> dict:
    """A stored submission as form values, so a returned one can be corrected."""
    values = {f"header_{k}": v for k, v in (record.get("headers") or {}).items()}
    fields = dict(record.get("fields_") or {})
    for i, row in enumerate(fields.pop("controls", None) or [], start=1):
        values.update({f"control_{i}_{k}": v or "" for k, v in row.items()})
    values.update({k: v or "" for k, v in fields.items()})
    values["source"] = record.get("source") or TEMPLATE_SOURCE
    return values
