"""Interact (SPEC.md 6.8; chapter 10): the interaction matrix, bow-ties and concentration.

A link is one entity per ordered pair (``FROM>TO``), re-recorded when the
judgement changes; every judgement stays in the audit trail. A bow-tie
(BT-nnn) keeps its causes and preventive controls row by row on one side of
the event, and its recovery controls and consequences on the other.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse

from riskid.assess import latest_assessments
from riskid.interact import KINDS, LETTER, axis_lines, candidate_links, concentration, nodes
from riskid.model import BowTie, Event, Interaction
from riskid.reconcile import library_lines
from riskid.store import Store
from riskid.web import get_store, render

router = APIRouter()
ROWS = 4


def _live(state: dict) -> dict:
    return {i: line for i, line in state.get("register", {}).items() if line.get("status") != "retired"}


def _titles(store: Store, state: dict) -> dict:
    library = library_lines(store)
    titles = {i: line.title for i, line in library.items()}
    titles.update({i: line.get("definition") for i, line in state.get("register", {}).items()
                   if i not in titles})
    return titles


def _page(request, store, reasons=(), status_code=200, values=None):
    state = store.state()
    live = _live(state)
    interactions = state.get("interaction", {})
    material = {i for i, (_, a) in latest_assessments(state).items() if a.get("material")}
    propagation, vulnerable = nodes(interactions)
    return render(request, "interact.html", "interact", status_code=status_code, reasons=list(reasons),
                  axis=axis_lines(material, interactions, set(live)), material=material,
                  cells={f"{l['from_line']}>{l['to_line']}": l for l in interactions.values()},
                  letter=LETTER, kinds=KINDS, live=sorted(live), titles=_titles(store, state),
                  propagation=propagation, vulnerable=vulnerable,
                  candidates=candidate_links(state.get("register", {}), interactions),
                  bowties=sorted(state.get("bowtie", {}).items()),
                  conc=concentration(state.get("system", {}), state.get("register", {})),
                  rows=range(1, ROWS + 1), values=values or {})


@router.get("/interact")
async def interact(request: Request, store: Store = Depends(get_store)):
    return _page(request, store)


@router.post("/interact/links")
async def link_record(request: Request, store: Store = Depends(get_store)):
    form = {k: str(v).strip() for k, v in (await request.form()).items()}
    live = _live(store.state())
    a, b = form.get("from_line", ""), form.get("to_line", "")
    reasons = []
    if a not in live or b not in live:
        reasons.append("Link: both lines must be live lines in the register.")
    elif a == b:
        reasons.append("Link: a line does not trigger, amplify or share a driver with itself.")
    if form.get("kind") not in KINDS:
        reasons.append("Link: triggers, amplifies, shared driver, or none.")
    if form.get("kind") in LETTER and not form.get("mechanism"):
        reasons.append("Link: state the mechanism; a cell with no mechanism stays blank (chapter 10).")
    if reasons:
        return _page(request, store, reasons, 422)
    link = Interaction(from_line=a, to_line=b, kind=form["kind"], mechanism=form.get("mechanism") or None,
                       delay=form.get("delay") or None, note=form.get("note") or None)
    store.append(Event(entity="interaction", entity_id=f"{a}>{b}", new=link.to_dict(),
                       actor=request.app.state.actor, reason=f"{a} {form['kind']} {b}"))
    return RedirectResponse("/interact#matrix", status_code=303)


def _parse_bowtie(form: dict, live: dict) -> tuple[BowTie, list]:
    reasons = []
    if form.get("line_id") not in live:
        reasons.append("Bow-tie: choose the live register line at its centre.")
    if not form.get("event"):
        reasons.append("Bow-tie: name the event at the centre.")
    if not form.get("owner"):
        reasons.append("Bow-tie: one owner, the head of the process the system sits in (chapter 10).")
    left = [(form.get(f"cause_{i}", ""), form.get(f"preventive_{i}", "")) for i in range(1, ROWS + 1)]
    right = [(form.get(f"consequence_{i}", ""), form.get(f"recovery_{i}", "")) for i in range(1, ROWS + 1)]
    left = [row for row in left if any(row)]
    right = [row for row in right if any(row)]
    if not left or any(not cause for cause, _ in left):
        reasons.append("Bow-tie: each row on the left names its cause, and there is at least one.")
    if not right or any(not consequence for consequence, _ in right):
        reasons.append("Bow-tie: each row on the right names its consequence, and there is at least one.")
    bowtie = BowTie(line_id=form.get("line_id"), event=form.get("event"), owner=form.get("owner"),
                    causes=[c for c, _ in left], preventive_controls=[p for _, p in left],
                    consequences=[c for c, _ in right], recovery_controls=[r for _, r in right],
                    escalation_factors=[x.strip() for x in form.get("escalation_factors", "").splitlines()
                                        if x.strip()])
    return bowtie, reasons


async def _save_bowtie(request, store, bt_id=None):
    form = {k: str(v).strip() for k, v in (await request.form()).items()}
    bowtie, reasons = _parse_bowtie(form, _live(store.state()))
    if reasons:
        return _page(request, store, reasons, 422, form)
    action = "updated" if bt_id else "created"
    bt_id = bt_id or store.next_id("bowtie", "BT")
    store.append(Event(entity="bowtie", entity_id=bt_id, new=bowtie.to_dict(),
                       actor=request.app.state.actor, reason=f"bow-tie {action} for {bowtie.line_id}"))
    return RedirectResponse(f"/interact/bowties/{bt_id}", status_code=303)


@router.post("/interact/bowties")
async def bowtie_create(request: Request, store: Store = Depends(get_store)):
    return await _save_bowtie(request, store)


@router.get("/interact/bowties/{bt_id}")
async def bowtie_view(bt_id: str, request: Request, store: Store = Depends(get_store)):
    bowtie = store.state().get("bowtie", {}).get(bt_id)
    if bowtie is None:
        raise HTTPException(404, f"No bow-tie {bt_id}.")
    values = {"line_id": bowtie["line_id"], "event": bowtie["event"], "owner": bowtie.get("owner"),
              "escalation_factors": "\n".join(bowtie.get("escalation_factors") or [])}
    for i, (c, p) in enumerate(zip(bowtie["causes"], bowtie["preventive_controls"]), start=1):
        values.update({f"cause_{i}": c, f"preventive_{i}": p})
    for i, (c, r) in enumerate(zip(bowtie["consequences"], bowtie["recovery_controls"]), start=1):
        values.update({f"consequence_{i}": c, f"recovery_{i}": r})
    state = store.state()
    return render(request, "bowtie.html", "interact", bt_id=bt_id, bowtie=bowtie, values=values,
                  live=sorted(_live(state)), titles=_titles(store, state), rows=range(1, ROWS + 1))


@router.post("/interact/bowties/{bt_id}")
async def bowtie_update(bt_id: str, request: Request, store: Store = Depends(get_store)):
    if bt_id not in store.state().get("bowtie", {}):
        raise HTTPException(404, f"No bow-tie {bt_id}.")
    return await _save_bowtie(request, store, bt_id)
