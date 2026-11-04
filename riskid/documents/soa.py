"""The Statement of Applicability (ISO/IEC 42001 clause 6.1.3(f); chapter 12).

"For each of the 38 Annex A controls, list the register lines that cite it in
their control summary. A control cited by a material line is included, and the
lines are the justification" (chapter 12). Here the references come from the
live lines: each line's Annex A references (B.3 field 19) and the Annex A
reference of each control recorded on it. Retired lines do not count.
"""

from __future__ import annotations

import io

from riskid.assess import latest_assessments
from riskid.documents.register import about_rows


def _key(ref: str) -> list:
    return [int(p) if p.isdecimal() else 0 for p in ref.split(".")[1:]]


def entries(state: dict) -> list:
    """``[(ref, lines, justification)]`` for every Annex A reference on a live line."""
    register = state.get("register", {})
    live = {i for i, line in register.items() if line.get("status") != "retired"}
    material = {i for i, (_, a) in latest_assessments(state).items() if a.get("material")}
    cited: dict = {}
    for line_id in sorted(live):
        for ref in register[line_id].get("annex_a_controls") or []:
            cited.setdefault(ref, set()).add(line_id)
    for control in state.get("control", {}).values():
        if control.get("line_id") in live and control.get("annex_a_ref"):
            cited.setdefault(control["annex_a_ref"], set()).add(control["line_id"])
    out = []
    for ref in sorted(cited, key=_key):
        lines = sorted(cited[ref])
        why = ("included: cited by a material line" if set(lines) & material
               else "cited by lines not yet material: include or record the reason to exclude")
        out.append((ref, lines, why))
    return out


def to_xlsx(table: list, prov: dict) -> bytes:
    from openpyxl import Workbook
    from openpyxl.styles import Font

    book = Workbook()
    sheet = book.active
    sheet.title = "Statement of Applicability"
    sheet.append(["Annex A control", "Register lines that cite it", "Inclusion and justification"])
    for cell in sheet[1]:
        cell.font = Font(bold=True)
    for ref, lines, why in table:
        sheet.append([ref, ", ".join(lines), why])
    about = book.create_sheet("About")
    for row in about_rows(prov):
        about.append(row)
    out = io.BytesIO()
    book.save(out)
    return out.getvalue()
