"""The register as a document: XLSX in the book's column order, CSV and PDF (SPEC.md section 7).

The thirty columns are the book's register file's, so a workbench export and
the book's register can be read side by side. Two of them describe the book's
own control catalogue and stay empty here. The "Target residual" columns hold
the residual of the latest assessment, which on a live system is what the
tested controls support.
"""

from __future__ import annotations

import csv
import io

from riskid import importers, rules
from riskid.assess import latest_assessments

COLUMNS = (
    "Risk ID", "L1 category", "L2", "Risk", "Definition (cause, event, consequence)", "Lifecycle stage",
    "Role exposed", "Who is harmed", "Unit of exposure", "Harm scored", "Likelihood", "Impact",
    "Dominant dimension", "Vulnerability", "Speed of onset", "Inherent score", "Inherent band", "Material",
    "Data quality", "Key controls (ISO/IEC 42001 Annex A)", "Catalogue controls (ai-management-system, MIT)",
    "Annex A refs with no catalogue control", "Target residual L", "Target residual I",
    "Target residual score", "Target residual band", "Owner (role)", "Key risk indicator",
    "Regulatory hooks", "Sources and precedents",
)


def rows(state: dict, library: dict) -> list:
    """One list of thirty values per live register line, in ID order."""
    scales = importers.load_scales()
    l1_names = {t["l1_code"]: t["l1"] for t in state.get("taxonomy", {}).values()}
    latest = latest_assessments(state)
    out = []
    for line_id, line in sorted(state.get("register", {}).items()):
        if line.get("status") == "retired":
            continue
        lib = library.get(line_id)
        a = latest.get(line_id, (None, {}))[1] or {}
        controls = [c for c in state.get("control", {}).values() if c.get("line_id") == line_id]
        impact = max(a["impact"].values()) if a.get("impact") else None
        out.append([
            line_id, l1_names.get(line.get("l1"), line.get("l1")), line.get("l2"),
            lib.title if lib else line.get("definition"), line.get("definition"),
            "; ".join(line.get("lifecycle_stages") or []), line.get("role"),
            "; ".join(line.get("persons_affected") or []),
            a.get("unit_of_exposure") or (lib.exposure if lib else None),
            a.get("harm_scored") or (lib.event if lib else None),
            a.get("likelihood"), impact,
            scales[a["dominant_dimension"]]["name"] if a.get("dominant_dimension") else None,
            a.get("vulnerability"), a.get("speed"), a.get("inherent"), a.get("inherent_band"),
            ("Yes" if a.get("material") else "No") if a else None, a.get("data_quality"),
            "; ".join([f"{c['name']} ({c.get('annex_a_ref') or c['type']})" for c in controls]
                      or [", ".join(line.get("annex_a_controls") or [])]),
            None, None,
            a.get("residual_L"), a.get("residual_I"), a.get("residual"),
            rules.band(a["residual"]) if a.get("residual") else None,
            line.get("owner"), lib.kri if lib else None, "; ".join(line.get("regulatory_hooks") or []),
            lib.sources if lib else None,
        ])
    return out


def to_xlsx(table: list, prov: dict) -> bytes:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill

    book = Workbook()
    sheet = book.active
    sheet.title = "Register"
    sheet.append(list(COLUMNS))
    for cell in sheet[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="1B2A4A")
        cell.alignment = Alignment(wrap_text=True, vertical="top")
    for row in table:
        sheet.append(row)
    sheet.freeze_panes = "E2"
    about = book.create_sheet("About")
    for row in about_rows(prov):
        about.append(row)
    out = io.BytesIO()
    book.save(out)
    return out.getvalue()


def about_rows(prov: dict) -> list:
    return [["RiskID Workbench"], ["Generated", prov["generated_at"], "by", prov["generated_by"]],
            ["Data packs", prov["pack_versions"]], ["Register state hash", prov["state_hash"]]]


def to_csv(table: list, prov: dict) -> str:
    out = io.StringIO()
    out.write(f"# RiskID Workbench register; data packs: {prov['pack_versions']}; "
              f"register state hash: {prov['state_hash']}; generated {prov['generated_at']}\n")
    writer = csv.writer(out)
    writer.writerow(COLUMNS)
    writer.writerows(table)
    return out.getvalue()
