"""Workshop (SPEC.md 6.4; B.4, B.5; chapter 6): the facilitator's six stages and the participant view.

A workshop moves forward through the six stages of B.5. Each stage opens its
own input: pre-workshop lists at stage 1 (hidden from everyone until stage 2,
then shown anonymised), SWIFT answers from stage 3, emerging risks from stage
4, votes at stage 5, the gap review at stage 6. Closing records the voted
register lines as top-down candidates; emerging risks stay in the workshop's
taxonomy gap list. Every change is an event; a closed workshop takes no more changes.
"""

from __future__ import annotations

import hashlib
from datetime import date
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse

from riskid import importers
from riskid.model import Event, LibraryLine, Workshop
from riskid.propose import propose_lines, register_line_from_library
from riskid.store import Store
from riskid.web import get_store, render
from riskid.web.system_form import WHOLE_NUMBER
from riskid.workshop import (LINE_ID, SEATS, STAGES, candidates, check_answer, check_votes,
                             pre_list_items, ranking, seat_differences)

router = APIRouter()
SWIFT = importers.load_swift()


def _get(store: Store, ws_id: str) -> dict:
    ws = store.state().get("workshop", {}).get(ws_id)
    if ws is None:
        raise HTTPException(404, f"No workshop {ws_id}.")
    return ws


def _require(ws: dict, ws_id: str, stage_from: int, stage_to: int = 6, what: str = "this"):
    if ws["status"] != "open":
        raise HTTPException(409, f"{ws_id} is closed; its record no longer changes.")
    if not stage_from <= ws["stage"] <= stage_to:
        when = (f"stage {stage_from}" if stage_from == stage_to
                else f"stage {stage_from} onwards")
        raise HTTPException(409, f"{what} is taken at {when}; {ws_id} is at stage {ws['stage']}.")


def _change(request, store, ws_id, field, old, new, reason):
    store.append(Event(entity="workshop", entity_id=ws_id, field=field, old=old, new=new,
                       actor=request.app.state.actor, reason=reason))


def _mentions(lists: list, known: set) -> list:
    """(line, number of lists naming it), lines not on every list first (chapter 6)."""
    counts: dict = {}
    for items in lists:
        for line_id in {m for item in items for m in LINE_ID.findall(item) if m in known}:
            counts[line_id] = counts.get(line_id, 0) + 1
    return sorted(counts.items(), key=lambda kv: (kv[1] == len(lists), -kv[1], kv[0]))


def _participants(ws: dict) -> list:
    """The people in the room: seated and not marked absent."""
    return [s["person"] for s in ws["seats"] if s.get("person") and s.get("present", True)]


def _context(store: Store, ws_id: str, ws: dict) -> dict:
    """Everything the facilitator view and the record show."""
    library = {d["id"]: LibraryLine.from_dict(d) for d in store.library()}
    register = store.state().get("register", {})
    known = set(library) | set(register)
    found = candidates(ws, SWIFT, known)
    titles = {i: line.title for i, line in library.items()}
    titles.update({i: line.get("definition") for i, line in register.items() if i not in titles})
    titles.update({c["id"]: c["title"] for c in found if c["kind"] == "emerging"})
    systems = [store.state().get("system", {}).get(s, {"id": s}) for s in ws["system_ids"]]
    # Anonymised: shown in an order set by their content, not by who sent them first.
    lists = sorted((ws.get("pre_lists") or {}).values(),
                   key=lambda items: hashlib.sha256("\n".join(items).encode()).hexdigest())
    return {"ws_id": ws_id, "ws": ws, "systems": systems, "stages": STAGES, "swift": SWIFT,
            "answers": ws.get("swift_answers") or {}, "candidates": found, "titles": titles,
            "ranked": ranking(ws.get("votes")), "diffs": seat_differences(ws.get("votes"), ws["seats"]),
            "participants": _participants(ws),
            "lists": [(chr(ord("A") + i), items) for i, items in enumerate(lists)],
            "list_count": len(lists), "register": register, "mentions": _mentions(lists, known)}


def _page(request, store, ws_id, ws, reasons=(), status_code=200):
    return render(request, "workshop.html", "workshop", status_code=status_code,
                  reasons=list(reasons), **_context(store, ws_id, ws))


@router.get("/workshops")
async def workshops_list(request: Request, store: Store = Depends(get_store)):
    return _list_page(request, store)


def _list_page(request, store, reasons=(), values=None, status_code=200):
    systems = sorted(store.state().get("system", {}).values(), key=lambda s: s["id"])
    workshops = sorted(store.state().get("workshop", {}).items())
    return render(request, "workshops_list.html", "workshop", status_code=status_code,
                  systems=systems, workshops=workshops, seats=SEATS, reasons=list(reasons),
                  values=values or {"date": date.today().isoformat(), "vote_allowance": "5"})


