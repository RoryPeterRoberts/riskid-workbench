"""Reconcile (SPEC.md 6.6; chapter 8): the five steps on one screen, and the disagreement log.

Resolving applies the disposition to the register in the same transaction:
"add" makes the line active (adopting a blind spot from the library first),
"merge" retires it into the line named, "escalate" and "local" make it
active, "not applicable" retires it; a blind spot closed as not applicable
keeps its recorded reason and stays out of the register. A disagreement
resolved by any disposition is closed.
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse

from riskid.model import Disagreement, Event, Reconciliation, Resolution
from riskid.propose import register_line_from_library
from riskid.reconcile import (DIMENSIONS, DISPOSITION_KEYS, DISPOSITIONS, DONE, blind_spots,
                              bottom_up_entries, gaps, library_lines, match_table, top_down_entries)
from riskid.store import Store
from riskid.web import get_store, render
from riskid.web.system_form import WHOLE_NUMBER
from riskid.workshop import seat_differences

router = APIRouter()


def _context(store: Store) -> dict:
    state = store.state()
    library = library_lines(store)
    top_down, bottom_up = top_down_entries(state, library), bottom_up_entries(state)
    resolutions = state.get("resolution", {})
    found = gaps(state, top_down, bottom_up)
    spots = blind_spots(state, library)
    agenda = [{"ws_id": ws_id, **d} for ws_id, ws in sorted(state.get("workshop", {}).items())
              for d in seat_differences(ws.get("votes"), ws.get("seats") or [])]
    titles = {i: line.title for i, line in library.items()}
    titles.update({i: line.get("definition") for i, line in state.get("register", {}).items()
                   if i not in titles})
    open_gaps = [g for g in found + spots if g["subject"] not in resolutions]
    disagreements = sorted(state.get("disagreement", {}).items())
    register = sorted(state.get("register", {}).items())
    tracks = {}
    for e in top_down:
        tracks.setdefault(e["line_id"], set()).add("top-down")
    for e in bottom_up:
        tracks.setdefault(e["line_id"], set()).add("bottom-up")
    for row in match_table(top_down, bottom_up):
        for bu in row["matched"]:
            tracks.setdefault(row["line_id"], set()).add("bottom-up")
            tracks.setdefault(bu["line_id"], set()).add("top-down")
    return {"matches": match_table(top_down, bottom_up), "gaps": found, "blind_spots": spots,
            "agenda": agenda, "disagreements": disagreements, "resolutions": resolutions,
            "open_gaps": open_gaps, "titles": titles, "register": register, "tracks": tracks,
            "dispositions": DISPOSITIONS, "done": DONE, "dimensions": DIMENSIONS,
            "runs": sorted(state.get("reconciliation", {}).items()),
            "counts": {"lines": sum(1 for _, l in register if l.get("status") != "retired"),
                       "open_gaps": len(open_gaps),
                       "open_disagreements": sum(1 for _, d in disagreements if d["status"] == "open")}}


def _page(request, store, reasons=(), status_code=200):
    return render(request, "reconcile.html", "reconcile", status_code=status_code,
                  reasons=list(reasons), **_context(store))


@router.get("/reconcile")
async def reconcile(request: Request, store: Store = Depends(get_store)):
    return _page(request, store)


@router.post("/reconcile/disagreements")
async def disagreement_add(request: Request, store: Store = Depends(get_store)):
    form = {k: str(v).strip() for k, v in (await request.form()).items()}
    state = store.state()
    reasons = []
    if form.get("line_id") not in state.get("register", {}):
        reasons.append("Disagreement: name a line in the register.")
    if not WHOLE_NUMBER.fullmatch(form.get("minority_score", "")) or not 1 <= int(form["minority_score"]) <= 5:
        reasons.append("Disagreement: the minority score is a whole number from 1 to 5.")
    majority = form.get("majority_score", "")
    if majority and (not WHOLE_NUMBER.fullmatch(majority) or not 1 <= int(majority) <= 5):
        reasons.append("Disagreement: the majority score, if given, is from 1 to 5.")
    if form.get("dimension") not in DIMENSIONS:
        reasons.append("Disagreement: choose the dimension the views differ on.")
    if not form.get("holder"):
        reasons.append("Disagreement: name who holds the minority view.")
    if reasons:
        return _page(request, store, reasons, 422)
    dl_id = store.next_id("disagreement", "DL")
    entry = Disagreement(line_id=form["line_id"], raised_in=form.get("raised_in") or "reconciliation",
                         holder=form["holder"], majority_score=int(majority) if majority else None,
                         minority_score=int(form["minority_score"]), dimension=form["dimension"],
                         evidence=form.get("evidence") or None)
    store.append(Event(entity="disagreement", entity_id=dl_id, new=entry.to_dict(),
                       actor=request.app.state.actor, reason="disagreement logged"))
    return RedirectResponse("/reconcile#challenge", status_code=303)


@router.post("/reconcile/resolve")
async def resolve(request: Request, store: Store = Depends(get_store)):
    form = {k: str(v).strip() for k, v in (await request.form()).items()}
    state = store.state()
    register, library = state.get("register", {}), library_lines(store)
    subject, disposition = form.get("subject", ""), form.get("disposition", "")
    reason, target = form.get("reason", ""), form.get("target", "")
    is_disagreement = subject in state.get("disagreement", {})
    reasons = []
    if not (is_disagreement or subject in register or subject in library):
        reasons.append(f"{subject or 'The subject'} is not a line or a disagreement.")
    if disposition not in DISPOSITION_KEYS:
        reasons.append("Choose one of the five dispositions (chapter 8, step 4).")
    if not reason:
        reasons.append("Resolve: give the reason; it is recorded with your name and the date.")
    if disposition == "merge" and not is_disagreement and (target not in register or target == subject):
        reasons.append("Merge: name the line it merges into, which must be another line in the register.")
    spot_systems = {b["subject"]: b["systems"] for b in blind_spots(state, library)}
    system_id = form.get("system_id") or (spot_systems.get(subject) or [None])[0]
    if disposition == "add" and subject not in register and not is_disagreement and (
            system_id not in state.get("system", {})):
        reasons.append("Add: choose the system the line is for.")
    if subject in register and register[subject].get("status") == "retired":
        reasons.append(f"{subject} is retired; its record stands and it is not resolved again.")
    if is_disagreement and state["disagreement"][subject].get("status") != "open":
        reasons.append(f"{subject} is already resolved.")
    if reasons:
        return _page(request, store, reasons, 422)
    actor = request.app.state.actor
    with store.transaction():
        if is_disagreement:
            store.append(Event(entity="disagreement", entity_id=subject, field="status", old="open",
                               new="resolved", actor=actor, reason=f"{DONE[disposition]}: {reason}"))
        elif disposition == "add" and subject not in register:
            line = register_line_from_library(library[subject], system_id)
            line.status = "active"
            store.append(Event(entity="register", entity_id=subject, new=line.to_dict(), actor=actor,
                               reason=f"reconciliation: added to the register: {reason}"))
        elif subject in register and disposition in ("merge", "not applicable"):
            why = f"merged into {target}: {reason}" if disposition == "merge" else reason
            store.retire(subject, reason=why, actor=actor)
        elif subject in register and register[subject].get("status") == "candidate":
            store.append(Event(entity="register", entity_id=subject, field="status", old="candidate",
                               new="active", actor=actor, reason=f"reconciliation: {DONE[disposition]}: {reason}"))
        store.append(Event(entity="resolution", entity_id=subject, actor=actor, reason=reason,
                           new=Resolution(subject=subject, disposition=disposition, reason=reason,
                                          target=target or None, decided_by=actor,
                                          date=date.today().isoformat()).to_dict()))
    return RedirectResponse("/reconcile#resolve", status_code=303)


@router.post("/reconcile/record")
async def record_pass(request: Request, store: Store = Depends(get_store)):
    form = {k: str(v).strip() for k, v in (await request.form()).items()}
    present = [p.strip() for p in form.get("present", "").split(",") if p.strip()]
    reasons = []
    if not form.get("signed_by"):
        reasons.append("Record: the executive accountable for AI risk signs the reconciled register.")
    if not present:
        reasons.append("Record: name those present.")
    if reasons:
        return _page(request, store, reasons, 422)
    run_id = store.next_id("reconciliation", "RC")
    run = Reconciliation(date=date.today().isoformat(), present=present, signed_by=form["signed_by"],
                         counts=_context(store)["counts"])
    store.append(Event(entity="reconciliation", entity_id=run_id, new=run.to_dict(),
                       actor=request.app.state.actor, reason=f"reconciled register signed by {run.signed_by}"))
    return RedirectResponse("/reconcile#record", status_code=303)
