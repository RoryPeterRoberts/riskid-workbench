"""The fundamental rights impact assessment for one system (Article 27(1); B.7; chapter 12).

Each of the six elements is assembled from the fields B.7 maps to it, and
names those fields as its source, so the assessment is "assembly of what is
already recorded and not a new project" (chapter 12). An element with nothing
recorded says what is missing.
"""

from __future__ import annotations

import io

from riskid.assess import latest_assessments

ELEMENTS = (
    ("27(1)(a)", "The deployer's processes in which the system is used, in line with its intended purpose",
     "Register: title and description of the lines that apply; lifecycle. Inventory fields 1, 4 and 5; "
     "template headers 1 and 4."),
    ("27(1)(b)", "The period within which, and the frequency with which, the system is used",
     "Register: lifecycle. Inventory field 13 and field 11 (stage); template field 6 and header 3."),
    ("27(1)(c)", "The categories of natural persons and groups likely to be affected",
     "Register: who is harmed (B.3 column 17). Inventory field 6; template header 5."),
    ("27(1)(d)", "The specific risks of harm likely to affect those categories",
     "Register: lines in categories 3.x, 5.5 and 7.1 (the FAI lines, HUM-08, LEG-01, LEG-02) with L, I, "
     "V, S and data quality. Template fields 3 to 7 and 11; assessment record fields 1 and 4."),
    ("27(1)(e)", "The implementation of human oversight measures, according to the instructions for use",
     "Register: controls (A.9.3) and owner of HUM-01, HUM-05 and HUM-07; the override rate. Inventory "
     "field 5; template field 8."),
    ("27(1)(f)", "The measures to be taken if those risks materialise, including internal governance and "
     "complaint mechanisms",
     "Register: recovery controls, owner and indicators, residual L and I; TRA-02. Template fields 8 to 10; "
     "Annex A A.8.3 and A.3.3; inventory field 10."),
)
OVERSIGHT_LINES = ("HUM-01", "HUM-05", "HUM-07")


def _control_text(c: dict) -> str:
    tested = f"tested {c['last_test_date']}, {c['last_test_result']}" if c.get("last_test_date") else "untested"
    return f"{c['name']} ({c['type']}): {tested}"


def build(system: dict, state: dict, library: dict) -> list:
    """``[(element, title, source, [statements])]`` for the six elements of Article 27(1)."""
    sys_id = system["id"]
    lines = {i: l for i, l in state.get("register", {}).items()
             if l.get("system_id") == sys_id and l.get("status") != "retired"}
    latest = latest_assessments(state)
    controls = {i: [c for c in state.get("control", {}).values() if c.get("line_id") == i] for i in lines}
    title = {i: (library[i].title if i in library else l.get("definition")) for i, l in lines.items()}
    users = ", ".join(f"{u['role']} ({u['number']})" if u.get("number") else u["role"]
                      for u in system.get("users") or [])
    a = [f"{system.get('name')}: {system.get('function') or 'function not recorded'}."]
    if system.get("purpose_stated") or system.get("purpose_in_use"):
        a.append(f"Purpose as stated: {system.get('purpose_stated') or 'not recorded'}; "
                 f"purpose in use: {system.get('purpose_in_use') or 'not recorded'}.")
    if users:
        a.append(f"Users: {users}.")
    a += [f"{i} {title[i]} ({'; '.join(lines[i].get('lifecycle_stages') or [])})" for i in sorted(lines)]
    b = [f"Period and frequency: {system.get('period_and_frequency') or 'not recorded (inventory field 13)'}.",
         f"Lifecycle stage: {system.get('lifecycle_stage') or 'not recorded'}."]
    groups = [p["group"] + (" (vulnerable)" if p.get("vulnerable") else "") for p in system.get("persons_affected") or []]
    c = ([f"Groups affected: {', '.join(groups)}."] if groups else
         ["Not yet recorded: the groups affected (inventory field 6)."])
    harmed = sorted({h for l in lines.values() for h in l.get("persons_affected") or []})
    if harmed:
        c.append(f"Harmed, by the lines that apply: {', '.join(harmed)}.")
    d = []
    for i in sorted(lines):
        l2 = str(lines[i].get("l2") or "")
        if l2.startswith("3.") or l2 in ("5.5", "7.1"):
            s = latest.get(i, (None, None))[1]
            scores = (f"L {s['likelihood']}, I {max(s['impact'].values())} (IND {s['impact'].get('IND')}), "
                      f"V {s['vulnerability']}, S {s['speed']}, data quality {s['data_quality']}"
                      if s else "not yet assessed")
            d.append(f"{i} {title[i]}: {scores}.")
    e = []
    for i in OVERSIGHT_LINES:
        if i in lines:
            owner = lines[i].get("owner") or "owner not named"
            found = "; ".join(_control_text(x) for x in controls[i]) or "no controls recorded"
            e.append(f"{i} {title[i]} ({owner}): {found}.")
    if users:
        e.append(f"Who oversees in use (inventory field 5): {users}.")
    f = []
    for bt in state.get("bowtie", {}).values():
        if bt.get("line_id") in lines:
            f += [f"{bt['line_id']} recovery: {r}" for r in bt.get("recovery_controls") or [] if r]
    for i in sorted(lines):
        s = latest.get(i, (None, None))[1]
        if s and s.get("material"):
            f.append(f"{i} residual L {s['residual_L']}, I {s['residual_I']}; owner "
                     f"{lines[i].get('owner') or 'not named'}.")
    if "TRA-02" in lines:
        f.append("TRA-02 (route to contest): " + ("; ".join(_control_text(x) for x in controls["TRA-02"])
                                                    or "no controls recorded") + ".")
    f.append(f"Accountable for the system (inventory field 10): {system.get('owner') or 'not named'}.")
    gaps = {"27(1)(d)": "Not yet recorded: no line in categories 3.x, 5.5 or 7.1 is in the register for this system.",
            "27(1)(e)": "Not yet recorded: HUM-01, HUM-05 and HUM-07 are not in the register for this system."}
    out = []
    for (element, heading, source), statements in zip(ELEMENTS, (a, b, c, d, e, f)):
        out.append((element, heading, source, statements or [gaps.get(element, "Not yet recorded.")]))
    return out


def to_docx(system: dict, elements: list, prov: dict) -> bytes:
    from docx import Document

    doc = Document()
    doc.add_heading(f"Fundamental rights impact assessment: {system['id']} {system.get('name')}", level=1)
    doc.add_paragraph("Article 27(1) of the AI Act, assembled from the register as mapped in Appendix B.7. "
                      "The duty falls on deployers that are public bodies, private entities providing public "
                      "services, and deployers of the systems in Annex III, points 5(b) and (c).")
    doc.add_paragraph(f"Built from data packs {prov['pack_versions']}; register state hash {prov['state_hash']}; "
                      f"generated {prov['generated_at']} by {prov['generated_by']}.")
    for element, heading, source, statements in elements:
        doc.add_heading(f"{element} {heading}", level=2)
        for statement in statements:
            doc.add_paragraph(statement, style="List Bullet")
        doc.add_paragraph(f"Source: {source}")
    out = io.BytesIO()
    doc.save(out)
    return out.getvalue()
