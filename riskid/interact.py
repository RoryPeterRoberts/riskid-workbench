"""Risk interaction (chapter 10): the matrix, its nodes, candidate links and concentration.

The matrix has the material lines on both axes, with every line linked to
them; each ordered pair records whether the row line triggers (T) the column
line, amplifies it (A) or is correlated with it through a shared driver (C),
with the mechanism and the delay. It is not symmetric. A cell with no
mechanism stays blank, so a link is refused without one; a judgement of no
effect is recorded as "none" rather than deleted.
"""

from __future__ import annotations

from collections import Counter

KINDS = ("triggers", "amplifies", "shared driver", "none")
LETTER = {"triggers": "T", "amplifies": "A", "shared driver": "C"}


def live_links(interactions: dict) -> list:
    return [link for link in interactions.values() if link.get("kind") in LETTER]


def axis_lines(material: set, interactions: dict, live: set) -> list:
    """The material lines and every line in a recorded link, still live, sorted."""
    lines = set(material)
    for link in live_links(interactions):
        lines.update((link["from_line"], link["to_line"]))
    return sorted(lines & live)


def nodes(interactions: dict) -> tuple[list, list]:
    """``(propagation, vulnerable)``: lines by outgoing and by incoming links, most first.

    Chapter 10: a propagation node sets other lines off; a vulnerable node is
    reached by many. Only lines with at least two links in that direction.
    """
    def ranked(counts):
        return [(line, n) for line, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
                if n >= 2]

    out = Counter(link["from_line"] for link in live_links(interactions))
    into = Counter(link["to_line"] for link in live_links(interactions))
    return ranked(out), ranked(into)


def candidate_links(register: dict, interactions: dict) -> list:
    """Ordered pairs of live lines that cite the same Annex A control, not yet judged.

    Chapter 10: lines that name the same control, data source or owner are the
    first candidates; the session confirms or strikes them.
    """
    judged = {(link["from_line"], link["to_line"]) for link in interactions.values()}  # ordered
    by_control: dict = {}
    for line_id, line in sorted(register.items()):
        if line.get("status") == "retired":
            continue
        for ref in line.get("annex_a_controls") or []:
            by_control.setdefault(ref, []).append(line_id)
    out = []
    for ref, lines in sorted(by_control.items()):
        pairs = [(a, b) for a in lines for b in lines if a != b and (a, b) not in judged]
        if pairs:
            out.append({"control": ref, "lines": lines, "pairs": pairs})
    return out


def concentration(systems: dict, register: dict) -> dict:
    """Chapter 10's concentration counts: systems per supplier, per model provider and per
    model; live lines per Annex A control; and hidden concentration, one model under
    several suppliers."""
    def count(key):
        table: dict = {}
        for sys_id, system in sorted(systems.items()):
            value = key(system)
            if value:
                table.setdefault(value, []).append(sys_id)
        return sorted(table.items(), key=lambda kv: (-len(kv[1]), kv[0]))

    def model(system):
        parts = [system.get("model_provider"), system.get("model_name")]
        return " ".join(p for p in parts if p) or None

    by_model = count(model)
    hidden = []
    for name, ids in by_model:
        suppliers = {systems[i].get("supplier") for i in ids if systems[i].get("supplier")}
        if len(suppliers) > 1:
            hidden.append({"model": name, "suppliers": sorted(suppliers), "systems": ids})
    controls: dict = {}
    for line_id, line in sorted(register.items()):
        if line.get("status") != "retired":
            for ref in line.get("annex_a_controls") or []:
                controls.setdefault(ref, []).append(line_id)
    return {"supplier": count(lambda s: s.get("supplier")),
            "provider": count(lambda s: s.get("model_provider")),
            "model": by_model, "hidden": hidden,
            "controls": sorted(((ref, ids) for ref, ids in controls.items() if len(ids) > 1),
                               key=lambda kv: (-len(kv[1]), kv[0]))}
