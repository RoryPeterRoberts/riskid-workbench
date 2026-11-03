"""The Inventory form: template B.1 as fields, with parsing and the save checks.

The form is the template (SPEC.md section 1): its 18 rows are B.1's rows in
order, each with the book's "what to record" and "why it is there" text, and
its fields are the System fields of SPEC.md section 4. A save is refused
without a name, an owner, a role under the Act and an Article 6 outcome (the
Day-one journey, SPEC.md section 3); the reasons are returned to the form.

Form field names are the System field names; the parts of a structured field
use dotted names (``data.personal``, ``impact_assessments.DPIA.ref``).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

from riskid.rules import LIFECYCLE_STAGES

ROLES = ("provider", "deployer", "both")
VENDOR_OR_BUILT = ("built", "bought", "bought and configured")
DISCOVERY_SOURCES = ("declared", "procurement", "scan", "audit", "incident")

# The Article 6 outcomes, one per end of chapter 5's classification steps.
ARTICLE_6_OUTCOMES = (
    ("out of scope", "Not an AI system under Article 3(1)"),
    ("prohibited", "Prohibited practice under Article 5"),
    ("high-risk: Annex I", "High-risk: product or safety component under Annex I (Article 6(1))"),
    ("high-risk: Annex III", "High-risk: Annex III use case (Article 6(2))"),
    ("not high-risk: Article 6(3)", "Not high-risk: an Article 6(3) condition applies"),
    ("no further class", "No further class beyond Article 4 AI literacy"),
)

# A whole number in ASCII digits; str.isdigit() also accepts "²", which int() refuses.
WHOLE_NUMBER = re.compile(r"[0-9]+")

REASON_NAME = "System: give the system a name (B.1 field 1)."
REASON_OWNER = "Owner: name the one person accountable for this system (B.1 field 10)."
REASON_ROLE = "Role under the Act: choose provider, deployer or both (B.1 field 8)."
REASON_CLASS = "Classification: choose the Article 6 outcome (B.1 field 9)."

_ASSESSMENTS = (("DPIA", "DPIA"), ("FRIA", "Fundamental rights impact assessment"),
                ("42005", "ISO/IEC 42005-style assessment"))


@dataclass(frozen=True)
class Field:
    name: str                 # form name; dotted for a part of a structured field
    label: str
    kind: str                 # text | textarea | select | date | yesno | lines | users | persons | csv
    choices: tuple = ()       # (value, label) pairs for a select
    help: str = ""


@dataclass(frozen=True)
class Row:
    number: int
    title: str
    record: str               # B.1 "What to record"
    why: str                  # B.1 "Why it is there"
    fields: tuple


def _pairs(values):
    return tuple((v, v) for v in values)


B1_ROWS = (
    Row(1, "System", "Name, business function and components; a unique, persistent system ID",
        "Lists each system once; the ID links to the register, the impact assessments and the logs",
        (Field("name", "Name", "text"), Field("function", "Business function", "text"),
         Field("components", "Components", "lines", help="One per line."))),
    Row(2, "Vendor or built", "Built, bought, or bought and configured; supplier and contract; "
        "any model provider behind the product",
        "Who holds the documentation (Articles 13, 25(4)); DAT-04, TRA-04",
        (Field("vendor_or_built", "Built or bought", "select", _pairs(VENDOR_OR_BUILT)),
         Field("supplier", "Supplier", "text"), Field("contract_ref", "Contract reference", "text"),
         Field("model_provider", "Model provider behind the product", "text"))),
    Row(3, "Model and version", "Model name, version identifier, date of the last change notice, "
        "whether the version can be pinned", "MOD-05, OPS-05",
        (Field("model_name", "Model name", "text"), Field("model_version", "Version identifier", "text"),
         Field("last_change_notice", "Last change notice", "date"),
         Field("version_pinned", "Version can be pinned", "yesno"))),
    Row(4, "Purpose", "The intended purpose as the provider states it, and the purpose in use",
        "HUM-03; A.9.4",
        (Field("purpose_stated", "Intended purpose, as the provider states it", "textarea"),
         Field("purpose_in_use", "Purpose in use", "textarea"))),
    Row(5, "Users", "Who operates the system or acts on its output, by role and number",
        "Articles 4, 26(2); HUM-05",
        (Field("users", "Users", "users", help="One per line, as role, number."),)),
    Row(6, "Persons affected", "People whose money, access, rights or health the output affects, "
        "including those unaware of the system; children and vulnerable groups flagged",
        "Article 27(1)(c); ISO/IEC 42005, section 6.7",
        (Field("persons_affected", "Groups affected", "persons",
               help="One group per line; end a line with \", vulnerable\" to flag it."),)),
    Row(7, "Data", "Training sources if built; production inputs; personal and special-category "
        "data; where data is sent and kept", "A.4, A.7; Articles 10, 26(4)",
        (Field("data.training_sources", "Training sources, if built", "textarea"),
         Field("data.production_inputs", "Production inputs", "textarea"),
         Field("data.personal", "Personal data", "yesno"),
         Field("data.special_category", "Special-category data", "yesno"),
         Field("data.locations", "Where data is sent and kept", "text"))),
    Row(8, "Role under the Act", "Provider, deployer or both; the ISO/IEC 42001 role; "
        "the Article 25 check", "Articles 3, 25; LEG-07",
        (Field("role_under_act", "Role under the Act", "select", _pairs(ROLES)),
         Field("article_25_check", "Article 25 check", "textarea"))),
    Row(9, "Classification", "The Article 6 outcome and a reference to the record, with the "
        "Article 5 screen and any Article 50 duty", "Articles 5, 6, 49; LEG-07, LEG-08",
        (Field("article_6_outcome", "Article 6 outcome", "select", ARTICLE_6_OUTCOMES),
         Field("article_6_record_ref", "Reference to the classification record", "text"),
         Field("article_5_screen", "Article 5 screen: result, date, signatory", "textarea"),
         Field("article_50_duty", "Article 50 duty, and how it is met", "text"))),
    Row(10, "Owner", "One named person accountable, with the model owner and data owner",
        "A.3.2; TRA-05",
        (Field("owner", "Owner (one named person)", "text"),
         Field("model_owner", "Model owner", "text"), Field("data_owner", "Data owner", "text"))),
    Row(11, "Stage", "One of the seven lifecycle stages", "OPS-08",
        (Field("lifecycle_stage", "Lifecycle stage", "select", _pairs(LIFECYCLE_STAGES)),)),
    Row(12, "Jurisdictions", "Where it is used and where the affected persons are",
        "Regulatory hooks (Chapter 15)",
        (Field("jurisdictions", "Jurisdictions", "csv", help="Separate with commas."),)),
    Row(13, "Period and frequency of use", "How long and how often it is used", "Article 27(1)(b)",
        (Field("period_and_frequency", "Period and frequency of use", "text"),)),
    Row(14, "Impact assessments", "DPIA, fundamental rights impact assessment and ISO/IEC "
        "42005-style assessment: reference, date, next due", "A.5; Articles 26(9), 27",
        tuple(f for key, label in _ASSESSMENTS for f in (
            Field(f"impact_assessments.{key}.ref", f"{label}: reference", "text"),
            Field(f"impact_assessments.{key}.date", f"{label}: date", "date"),
            Field(f"impact_assessments.{key}.next_due", f"{label}: next due", "date")))),
    Row(15, "Last risk assessment", "The date, and the version assessed",
        "The quarterly version check (Chapter 13)",
        (Field("last_risk_assessment.date", "Date of the last risk assessment", "date"),
         Field("last_risk_assessment.version", "Version assessed", "text"))),
    Row(16, "Discovery source", "Declared, procurement, scan, audit or incident",
        "Measures shadow AI (OPS-07)",
        (Field("discovery_source", "Discovery source", "select", _pairs(DISCOVERY_SOURCES)),)),
    Row(17, "Pilot end date", "The date by which the pilot closes or goes through the deployment gate",
        "OPS-08; A.6.2.5", (Field("pilot_end_date", "Pilot end date", "date"),)),
    Row(18, "Logs", "Where they are kept and for how long", "Articles 12, 26(6); A.6.2.8; TRA-07",
        (Field("logs.location", "Where the logs are kept", "text"),
         Field("logs.retention", "How long they are kept", "text"))),
)

FIELDS = tuple(f for row in B1_ROWS for f in row.fields)

# The four fields a save needs, with the reason returned when one is missing.
_REQUIRED = {"name": REASON_NAME, "owner": REASON_OWNER,
             "role_under_act": REASON_ROLE, "article_6_outcome": REASON_CLASS}
REQUIRED_FIELDS = tuple(_REQUIRED)


def _parse_one(f: Field, raw: str):
    """Parse one form value; return (value, reason or None). Empty means not set."""
    text = (raw or "").strip()
    if f.kind in ("text", "textarea"):
        return (text or None), None
    if f.kind == "select":
        if not text:
            return None, None
        if text in {value for value, _ in f.choices}:
            return text, None
        return None, _REQUIRED.get(f.name, f"{f.label}: choose one of the listed options.")
    if f.kind == "date":
        if not text:
            return None, None
        try:
            return date.fromisoformat(text).isoformat(), None
        except ValueError:
            return None, f"{f.label}: use a date in the form YYYY-MM-DD."
    if f.kind == "yesno":
        if text in ("yes", "no"):
            return text == "yes", None
        return None, (None if not text else f"{f.label}: choose yes or no.")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if f.kind == "lines":
        return lines, None
    if f.kind == "csv":
        return [part.strip() for part in text.split(",") if part.strip()], None
    if f.kind == "persons":
        out = []
        for line in lines:
            group, _, flag = line.rpartition(",")
            if group and flag.strip().lower() == "vulnerable":
                out.append({"group": group.strip(), "vulnerable": True})
            else:
                out.append({"group": line, "vulnerable": False})
        return out, None
    if f.kind == "users":
        out = []
        for line in lines:
            role, sep, number = line.rpartition(",")
            if not sep:
                out.append({"role": line, "number": None})
            elif role.strip() and WHOLE_NUMBER.fullmatch(number.strip()):
                out.append({"role": role.strip(), "number": int(number)})
            else:
                return None, "Users: give each line as role, number (for example: credit analyst, 12)."
        return out, None
    raise ValueError(f"unknown field kind {f.kind!r}")


def _set(target: dict, dotted: str, value) -> None:
    head, _, rest = dotted.partition(".")
    if not rest:
        target[head] = value
    else:
        _set(target.setdefault(head, {}), rest, value)


def parse_system_form(form) -> tuple[dict, list[str]]:
    """Turn submitted B.1 values into System fields, with the reasons for any refusal.

    ``form`` maps form names to strings. Unset parts of a structured field are
    left out of it, so an unrecorded DPIA reference is absent rather than empty.
    """
    system: dict = {}
    reasons: list[str] = []
    for f in FIELDS:
        value, reason = _parse_one(f, form.get(f.name, ""))
        if reason and reason not in reasons:
            reasons.append(reason)
        if "." in f.name:
            if value not in (None, [], ""):
                _set(system, f.name, value)
        else:
            system[f.name] = value
    for name, reason in _REQUIRED.items():
        if not system.get(name) and reason not in reasons:
            reasons.append(reason)
    order = list(_REQUIRED.values())
    reasons.sort(key=lambda r: order.index(r) if r in order else len(order))
    return system, reasons


def _get(source: dict, dotted: str):
    value = source
    for part in dotted.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value


def form_values(system: dict) -> dict:
    """The inverse of :func:`parse_system_form`: a stored System as form strings."""
    values = {}
    for f in FIELDS:
        value = _get(system, f.name)
        if value is None:
            values[f.name] = ""
        elif f.kind == "yesno":
            values[f.name] = "yes" if value else "no"
        elif f.kind == "lines":
            values[f.name] = "\n".join(value)
        elif f.kind == "csv":
            values[f.name] = ", ".join(value)
        elif f.kind == "persons":
            values[f.name] = "\n".join(
                p["group"] + (", vulnerable" if p.get("vulnerable") else "") for p in value)
        elif f.kind == "users":
            values[f.name] = "\n".join(
                u["role"] + ("" if u.get("number") is None else f", {u['number']}") for u in value)
        else:
            values[f.name] = str(value)
    return values