@router.post("/workshops")
async def workshop_create(request: Request, store: Store = Depends(get_store)):
    form = await request.form()
    values = {k: str(v) for k, v in form.items()}
    system_ids = [str(s) for s in form.getlist("system_ids") if str(s)]
    known = store.state().get("system", {})
    reasons = []
    if not system_ids or any(s not in known for s in system_ids):
        reasons.append("Systems: choose at least one system from the inventory.")
    held = None
    try:
        held = date.fromisoformat(values.get("date", "").strip()).isoformat()
    except ValueError:
        reasons.append("Date: give it as YYYY-MM-DD.")
    facilitator = values.get("facilitator", "").strip()
    if not facilitator:
        reasons.append("Facilitator: name the person who runs the session (B.5).")
    allowance = values.get("vote_allowance", "").strip()
    if not WHOLE_NUMBER.fullmatch(allowance) or not 1 <= int(allowance) <= 20:
        reasons.append("Votes per participant: a whole number from 1 to 20 (chapter 6: five to ten).")
    seats = [{"role": seat["role"], "person": values.get(f"seat_{i}", "").strip(),
              "present": not values.get(f"seat_{i}_absent")}
             for i, seat in enumerate(SEATS, start=1) if values.get(f"seat_{i}", "").strip()]
    people = [s["person"] for s in seats]
    if len(people) != len(set(people)):
        reasons.append("Seats: each person takes one seat, so their list and votes stay their own.")
    if reasons:
        return _list_page(request, store, reasons, values, status_code=422)
    ws_id = store.next_id("workshop", "WS")
    ws = Workshop(system_ids=system_ids, date=held, facilitator=facilitator, seats=seats,
                  vote_allowance=int(allowance))
    store.append(Event(entity="workshop", entity_id=ws_id, new=ws.to_dict(),
                       actor=request.app.state.actor, reason="workshop opened"))
    return RedirectResponse(f"/workshops/{ws_id}", status_code=303)


@router.get("/workshops/{ws_id}")
async def workshop_view(ws_id: str, request: Request, store: Store = Depends(get_store)):
    return _page(request, store, ws_id, _get(store, ws_id))


@router.get("/workshops/{ws_id}/record")
async def workshop_record(ws_id: str, request: Request, store: Store = Depends(get_store)):
    ws = _get(store, ws_id)
    return render(request, "workshop_record.html", "workshop", **_context(store, ws_id, ws))


@router.post("/workshops/{ws_id}/advance")
async def workshop_advance(ws_id: str, request: Request, store: Store = Depends(get_store)):
    ws = _get(store, ws_id)
    _require(ws, ws_id, 1, 5, "Moving to the next stage")
    entering = STAGES[ws["stage"]]          # STAGES is 0-indexed, so this is stage + 1
    _change(request, store, ws_id, "stage", ws["stage"], entering["n"],
            f"stage {entering['n']}: {entering['name']}")
    return RedirectResponse(f"/workshops/{ws_id}#stage-{ws['stage'] + 1}", status_code=303)


@router.post("/workshops/{ws_id}/swift/{prompt_id}")
async def workshop_answer(ws_id: str, prompt_id: int, request: Request,
                          store: Store = Depends(get_store)):
    ws = _get(store, ws_id)
    if not 1 <= prompt_id <= len(SWIFT):
        raise HTTPException(404, f"No SWIFT prompt {prompt_id}.")
    _require(ws, ws_id, 3, what="A SWIFT answer")
    form = await request.form()
    status, control, evidence, note = (str(form.get(k, "")).strip()
                                       for k in ("status", "control", "evidence", "note"))
    reasons = check_answer(status, control, evidence)
    if reasons:
        return _page(request, store, ws_id, ws, [f"Prompt {prompt_id}: {r}" for r in reasons], 422)
    answers = dict(ws.get("swift_answers") or {})
    answers[str(prompt_id)] = {"status": status, "control": control or None,
                               "evidence": evidence or None, "note": note or None}
    _change(request, store, ws_id, "swift_answers", ws.get("swift_answers"), answers,
            f"SWIFT prompt {prompt_id}: {status}")
    return RedirectResponse(f"/workshops/{ws_id}#prompt-{prompt_id}", status_code=303)


@router.post("/workshops/{ws_id}/emerging")
async def workshop_emerging(ws_id: str, request: Request, store: Store = Depends(get_store)):
    ws = _get(store, ws_id)
    _require(ws, ws_id, 4, what="An emerging risk")
    form = await request.form()
    title, note = str(form.get("title", "")).strip(), str(form.get("note", "")).strip()
    if not title:
        return _page(request, store, ws_id, ws, ["Emerging risk: give it a title."], 422)
    risks = list(ws.get("emerging_risks") or []) + [{"title": title, "note": note or None}]
    _change(request, store, ws_id, "emerging_risks", ws.get("emerging_risks"), risks,
            f"emerging risk: {title}")
    return RedirectResponse(f"/workshops/{ws_id}#stage-4", status_code=303)


