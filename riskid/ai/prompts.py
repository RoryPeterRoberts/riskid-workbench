"""The five draft kinds of SPEC.md section 8: a JSON schema each, and the message built from one screen.

The assistant drafts and a person accepts. No schema asks for a score, a rating,
an acceptance or an owner, because the assistant may set none of them (SPEC.md
section 8; chapter 14: "It is never the owner. It is never the scorer of
record."). Each message carries only the fields given for its screen.
"""

from __future__ import annotations

import json

SYSTEM = ("You draft text for an AI risk register. A named person checks every draft against its source "
          "before it is used. Use only the facts given. Where they do not say, write \"not stated\" rather "
          "than guessing. Answer with JSON that fits the schema and nothing else.")

_TEXT = {"type": "string"}
_LINES = {"type": "array", "maxItems": 12,
          "items": {"type": "object", "properties": {"line_id": _TEXT, "why": _TEXT}, "required": ["line_id", "why"]}}

KINDS = {
    "use_case": {
        "task": ("Draft the eleven fields of the B.2 use-case template for one risk of this system, from its "
                 "header lines. Choose the taxonomy code from the list. Leave risk_id empty unless a library "
                 "ID fits exactly. Do not name an owner or rate the data quality: a person does both."),
        "schema": {"type": "object", "required": ["taxonomy", "definition", "drivers_direct", "drivers_indirect",
                                                  "metrics", "qualitative", "indicators", "controls",
                                                  "data_quality_basis"],
                   "properties": {"risk_id": _TEXT, "taxonomy": _TEXT, "definition": _TEXT,
                                  "drivers_direct": _TEXT, "drivers_indirect": _TEXT, "metrics": _TEXT,
                                  "qualitative": _TEXT, "indicators": _TEXT, "data_quality_basis": _TEXT,
                                  "controls": {"type": "array", "maxItems": 4, "items": {
                                      "type": "object", "required": ["name", "type", "evidence"],
                                      "properties": {"name": _TEXT, "evidence": _TEXT,
                                                     "type": {"type": "string",
                                                              "enum": ["preventive", "detective", "corrective"]}}}}}},
    },
    "swift_answers": {
        "task": ("Answer one SWIFT prompt for the systems described: is the risk it asks about covered by a "
                 "control the facts name, or not known? Name the control and the evidence if covered."),
        "schema": {"type": "object", "required": ["status", "control", "evidence"],
                   "properties": {"status": {"type": "string", "enum": ["covered", "not known"]},
                                  "control": _TEXT, "evidence": _TEXT}},
    },
    "library_lines": {
        "task": ("Propose the library lines that apply to this system, each with the reason in its facts. "
                 "Use only IDs from the list given."),
        "schema": {"type": "object", "required": ["lines"], "properties": {"lines": _LINES}},
    },
    "trigger_summary": {
        "task": ("Summarise the trigger in two sentences and name the live register lines it touches, each "
                 "with the reason. Use only IDs from the list given."),
        "schema": {"type": "object", "required": ["summary", "lines"], "properties": {"summary": _TEXT,
                                                                                    "lines": _LINES}},
    },
    "report_narrative": {
        "task": ("Write a short narrative for each item of the board report from its statements. Add no "
                 "number, risk or judgement that the statements do not contain."),
        "schema": {"type": "object", "required": ["sections"], "properties": {"sections": {
            "type": "array", "maxItems": 12, "items": {
                "type": "object", "required": ["item", "narrative"],
                "properties": {"item": {"type": "integer", "minimum": 1, "maximum": 12}, "narrative": _TEXT}}}}},
    },
}


def message(kind: str, fields: dict) -> str:
    """The user message for one draft: the task, then the screen's fields as JSON."""
    return f"{KINDS[kind]['task']}\n\nThe facts:\n{json.dumps(fields, indent=1, ensure_ascii=False)}"


def check(kind: str, value) -> list:
    """The ways ``value`` does not fit the kind's schema (empty when it fits)."""
    return _check(KINDS[kind]["schema"], value, "draft")


_TYPES = {"object": dict, "array": list, "string": str, "integer": int}


def _check(schema: dict, value, where: str) -> list:
    expected = _TYPES[schema["type"]]
    if not isinstance(value, expected) or (expected is int and isinstance(value, bool)):
        return [f"{where} is not a{'n' if schema['type'][0] in 'aeiou' else ''} {schema['type']}"]
    problems = []
    if "enum" in schema and value not in schema["enum"]:
        problems.append(f"{where} is not one of {', '.join(schema['enum'])}")
    if ("minimum" in schema and value < schema["minimum"]) or ("maximum" in schema and value > schema["maximum"]):
        problems.append(f"{where} is out of range")
    if expected is dict:
        problems += [f"{where} lacks {k}" for k in schema.get("required", []) if k not in value]
        for k, sub in schema.get("properties", {}).items():
            if k in value:
                problems += _check(sub, value[k], f"{where}.{k}")
    if expected is list:
        if len(value) > schema.get("maxItems", len(value)):
            problems.append(f"{where} has more than {schema['maxItems']} items")
        for i, item in enumerate(value):
            problems += _check(schema["items"], item, f"{where}[{i}]")
    return problems
