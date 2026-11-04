"""The living register (chapter 11; template B.3; SPEC.md 6.9).

Every function here works on a state snapshot, the live one or one replayed
to a date, so the grid an auditor sees for 30 June is built exactly as
today's. A line's audit trail is every event on the line and on what hangs
from it: its assessments, controls, disagreements, use cases, links, bow-ties
and resolutions.
"""

from __future__ import annotations

import json

from riskid import rules
from riskid.assess import latest_assessments
from riskid.interact import LETTER

COSO = ("strategic", "operations", "reporting", "compliance")


def _assessments(state: dict, line_id: str) -> list:
    return [(i, a) for i, a in sorted(state.get("assessment", {}).items(), key=lambda kv: int(kv[0].rsplit("-", 1)[-1]))
            if a.get("line_id") == line_id]


def trend(history: list) -> str:
    """B.3 field 13: increasing, stable or decreasing since the last assessment, or new."""
    if not history:
        return ""
    if len(history) == 1:
        return "new"
    before, now = history[-2][1].get("inherent", 0), history[-1][1].get("inherent", 0)
    return "increasing" if now > before else "decreasing" if now < before else "stable"


def interaction_summary(state: dict, line_id: str) -> str:
    """B.3 field 11: the line's links each way and its bow-tie references."""
    parts = []
    for link in state.get("interaction", {}).values():
        if link.get("kind") in LETTER and link["from_line"] == line_id:
            parts.append(f"{link['kind']} {link['to_line']}")
        elif link.get("kind") in LETTER and link["to_line"] == line_id:
            parts.append(f"{link['kind']} by {link['from_line']}")
    parts += [f"bow-tie {bt_id}" for bt_id, b in sorted(state.get("bowtie", {}).items())
              if b.get("line_id") == line_id]
    return "; ".join(sorted(parts))


def grid_rows(state: dict, library: dict, taxonomy: dict) -> list:
    """One row per live register line, with the 14 fields and the 5 AI columns of B.3."""
    latest = latest_assessments(state)
    rows = []
    for line_id, line in sorted(state.get("register", {}).items()):
        if line.get("status") == "retired":
            continue
        a = latest.get(line_id, (None, None))[1]
        controls = [c for c in state.get("control", {}).values() if c.get("line_id") == line_id]
        lib = library.get(line_id)
        rows.append({
            "id": line_id, "line": line, "a": a,
            "taxonomy": f"{line.get('l1')} {line.get('l2')} {taxonomy.get(line.get('l2'), '')}".strip(),
            "controls": [f"{c['name']} ({c['type']}): " + (f"tested {c['last_test_date']}, "
                                                           f"{c['last_test_result']}"
                                                           if c.get("last_test_date") else "untested")
                         for c in controls],
            "residual_band": rules.band(a["residual"]) if a and a.get("residual") else None,
            "interactions": interaction_summary(state, line_id),
            "indicators": lib.kri if lib else "",
            "trend": trend(_assessments(state, line_id)),
            "last_review": a.get("date") if a else None,
        })
    return rows


def retired_rows(state: dict) -> list:
    return [(i, line) for i, line in sorted(state.get("register", {}).items())
            if line.get("status") == "retired"]


def signs(state: dict, rows: list) -> list:
    """Chapter 11's signs of a living inventory against a compliance artefact."""
    n = len(rows) or 1
    assessed = [r["a"] for r in rows if r["a"]]
    ratings = [a.get("data_quality") for a in assessed]
    review_dates = {a.get("date") for a in assessed}
    return [
        ("Lines with a named owner", f"{sum(1 for r in rows if r['line'].get('owner'))} of {len(rows)}"),
        ("Data quality ratings rated Medium", f"{ratings.count('Medium')} of {len(ratings)} assessed "
                                               "(the AI officer challenges every Medium)"),
        ("Lines with an interaction summary", f"{sum(1 for r in rows if r['interactions'])} of {len(rows)}"),
        ("Entries in the disagreement log", str(len(state.get("disagreement", {})))),
        ("Different review dates", f"{len(review_dates)} across {len(assessed)} assessed lines "
                                   "(staggered dates are a sign of life)"),
        ("Lines assessed", f"{len(assessed)} of {len(rows)} ({100 * len(assessed) // n}%)"),
    ]


def trail(state: dict, events: list, line_id: str) -> list:
    """Every event on the line and on what hangs from it, oldest first."""
    related = {("register", line_id), ("resolution", line_id)}
    for entity, key in (("assessment", "line_id"), ("control", "line_id"), ("disagreement", "line_id"),
                        ("usecase", "line_id"), ("bowtie", "line_id")):
        related |= {(entity, i) for i, x in state.get(entity, {}).items() if x.get(key) == line_id}
    related |= {("interaction", i) for i, x in state.get("interaction", {}).items()
                if line_id in (x.get("from_line"), x.get("to_line"))}
    out = []
    for e in events:
        if (e["entity"], e["entity_id"]) in related:
            new = json.loads(e["new"]) if e["new"] else None
            out.append({**e, "summary": new if e["field"] else None})
    return out
