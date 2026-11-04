"""Cycle (SPEC.md 6.11; chapter 13; B.8): indicators, triggers, the calendar and the checklist runner.

An indicator (KRI-nnn) watches one register line, with amber and red
thresholds, the direction that is worse and the person who reads it; every
reading is kept in its history. A reading that turns red logs a trigger,
because red "prompts a decision on an event-driven update" (chapter 13).

A trigger (TR-nnn) records what happened and the live lines it touches, and
brings each one's next review forward to its date (SPEC.md 5.7). The decision
on its significance is recorded with the reason and the person.

A run (CR-nnn) works through the 18 steps of B.8 with evidence, an owner and a
date per step. It is signed only when every step has evidence and is done.
The signature fixes the next run, and each live line's next review becomes the
earlier of that date and any trigger still awaiting its decision. A signed run
is closed, and its quarterly pack holds the register as it stood when signed.
"""

from __future__ import annotations

import math
import re
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse

from riskid import cycle, importers, rules
from riskid.documents import packs
from riskid.documents.provenance import provenance
from riskid.model import CycleRun, Event, Indicator, Trigger
from riskid.reconcile import library_lines
from riskid.store import Store
from riskid.web import get_store, render
from riskid.web.routes_documents import send_document

router = APIRouter()
RUN_KINDS = ("quarterly", "annual")
SIGNIFICANCE = ("significant", "not")
NUMBER = re.compile(r"-?[0-9]+(?:\.[0-9]+)?")


def _live(state: dict) -> dict:
    return {i: line for i, line in state.get("register", {}).items() if line.get("status") != "retired"}


def _number(text):
    if not text or not NUMBER.fullmatch(text):
        return None
    value = float(text)
    if not math.isfinite(value):         # a long enough string of digits overflows to infinity
        return None
    return int(value) if value.is_integer() else value


def _date(text):
    try:
        return date.fromisoformat(text or "").isoformat()
    except ValueError:
        return None


async def _form(request: Request) -> dict:
    return {k: str(v).strip() for k, v in (await request.form()).items()}


def _calendar(today: str) -> list:
    out = []
    for e in importers.load_calendar():
        when = e["applies_from"]
        status = ("" if when is None else "in force" if when <= today
                  else f"in {(date.fromisoformat(when) - date.fromisoformat(today)).days} days")
        out.append(dict(e, status=status))
    return out


def _page(request, store, reasons=(), status_code=200, values=None):
    state = store.state()
    live = _live(state)
    today = date.today().isoformat()
    presets = importers.load_indicators()
    indicators = [(k, kri, cycle.status(kri)) for k, kri in sorted(state.get("indicator", {}).items())]
    due = sorted((line["next_review"], i) for i, line in live.items() if line.get("next_review"))
    return render(request, "cycle.html", "cycle", status_code=status_code, reasons=list(reasons),
                  values=values or {}, live=sorted(live), indicators=indicators, directions=cycle.DIRECTIONS,
                  presets=presets, suggested=[p for p in presets if set(p["lines"]) & set(live)],
                  triggers=sorted(state.get("trigger", {}).items(), reverse=True), significance=SIGNIFICANCE,
                  calendar=_calendar(today), today=today, due=due[:12], undated=len(live) - len(due),
                  runs=sorted(state.get("cycle", {}).items(), reverse=True), run_kinds=RUN_KINDS)


@router.get("/cycle")
async def cycle_page(request: Request, store: Store = Depends(get_store)):
    return _page(request, store)


# -- indicators -------------------------------------------------------------

