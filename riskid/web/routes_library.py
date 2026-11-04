"""Library (SPEC.md 6.3; Appendix A and chapter 4): the 91 lines, the taxonomy, proposals, adoption.

Proposals come from :mod:`riskid.propose` (chapter 5's straw man). Adopting a
line records a candidate register line that keeps the library ID, as one
whole-entity event; a line already in the register is not adopted again.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse

from riskid.model import Event, LibraryLine
from riskid.propose import register_line_from_library, screen_lines
from riskid.store import Store
from riskid.web import get_store, render

router = APIRouter()


def _l2_key(code: str) -> list:
    return [int(p) if p.isdecimal() else 0 for p in str(code).split(".")]


def _library(store: Store) -> list[LibraryLine]:
    """The organisation's library as loaded into its file, in the taxonomy's order."""
    order = {t["l1_code"]: _l2_key(t["l2_code"])[0] for t in store.taxonomy()}
    lines = [LibraryLine.from_dict(d) for d in store.library()]
    return sorted(lines, key=lambda line: (order.get(line.l1, 99), line.id))


def _taxonomy(store: Store) -> list[dict]:
    return sorted(store.taxonomy(), key=lambda t: _l2_key(t["l2_code"]))


def _l1_names(store: Store) -> dict:
    return {t["l1_code"]: t["l1"] for t in store.taxonomy()}


def _matches(line: LibraryLine, q: str) -> bool:
    text = " ".join(str(getattr(line, f) or "") for f in
                    ("id", "title", "description", "event", "reg", "controls", "kri")).lower()
    return all(word in text for word in q.lower().split())


@router.get("/library")
async def library_list(request: Request, q: str = "", l1: str = "",
                       store: Store = Depends(get_store)):
    lines = [line for line in _library(store)
             if (not l1 or line.l1 == l1) and (not q.strip() or _matches(line, q))]
    systems = sorted(store.state().get("system", {}).values(), key=lambda s: s["id"])
    return render(request, "library_list.html", "library", lines=lines, q=q, l1=l1,
                  l1_names=_l1_names(store), taxonomy=_taxonomy(store), systems=systems)


def _propose_page(request, store, system_id, status_code=200, refusal=None, adopted=None):
    systems = store.state().get("system", {})
    system = systems.get(system_id) if system_id else None
    if system_id and system is None:
        raise HTTPException(404, f"No system {system_id} in this inventory.")
    proposed = removed = []
    if system is not None:
        proposed, removed = screen_lines(system, _library(store))
    register = store.state().get("register", {})
    return render(request, "library_propose.html", "library", status_code=status_code,
                  system=system, systems=sorted(systems.values(), key=lambda s: s["id"]),
                  proposed=proposed, removed=removed, register=register,
                  l1_names=_l1_names(store), refusal=refusal, adopted=adopted)


@router.get("/library/propose")
async def library_propose(request: Request, system: str = "", store: Store = Depends(get_store)):
    adopted = request.query_params.get("adopted", "")
    known = {line.id for line in _library(store)}
    return _propose_page(request, store, system or None,
                         adopted=adopted if adopted in known else None)


@router.post("/library/adopt")
async def library_adopt(request: Request, store: Store = Depends(get_store)):
    form = await request.form()
    line_id, system_id = str(form.get("line_id", "")), str(form.get("system_id", ""))
    library = {line.id: line for line in _library(store)}
    if line_id not in library:
        raise HTTPException(404, f"No line {line_id} in the library.")
    if system_id not in store.state().get("system", {}):
        raise HTTPException(404, f"No system {system_id} in this inventory.")
    existing = store.state().get("register", {}).get(line_id)
    if existing is not None:
        refusal = (f"{line_id} is already in the register ({existing.get('status')}), adopted "
                   f"for {existing.get('system_id') or 'another system'}; a register ID is used "
                   "once.")
        return _propose_page(request, store, system_id, status_code=409, refusal=refusal)
    system = store.state()["system"][system_id]
    _, removed = screen_lines(system, list(library.values()))
    filtered_out = dict((line.id, reasons) for line, reasons in removed).get(line_id)
    reason = f"adopted from the library for {system_id}"
    if filtered_out:
        reason += f", although the filter removed it ({'; '.join(filtered_out)})"
    line = register_line_from_library(library[line_id], system_id)
    store.append(Event(entity="register", entity_id=line_id, new=line.to_dict(),
                       actor=request.app.state.actor, reason=reason))
    return RedirectResponse(f"/library/propose?system={system_id}&adopted={line_id}",
                            status_code=303)


@router.get("/library/{line_id}")
async def library_line(line_id: str, request: Request, store: Store = Depends(get_store)):
    line = next((line for line in _library(store) if line.id == line_id), None)
    if line is None:
        raise HTTPException(404, f"No line {line_id} in the library.")
    in_register = store.state().get("register", {}).get(line_id)
    return render(request, "library_line.html", "library", line=line,
                  l1_names=_l1_names(store), in_register=in_register)