@router.post("/workshops/{ws_id}/attendance")
async def workshop_attendance(ws_id: str, request: Request, store: Store = Depends(get_store)):
    """Stage 1 takes the attendance: a seat not ticked present is absent."""
    ws = _get(store, ws_id)
    _require(ws, ws_id, 1, 1, "Attendance")
    form = await request.form()
    seats = [dict(seat, present=bool(form.get(f"present_{i}"))) for i, seat in enumerate(ws["seats"])]
    _change(request, store, ws_id, "seats", ws["seats"], seats, "attendance taken")
    return RedirectResponse(f"/workshops/{ws_id}#stage-1", status_code=303)


@router.post("/workshops/{ws_id}/gap")
async def workshop_gap(ws_id: str, request: Request, store: Store = Depends(get_store)):
    ws = _get(store, ws_id)
    _require(ws, ws_id, 6, what="The gap review")
    form = await request.form()
    notes = str(form.get("gap_review", "")).strip() or None
    _change(request, store, ws_id, "gap_review", ws.get("gap_review"), notes, "gap review notes")
    return RedirectResponse(f"/workshops/{ws_id}#stage-6", status_code=303)


@router.post("/workshops/{ws_id}/close")
async def workshop_close(ws_id: str, request: Request, store: Store = Depends(get_store)):
    """Close at stage 6: voted register lines become top-down candidates."""
    ws = _get(store, ws_id)
    _require(ws, ws_id, 6, what="Closing")
    library = {d["id"]: LibraryLine.from_dict(d) for d in store.library()}
    register = store.state().get("register", {})
    systems = store.state().get("system", {})
    with store.transaction():
        for entry in ranking(ws.get("votes")):
            line_id = entry["id"]
            if line_id in library and line_id not in register:
                # The first system in scope that the line was proposed for, else the first.
                proposed_for = [s for s in ws["system_ids"] if s in systems and line_id in
                                {line.id for line, _ in propose_lines(systems[s], list(library.values()))}]
                line = register_line_from_library(library[line_id], (proposed_for or ws["system_ids"])[0])
                line.source = "top-down"
                store.append(Event(entity="register", entity_id=line_id, new=line.to_dict(),
                                   actor=request.app.state.actor,
                                   reason=f"top-down candidate from workshop {ws_id} "
                                          f"({entry['voters']} voters, {entry['votes']} votes)"))
        _change(request, store, ws_id, "status", "open", "closed", "workshop closed")
    return RedirectResponse(f"/workshops/{ws_id}/record", status_code=303)


@router.get("/workshops/{ws_id}/participant")
async def participant_view(ws_id: str, request: Request, participant: str = "",
                           store: Store = Depends(get_store)):
    ws = _get(store, ws_id)
    return _participant_page(request, store, ws_id, ws, participant)


def _participant_page(request, store, ws_id, ws, participant, reasons=(), status_code=200):
    context = _context(store, ws_id, ws)
    return render(request, "workshop_participant.html", "workshop", status_code=status_code,
                  participant=participant if participant in context["participants"] else "",
                  submitted=participant in (ws.get("pre_lists") or {}), reasons=list(reasons),
                  **{k: context[k] for k in ("ws_id", "ws", "participants", "candidates", "titles")})


@router.post("/workshops/{ws_id}/participant")
async def participant_entry(ws_id: str, request: Request, store: Store = Depends(get_store)):
    ws = _get(store, ws_id)
    form = await request.form()
    participant = str(form.get("participant", "")).strip()
    if participant not in _participants(ws):
        return _participant_page(request, store, ws_id, ws, "",
                                 ["Choose your seat's name from the list (B.5)."], 422)
    if "pre_list" in form:
        _require(ws, ws_id, 1, 1, "A pre-workshop list")
        items, reasons = pre_list_items(str(form["pre_list"]))
        if reasons:
            return _participant_page(request, store, ws_id, ws, participant, reasons, 422)
        lists = dict(ws.get("pre_lists") or {})
        lists[participant] = items
        _change(request, store, ws_id, "pre_lists", ws.get("pre_lists"), lists,
                f"pre-workshop list from {participant}")
    else:
        _require(ws, ws_id, 5, 5, "Votes")
        allocation, reasons = {}, []
        for key, value in form.items():
            if key.startswith("vote_") and str(value).strip():
                if WHOLE_NUMBER.fullmatch(str(value).strip()):
                    if int(value):
                        allocation[key[5:]] = int(value)
                else:
                    reasons.append(f"{key[5:]}: votes are whole numbers.")
        ids = {c["id"] for c in _context(store, ws_id, ws)["candidates"]}
        reasons += check_votes(allocation, ws["vote_allowance"], ids)
        if reasons:
            return _participant_page(request, store, ws_id, ws, participant, reasons, 422)
        votes = dict(ws.get("votes") or {})
        votes[participant] = allocation
        _change(request, store, ws_id, "votes", ws.get("votes"), votes, f"votes from {participant}")
    return RedirectResponse(f"/workshops/{ws_id}/participant?participant={quote(participant)}",
                            status_code=303)