@router.post("/cycle/indicators")
async def indicator_create(request: Request, store: Store = Depends(get_store)):
    form = await _form(request)
    reasons = []
    if form.get("line_id") not in _live(store.state()):
        reasons.append("Indicator: choose the live register line it watches.")
    if not form.get("name"):
        reasons.append("Indicator: name what is measured.")
    if not form.get("read_by"):
        reasons.append("Indicator: name the person who reads it; an indicator with no owner is decoration "
                       "(chapter 13).")
    amber, red = _number(form.get("amber")), _number(form.get("red"))
    if amber is None or red is None:
        reasons.append("Indicator: give the amber and red thresholds as numbers.")
    else:
        reasons += cycle.check_thresholds(amber, red, form.get("direction"))
    if reasons:
        return _page(request, store, reasons, 422, form)
    kri_id = store.next_id("indicator", "KRI")
    kri = Indicator(line_id=form["line_id"], name=form["name"], unit=form.get("unit") or None,
                    thresholds={"amber": amber, "red": red, "direction": form["direction"]},
                    read_by=form["read_by"])
    store.append(Event(entity="indicator", entity_id=kri_id, new=kri.to_dict(), actor=request.app.state.actor,
                       reason=f"indicator set on {kri.line_id}"))
    return RedirectResponse("/cycle#indicators", status_code=303)


@router.post("/cycle/indicators/{kri_id}/value")
async def indicator_reading(kri_id: str, request: Request, store: Store = Depends(get_store)):
    form = await _form(request)
    kri = store.state().get("indicator", {}).get(kri_id)
    if kri is None:
        raise HTTPException(404, f"No indicator {kri_id}.")
    value, read_on = _number(form.get("value")), _date(form.get("date"))
    reasons = []
    if value is None:
        reasons.append(f"Reading for {kri_id}: give the value as a number.")
    if read_on is None:
        reasons.append(f"Reading for {kri_id}: give the date as YYYY-MM-DD.")
    if reasons:
        return _page(request, store, reasons, 422)
    actor = request.app.state.actor
    # The current value is the latest-dated reading; a reading entered late does not replace it.
    history = sorted([*(kri.get("history") or []), {"date": read_on, "value": value, "by": actor}],
                     key=lambda r: r["date"])
    before, after = cycle.status(kri), cycle.status(dict(kri, current_value=history[-1]["value"]))
    with store.transaction():
        for field, new in (("history", history), ("current_value", history[-1]["value"])):
            store.append(Event(entity="indicator", entity_id=kri_id, field=field, old=kri.get(field), new=new,
                               actor=actor, reason=f"reading {value} on {read_on}"))
        if after == "red" and before != "red":
            t = kri["thresholds"]
            _log_trigger(store, read_on, f"indicator {kri_id}",
                         f"{kri_id} {kri['name']} on {kri['line_id']} read {value}{kri.get('unit') or ''} "
                         f"on {read_on}: red (red at {t['red']}, {t['direction']}).", actor)
    return RedirectResponse("/cycle#indicators", status_code=303)


# -- triggers ---------------------------------------------------------------

def _log_trigger(store: Store, when: str, source: str, text: str, actor: str) -> str:
    """Record a trigger and bring the next review of each line it touches forward to its date."""
    state = store.state()
    touched = cycle.touched_lines(text, state, importers.load_indicators())
    tr_id = store.next_id("trigger", "TR")
    register = state.get("register", {})
    changes = []
    with store.transaction():
        for t in touched:
            old = register[t["line_id"]].get("next_review")
            new = rules.next_review(old, when)
            if new != old:
                store.append(Event(entity="register", entity_id=t["line_id"], field="next_review", old=old,
                                   new=new, actor=actor, reason=f"event-driven update opened by {tr_id}"))
                changes.append({"line_id": t["line_id"], "field": "next_review", "old": old, "new": new})
        trigger = Trigger(date=when, source=source, text=text, lines_touched=touched, resulting_changes=changes)
        store.append(Event(entity="trigger", entity_id=tr_id, new=trigger.to_dict(), actor=actor,
                           reason=f"trigger logged from {source}"))
    return tr_id


@router.post("/cycle/triggers")
async def trigger_create(request: Request, store: Store = Depends(get_store)):
    form = await _form(request)
    when = _date(form.get("date"))
    reasons = []
    if when is None:
        reasons.append("Trigger: give the date it happened as YYYY-MM-DD.")
    if not form.get("source"):
        reasons.append("Trigger: say where it came from: a supplier, an incident, guidance or law, a new use, a date.")
    if not form.get("text"):
        reasons.append("Trigger: describe what happened.")
    if reasons:
        return _page(request, store, reasons, 422, form)
    tr_id = _log_trigger(store, when, form["source"], form["text"], request.app.state.actor)
    return RedirectResponse(f"/cycle#{tr_id}", status_code=303)


