"""Reconciliation (chapter 8): match, gap, challenge, resolve, record.

Top-down entries are the lines a closed workshop voted for, and any register
line whose source is top-down. Bottom-up entries are the accepted use cases.
They match on the taxonomy's Level 2 node and the system, as chapter 8 says;
what is left unmatched in either direction is a gap, and so is a line adopted
from the library that neither track raised. A blind spot is a line the filter
proposed for a system that is in neither track nor the register: "Every
register line that is absent from the reconciled register receives a recorded
reason" (chapter 8). Every gap and every disagreement gets one of five
dispositions, with a reason, a person and a date.
"""

from __future__ import annotations

from riskid.model import LibraryLine
from riskid.propose import propose_lines
from riskid.workshop import ranking

DISPOSITIONS = (
    ("add", "Add to the register as a new line", "added to the register"),
    ("merge", "Merge with an existing line", "merged"),
    ("escalate", "Escalate to the principal list", "escalated to the principal list"),
    ("local", "Accept as local", "accepted as local"),
    ("not applicable", "Close as not applicable", "closed as not applicable"),
)
DISPOSITION_KEYS = tuple(d[0] for d in DISPOSITIONS)
DONE = {d[0]: d[2] for d in DISPOSITIONS}
# Where linked entries disagree: on an impact dimension, the likelihood, or a control (ch 8).
DIMENSIONS = ("FIN", "REG", "REP", "IND", "OPS", "likelihood", "control effectiveness")


def _l2_of(state: dict, library: dict) -> dict:
    l2 = {i: line.l2 for i, line in library.items()}
    l2.update({i: line.get("l2") for i, line in state.get("register", {}).items()})
    return l2


def top_down_entries(state: dict, library: dict) -> list:
    """Lines a closed workshop voted for, then top-down register lines no workshop names."""
    l2 = _l2_of(state, library)
    entries, seen = [], set()
    for ws_id, ws in sorted(state.get("workshop", {}).items()):
        if ws.get("status") != "closed":
            continue
        for entry in ranking(ws.get("votes")):
            if entry["id"] in l2:
                entries.append({"source": ws_id, "line_id": entry["id"], "l2": l2[entry["id"]],
                                "systems": list(ws["system_ids"]), "voters": entry["voters"]})
                seen.add(entry["id"])
    for line_id, line in sorted(state.get("register", {}).items()):
        if line.get("source") == "top-down" and line_id not in seen and line.get("status") != "retired":
            entries.append({"source": "register", "line_id": line_id, "l2": line.get("l2"),
                            "systems": [line.get("system_id")], "voters": None})
    return entries


def bottom_up_entries(state: dict) -> list:
    """The accepted use cases, each with its line, node and system."""
    return [{"source": uc_id, "line_id": u.get("line_id"), "l2": (u.get("fields_") or {}).get("taxonomy"),
             "system": u.get("system_id")}
            for uc_id, u in sorted(state.get("usecase", {}).items()) if u.get("status") == "accepted"]


def match_table(top_down: list, bottom_up: list) -> list:
    """Each top-down entry with the bottom-up entries at its node in its systems."""
    rows = []
    for td in top_down:
        linked = [bu for bu in bottom_up if bu["l2"] == td["l2"] and bu["system"] in td["systems"]]
        rows.append({**td, "matched": linked, "system_count": len({bu["system"] for bu in linked})})
    return rows


def gaps(state: dict, top_down: list, bottom_up: list) -> list:
    """What is left unmatched in each direction, and library lines neither track raised."""
    out, covered = [], set()
    for row in match_table(top_down, bottom_up):
        covered.add(row["line_id"])
        if row["matched"]:
            covered.update(bu["line_id"] for bu in row["matched"])
        else:
            out.append({"subject": row["line_id"], "kind": "no submission", "l2": row["l2"],
                         "systems": row["systems"],
                         "detail": f"raised top-down ({row['source']}); no bottom-up entry at this "
                                   "node for its systems"})
    for bu in bottom_up:
        if not any(bu["l2"] == td["l2"] and bu["system"] in td["systems"] for td in top_down):
            out.append({"subject": bu["line_id"], "kind": "no top-down line at this node",
                        "l2": bu["l2"], "systems": [bu["system"]],
                        "detail": f"submitted bottom-up ({bu['source']}); no top-down line at this "
                                  "node for this system"})
            covered.add(bu["line_id"])
    raised = covered | {bu["line_id"] for bu in bottom_up}
    for line_id, line in sorted(state.get("register", {}).items()):
        if line_id not in raised and line.get("status") != "retired":
            out.append({"subject": line_id, "kind": "no submission", "l2": line.get("l2"),
                        "systems": [line.get("system_id")],
                        "detail": f"{line.get('source')} line; neither track raised it"})
    return out


def blind_spots(state: dict, library: dict) -> list:
    """Lines proposed for some system that are in neither track nor the register."""
    register = state.get("register", {})
    found: dict = {}
    for system_id, system in sorted(state.get("system", {}).items()):
        for line, _ in propose_lines(system, list(library.values())):
            if line.id not in register:
                found.setdefault(line.id, {"subject": line.id, "kind": "blind spot",
                                           "l2": line.l2, "title": line.title, "systems": []})
                found[line.id]["systems"].append(system_id)
    return list(found.values())


def library_lines(store) -> dict:
    return {d["id"]: LibraryLine.from_dict(d) for d in store.library()}
