"""Register (SPEC.md 6.9; B.3; chapter 11): the grid, the line profile and the replay by date.

``/register?as_of=YYYY-MM-DD`` builds the same grid from the audit trail
replayed to the end of that day (UTC), which answers the auditor's question of
SPEC.md section 3. The profile shows every assessment, control and event on a
line with its date, person and reason. The owner and COSO category are set
here with a reason; a line is retired here with a reason and keeps its ID.
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse

from riskid.model import Event
from riskid.reconcile import library_lines
from riskid.register import COSO, grid_rows, retired_rows, signs, trail
from riskid.store import Store
from riskid.web import get_store, render

router = APIRouter()


def _taxonomy(store: Store) -> dict:
    return {t["l2_code"]: t["l2"] for t in store.taxonomy()}


@router.get("/register")
async def register(request: Request, as_of: str = "", store: Store = Depends(get_store)):
    stood = None
    if as_of:
        try:
            stood = date.fromisoformat(as_of).isoformat()
        except ValueError:
            raise HTTPException(422, "Give the date as YYYY-MM-DD.")
    state = store.replay(stood) if stood else store.state()
    rows = grid_rows(state, library_lines(store), _taxonomy(store))
    return render(request, "register.html", "register", rows=rows, as_of=stood,
                  retired=retired_rows(state), signs=signs(state, rows),
                  today=date.today().isoformat())


def _line(store: Store, line_id: str) -> dict:
    line = store.state().get("register", {}).get(line_id)
    if line is None:
        raise HTTPException(404, f"No line {line_id} in the register.")
    return line


def _profile(request, store, line_id, line, reasons=(), status_code=200):
    state = store.state()
    library = library_lines(store)
    row = next((r for r in grid_rows(state, library, _taxonomy(store)) if r["id"] == line_id), None)
    assessments = [(i, a) for i, a in sorted(state.get("assessment", {}).items()) if a["line_id"] == line_id]
    controls = [(i, c) for i, c in sorted(state.get("control", {}).items()) if c.get("line_id") == line_id]
    return render(request, "register_profile.html", "register", status_code=status_code,
                  line_id=line_id, line=line, row=row, reasons=list(reasons), coso=COSO,
                  title=library[line_id].title if line_id in library else line.get("definition"),
                  assessments=assessments, controls=controls,
                  disagreements=[(i, d) for i, d in sorted(state.get("disagreement", {}).items())
                                 if d.get("line_id") == line_id],
                  trail=trail(state, store.events(), line_id))


@router.get("/register/{line_id}")
async def profile(line_id: str, request: Request, store: Store = Depends(get_store)):
    return _profile(request, store, line_id, _line(store, line_id))


@router.post("/register/{line_id}")
async def edit(line_id: str, request: Request, store: Store = Depends(get_store)):
    # Read the form first: after the await, the line is read and written with no await between.
    form = {k: str(v).strip() for k, v in (await request.form()).items()}
    line = _line(store, line_id)
    reasons = []
    if "owner" in form and not form["owner"]:
        reasons.append("Owner: a named person, never a committee or a vendor (B.3 field 5).")
    if form.get("coso_category") and form["coso_category"] not in COSO:
        reasons.append("COSO category: strategic, operations, reporting or compliance (B.3 field 4).")
    if line.get("status") == "retired":
        reasons.append(f"{line_id} is retired; its record stands.")
    if reasons:
        return _profile(request, store, line_id, line, reasons, 422)
    why = form.get("change_reason") or "register edit"
    with store.transaction():
        for field in ("owner", "coso_category", "definition"):
            value = form.get(field) or None
            if field in form and value != line.get(field):
                store.append(Event(entity="register", entity_id=line_id, field=field, old=line.get(field),
                                   new=value, actor=request.app.state.actor, reason=why))
    return RedirectResponse(f"/register/{line_id}", status_code=303)


@router.post("/register/{line_id}/retire")
async def retire(line_id: str, request: Request, store: Store = Depends(get_store)):
    reason = str((await request.form()).get("reason", "")).strip()
    line = _line(store, line_id)
    if line.get("status") == "retired":
        raise HTTPException(409, f"{line_id} is already retired: {line.get('retired_reason')}")
    if not reason:
        return _profile(request, store, line_id, line,
                        ["Retire: give the reason; the line keeps its ID and its history."], 422)
    with store.transaction():
        store.retire(line_id, reason=reason, actor=request.app.state.actor)
    return RedirectResponse(f"/register/{line_id}", status_code=303)
