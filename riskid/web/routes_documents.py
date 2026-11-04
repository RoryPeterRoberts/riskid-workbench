"""Documents (SPEC.md section 7, 6.10; chapter 12): generate and download.

Each download is built from the current state, carries the data-pack versions
and the register state hash, and is recorded as a Document (DOC-nnn) in the
audit trail. The ``.html`` forms are previews of the same content and are not
recorded. Because a download writes to the audit trail, one that the browser
says another site's page asked for is refused, as other changes are.
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, Response

from riskid.documents import fria, register, render as docs, report, soa
from riskid.documents.provenance import provenance, record
from riskid.reconcile import library_lines
from riskid.store import Store
from riskid.web import get_store, render

router = APIRouter()
TYPES = {"xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
         "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
         "csv": "text/csv; charset=utf-8", "pdf": "application/pdf", "zip": "application/zip"}


def send_document(request, store, kind: str, name: str, fmt: str, body, prov: dict):
    if request.headers.get("sec-fetch-site") in ("cross-site", "same-site"):
        raise HTTPException(403, "Refused: a download is recorded in the audit trail, "
                                 "so it must come from the workbench's own pages.")
    filename = f"riskid-{name}-{date.today().isoformat()}.{fmt}"
    record(store, kind, filename, prov, request.app.state.actor)
    return Response(body, media_type=TYPES[fmt],
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.get("/documents")
async def documents(request: Request, store: Store = Depends(get_store)):
    state = store.state()
    return render(request, "documents.html", "documents",
                  systems=sorted(state.get("system", {}).values(), key=lambda s: s["id"]),
                  recorded=sorted(state.get("document", {}).items(), reverse=True),
                  prov=provenance(state, request.app.state.actor))


@router.get("/documents/register.{fmt}")
async def register_document(fmt: str, request: Request, store: Store = Depends(get_store)):
    state = store.state()
    prov = provenance(state, request.app.state.actor)
    table = register.rows(state, library_lines(store))
    if fmt == "html":
        return HTMLResponse(docs.html("register.html", table=table, prov=prov))
    if fmt == "xlsx":
        return send_document(request, store, "register", "register", fmt, register.to_xlsx(table, prov), prov)
    if fmt == "csv":
        return send_document(request, store, "register", "register", fmt, register.to_csv(table, prov), prov)
    if fmt == "pdf":
        return send_document(request, store, "register", "register", fmt,
                     docs.pdf(docs.html("register.html", table=table, prov=prov)), prov)
    raise HTTPException(404, "The register comes as xlsx, csv, pdf or html.")


@router.get("/documents/fria/{system_id}.{fmt}")
async def fria_document(system_id: str, fmt: str, request: Request, store: Store = Depends(get_store)):
    state = store.state()
    system = state.get("system", {}).get(system_id)
    if system is None:
        raise HTTPException(404, f"No system {system_id} in this inventory.")
    prov = provenance(state, request.app.state.actor)
    elements = fria.build(system, state, library_lines(store))
    markup = docs.html("fria.html", system=system, elements=elements, prov=prov)
    if fmt == "html":
        return HTMLResponse(markup)
    if fmt == "docx":
        return send_document(request, store, "FRIA", f"fria-{system_id}", fmt,
                             fria.to_docx(system, elements, prov), prov)
    if fmt == "pdf":
        return send_document(request, store, "FRIA", f"fria-{system_id}", fmt, docs.pdf(markup), prov)
    raise HTTPException(404, "The FRIA comes as docx, pdf or html.")


@router.get("/documents/soa.{fmt}")
async def soa_document(fmt: str, request: Request, store: Store = Depends(get_store)):
    state = store.state()
    prov = provenance(state, request.app.state.actor)
    table = soa.entries(state)
    markup = docs.html("soa.html", table=table, prov=prov)
    if fmt == "html":
        return HTMLResponse(markup)
    if fmt == "xlsx":
        return send_document(request, store, "SoA", "soa", fmt, soa.to_xlsx(table, prov), prov)
    if fmt == "pdf":
        return send_document(request, store, "SoA", "soa", fmt, docs.pdf(markup), prov)
    raise HTTPException(404, "The SoA comes as xlsx, pdf or html.")


@router.get("/documents/report.{fmt}")
async def report_document(fmt: str, request: Request, store: Store = Depends(get_store)):
    state = store.state()
    prov = provenance(state, request.app.state.actor)
    previous = [d["generated_at"] for d in state.get("document", {}).values() if d.get("kind") == "board report"]
    items = report.build(state, library_lines(store), store.events(), max(previous) if previous else None)
    markup = docs.html("report.html", items=items, prov=prov)
    if fmt == "html":
        return HTMLResponse(markup)
    if fmt == "pdf":
        return send_document(request, store, "board report", "board-report", fmt, docs.pdf(markup), prov)
    raise HTTPException(404, "The board report comes as pdf or html.")