@router.post("/cycle/triggers/{tr_id}/decision")
async def trigger_decision(tr_id: str, request: Request, store: Store = Depends(get_store)):
    form = await _form(request)
    trigger = store.state().get("trigger", {}).get(tr_id)
    if trigger is None:
        raise HTTPException(404, f"No trigger {tr_id}.")
    reasons = []
    if form.get("significance") not in SIGNIFICANCE:
        reasons.append(f"{tr_id}: significant or not; when in doubt, treat it as significant until a regression "
                       "run shows otherwise (chapter 13).")
    if not form.get("decision"):
        reasons.append(f"{tr_id}: record the reason and what follows from it.")
    if reasons:
        return _page(request, store, reasons, 422)
    actor = request.app.state.actor
    with store.transaction():
        for field, new in (("significance", form["significance"]), ("decision", form["decision"]),
                           ("decided_by", actor)):
            store.append(Event(entity="trigger", entity_id=tr_id, field=field, old=trigger.get(field), new=new,
                               actor=actor, reason=f"significance decision on {tr_id}"))
    return RedirectResponse(f"/cycle#{tr_id}", status_code=303)


# -- runs: the B.8 checklist and sign-off ---------------------------------------

def _run(state: dict, run_id: str) -> dict:
    run = state.get("cycle", {}).get(run_id)
    if run is None:
        raise HTTPException(404, f"No run {run_id}.")
    return run


def _window(events: list, run_id: str) -> tuple:
    """The period a run covers: (the previous run's signing, this run's signing, the events between).

    A signing is the run's ``signed_date`` event, the last of its sign-off, so
    the event sequence bounds the period exactly; the signings are ``None``
    when there is no earlier signed run, or this one is open.
    """
    signed = {e["entity_id"]: e for e in events if e["entity"] == "cycle" and e["field"] == "signed_date"}
    this = signed.get(run_id)
    earlier = [e for r, e in signed.items() if r != run_id and (this is None or e["seq"] < this["seq"])]
    previous = max(earlier, key=lambda e: e["seq"]) if earlier else None
    covered = [e for e in events if (previous is None or e["seq"] > previous["seq"])
               and (this is None or e["seq"] <= this["seq"])]
    return previous, this, covered


def _run_page(request, store, run_id: str, reasons=(), status_code=200):
    state = store.state()
    run = _run(state, run_id)
    previous, _, covered = _window(store.events(), run_id)
    since = previous["ts"] if previous else None
    steps = importers.load_checklist()
    return render(request, "cycle_run.html", "cycle", status_code=status_code, reasons=list(reasons),
                  run_id=run_id, run=run, steps=steps, recorded=run.get("steps") or {},
                  findings=cycle.step_findings(state, run["date"], since, covered),
                  missing=cycle.missing_evidence(run, steps), since=since)


@router.post("/cycle/runs")
async def run_create(request: Request, store: Store = Depends(get_store)):
    form = await _form(request)
    when = _date(form.get("date"))
    reasons = []
    if form.get("kind") not in RUN_KINDS:
        reasons.append("Run: quarterly or annual; both work through the 18 steps of B.8.")
    if when is None:
        reasons.append("Run: give its date as YYYY-MM-DD.")
    if reasons:
        return _page(request, store, reasons, 422, form)
    run_id = store.next_id("cycle", "CR")
    store.append(Event(entity="cycle", entity_id=run_id, new=CycleRun(kind=form["kind"], date=when).to_dict(),
                       actor=request.app.state.actor, reason=f"{form['kind']} run opened"))
    return RedirectResponse(f"/cycle/runs/{run_id}", status_code=303)


@router.get("/cycle/runs/{run_id}")
async def run_view(run_id: str, request: Request, store: Store = Depends(get_store)):
    return _run_page(request, store, run_id)


