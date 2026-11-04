"""The quarterly pack and the evidence pack (SPEC.md section 7; chapter 13).

Quarterly pack: the register (XLSX, CSV), the change list since the previous
signed run, the disagreement log and the run's checklist with its evidence
and sign-off (HTML and PDF), so it opens in Excel, a PDF reader and a browser
(SPEC.md section 11). Evidence pack: the register, the heat maps, the FRIA of each
high-risk system, the Statement of Applicability, the board report, the
checklist of every signed run, the disagreement log and the whole audit
trail. Each is one ZIP, and carries the data-pack versions and the state hash
in its README.
"""

from __future__ import annotations

import csv
import io
import zipfile

from riskid import importers
from riskid.documents import fria, heatmap, register, render, report, soa


def _csv(header: list, rows: list) -> str:
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(header)
    writer.writerows(rows)
    return out.getvalue()


def change_list(events: list) -> str:
    """The register's changes among ``events``: the run passes the events of the period it covers."""
    rows = [[e["ts"], e["actor"], e["entity_id"], e["field"] or "whole line", e["reason"] or ""]
            for e in events if e["entity"] == "register"]
    return _csv(["When (UTC)", "Who", "Line", "Field", "Reason"], rows)


def disagreement_log(state: dict) -> str:
    rows = [[k, d.get("line_id"), d.get("raised_in"), d.get("holder"), d.get("majority_score"),
             d.get("minority_score"), d.get("dimension"), d.get("evidence"), d.get("status")]
            for k, d in sorted(state.get("disagreement", {}).items())]
    return _csv(["ID", "Line", "Raised in", "Held by", "Majority score", "Minority score", "Dimension",
                 "Evidence", "Status"], rows)


def _readme(prov: dict, what: str) -> str:
    return (f"RiskID Workbench {what}\nGenerated {prov['generated_at']} by {prov['generated_by']}\n"
            f"Data packs: {prov['pack_versions']}\nRegister state hash: {prov['state_hash']}\n")


def quarterly(state: dict, library: dict, events: list, run_id: str, run: dict, steps: list,
              prov: dict) -> bytes:
    table = register.rows(state, library)
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as pack:
        pack.writestr("README.txt", _readme(prov, f"quarterly pack for {run_id}"))
        pack.writestr("register.xlsx", register.to_xlsx(table, prov))
        pack.writestr("register.csv", register.to_csv(table, prov))
        pack.writestr("change_list.csv", change_list(events))
        pack.writestr("disagreement_log.csv", disagreement_log(state))
        checklist = render.html("checklist.html", run_id=run_id, run=run, steps=steps, prov=prov)
        pack.writestr("checklist.html", checklist)
        pack.writestr("checklist.pdf", render.pdf(checklist))
    return out.getvalue()


def evidence(state: dict, library: dict, events: list, prov: dict) -> bytes:
    table = register.rows(state, library)
    rows = [[e["seq"], e["ts"], e["actor"], e["entity"], e["entity_id"], e["field"] or "", e["new"] or "",
             e["reason"] or "", e["evidence_ref"] or ""] for e in events]
    cells = [{"id": r[0], "L": r[10], "I": r[11], "rL": r[22], "rI": r[23]} for r in table]
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as pack:
        pack.writestr("README.txt", _readme(prov, "evidence pack"))
        pack.writestr("register.xlsx", register.to_xlsx(table, prov))
        pack.writestr("register.csv", register.to_csv(table, prov))
        pack.writestr("soa.xlsx", soa.to_xlsx(soa.entries(state), prov))
        pack.writestr("disagreement_log.csv", disagreement_log(state))
        pack.writestr("audit_trail.csv", _csv(["Seq", "When (UTC)", "Who", "Entity", "ID", "Field", "New value",
                                               "Reason", "Evidence"], rows))
        pack.writestr("heatmap_inherent.png", heatmap.render(cells, "L", "I", "Inherent risk"))
        pack.writestr("heatmap_residual.png", heatmap.render(cells, "rL", "rI", "Residual risk"))
        for sys_id, system in sorted(state.get("system", {}).items()):
            if (system.get("article_6_outcome") or "").startswith("high-risk"):
                pack.writestr(f"fria_{sys_id}.docx", fria.to_docx(system, fria.build(system, state, library), prov))
        items = report.build(state, library, events, None)
        pack.writestr("board_report.pdf", render.pdf(render.html("report.html", items=items, prov=prov)))
        steps = importers.load_checklist()
        for run_id, run in sorted(state.get("cycle", {}).items()):
            if run.get("signed_date"):
                pack.writestr(f"checklist_{run_id}.html",
                              render.html("checklist.html", run_id=run_id, run=run, steps=steps, prov=prov))
    return out.getvalue()