@router.post("/cycle/runs/{run_id}/steps/{n}")
async def run_step(run_id: str, n: int, request: Request, store: Store = Depends(get_store)):
    form = await _form(request)
    run = _run(store.state(), run_id)
    if run.get("signed_date"):
        raise HTTPException(409, f"{run_id} is signed and closed; open a new run.")
    if n not in {s["n"] for s in importers.load_checklist()}:
        raise HTTPException(404, "B.8 has steps 1 to 18.")
    done_on = _date(form.get("date")) if form.get("date") else date.today().isoformat()
    if done_on is None:
        return _run_page(request, store, run_id, [f"Step {n}: give the date as YYYY-MM-DD."], 422)
    steps = dict(run.get("steps") or {})
    steps[str(n)] = {"done": form.get("done") == "on", "evidence": form.get("evidence") or None,
                     "owner": form.get("owner") or None, "date": done_on}
    store.append(Event(entity="cycle", entity_id=run_id, field="steps", old=run.get("steps"), new=steps,
                       actor=request.app.state.actor, reason=f"step {n} recorded"))
    return RedirectResponse(f"/cycle/runs/{run_id}#step-{n}", status_code=303)


@router.post("/cycle/runs/{run_id}/sign")
async def run_sign(run_id: str, request: Request, store: Store = Depends(get_store)):
    form = await _form(request)
    state = store.state()
    run = _run(state, run_id)
    if run.get("signed_date"):
        raise HTTPException(409, f"{run_id} is already signed.")
    steps = importers.load_checklist()
    recorded = run.get("steps") or {}
    reasons = []
    missing = cycle.missing_evidence(run, steps)
    if missing:
        reasons.append(f"Sign-off: record the evidence for step {', '.join(map(str, missing))} first.")
    not_done = [s["n"] for s in steps if s["n"] not in missing and not (recorded.get(str(s["n"])) or {}).get("done")]
    if not_done:
        reasons.append(f"Sign-off: mark step {', '.join(map(str, not_done))} done.")
    if not form.get("signed_by"):
        reasons.append("Sign-off: name the accountable executive who signs (B.8 step 18).")
    next_due = _date(form.get("next_due"))
    if next_due is None or next_due <= run["date"]:
        reasons.append("Sign-off: fix the date of the next run, after this run's date (B.8 step 18).")
    if reasons:
        return _run_page(request, store, run_id, reasons, 422)
    actor = request.app.state.actor
    pending = cycle.pending_trigger_dates(state)
    with store.transaction():
        for line_id, line in sorted(_live(state).items()):
            new = rules.next_review(next_due, pending.get(line_id))
            if new != line.get("next_review"):
                store.append(Event(entity="register", entity_id=line_id, field="next_review",
                                   old=line.get("next_review"), new=new, actor=actor,
                                   reason=f"next review fixed by the sign-off of {run_id}"))
        # signed_date last: its event closes the sign-off, and bounds the period the run covers.
        for field, new in (("signed_by", form["signed_by"]), ("next_due", next_due),
                           ("signed_date", date.today().isoformat())):
            store.append(Event(entity="cycle", entity_id=run_id, field=field, old=run.get(field), new=new,
                               actor=actor, reason=f"{run_id} signed off"))
    return RedirectResponse(f"/cycle/runs/{run_id}", status_code=303)


# -- packs ------------------------------------------------------------------

@router.get("/cycle/runs/{run_id}/pack.zip")
async def run_pack(run_id: str, request: Request, store: Store = Depends(get_store)):
    run = _run(store.state(), run_id)
    _, this, covered = _window(store.events(), run_id)
    # A signed run's pack holds the register as it stood when it was signed.
    state = store.replay(seq=this["seq"]) if this else store.state()
    prov = provenance(state, request.app.state.actor)
    body = packs.quarterly(state, library_lines(store), covered, run_id, run, importers.load_checklist(), prov)
    return send_document(request, store, f"{run['kind']} pack", f"pack-{run_id}", "zip", body, prov)


@router.get("/cycle/evidence-pack.zip")
async def evidence_pack(request: Request, store: Store = Depends(get_store)):
    state = store.state()
    prov = provenance(state, request.app.state.actor)
    body = packs.evidence(state, library_lines(store), store.events(), prov)
    return send_document(request, store, "evidence pack", "evidence-pack", "zip", body, prov)
