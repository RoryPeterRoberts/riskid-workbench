"""Assess (SPEC.md 6.7; chapter 9; B.6): the scales as pickers, the controls table, the locked residual.

Each save is a new assessment (AS-nnn) for the line, so the line's history
keeps every assessment; the latest is the current one. A minority view given
in the record also goes to the disagreement log (B.6 field 7). Controls
(CT-nnn) belong to a line; recording a test is what unlocks the residual.
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse, Response

from riskid import importers, rules
from riskid.assess import DATA_QUALITY, SCALES, escalates, parse_assessment
from riskid.documents.heatmap import placements, render
from riskid.model import Control, Disagreement, Event
from riskid.reconcile import DIMENSIONS, library_lines
from riskid.store import Store
from riskid.web import get_store, render as render_page
from riskid.web.usecase_form import CONTROL_TYPES

router = APIRouter()
FLAGS = importers.load_flags()


def _line(store: Store, line_id: str) -> dict:
    line = store.state().get("register", {}).get(line_id)
    if line is None:
        raise HTTPException(404, f"No line {line_id} in the register.")
    return line


def _controls(store: Store, line_id: str) -> list:
    return [dict(c, id=ct_id) for ct_id, c in sorted(store.state().get("control", {}).items())
            if c.get("line_id") == line_id]


def latest_assessments(state: dict) -> dict:
    """The current (latest) assessment of each line: ``{line_id: (as_id, assessment)}``."""
    latest: dict = {}
    for as_id, a in sorted(state.get("assessment", {}).items(), key=lambda kv: int(kv[0][3:])):
        latest[a["line_id"]] = (as_id, a)
    return latest


def _rows(state: dict) -> list:
    live = {i for i, line in state.get("register", {}).items() if line.get("status") != "retired"}
    return [{"id": line_id, "L": a["likelihood"], "I": max(a["impact"].values()),
             "rL": a["residual_L"], "rI": a["residual_I"]}
            for line_id, (_, a) in sorted(latest_assessments(state).items()) if line_id in live]


def _title(store: Store, line_id: str, line: dict) -> str:
    library = library_lines(store)
    return library[line_id].title if line_id in library else (line.get("definition") or "")


def _form_page(request, store, line_id, line, values=None, reasons=(), status_code=200):
    controls = _controls(store, line_id)
    history = [(i, a) for i, a in sorted(store.state().get("assessment", {}).items())
               if a["line_id"] == line_id]
    return render_page(request, "assess_form.html", "assess", status_code=status_code,
                       line_id=line_id, line=line, title=_title(store, line_id, line),
                       scales=SCALES, dims=rules.DIM_ORDER, data_quality=DATA_QUALITY,
                       values=values or {}, reasons=list(reasons), controls=controls,
                       control_types=CONTROL_TYPES, dimensions=DIMENSIONS, history=history,
                       unlocked=rules.residual_allowed(controls))


@router.get("/assess")
async def assess_list(request: Request, store: Store = Depends(get_store)):
    state = store.state()
    latest = latest_assessments(state)
    lines = [(line_id, line, latest.get(line_id)) for line_id, line in
             sorted(state.get("register", {}).items()) if line.get("status") != "retired"]
    rows = _rows(state)
    return render_page(request, "assess_list.html", "assess", lines=lines,
                       titles={i: _title(store, i, l) for i, l, _ in lines},
                       cells={"inherent": placements(rows, "L", "I"),
                              "residual": placements(rows, "rL", "rI")},
                       band=rules.band, escalates=escalates)


@router.get("/assess/heatmap/{kind}.png")
async def heatmap(kind: str, store: Store = Depends(get_store)):
    keys = {"inherent": ("L", "I", "Inherent risk"), "residual": ("rL", "rI", "Residual risk")}
    if kind not in keys:
        raise HTTPException(404, "The heat maps are inherent and residual.")
    key_l, key_i, title = keys[kind]
    return Response(render(_rows(store.state()), key_l, key_i, title), media_type="image/png")


@router.get("/assess/{line_id}")
async def assess_form(line_id: str, request: Request, store: Store = Depends(get_store)):
    line = _line(store, line_id)
    latest = latest_assessments(store.state()).get(line_id)
    values = {}
    if latest:
        a = latest[1]
        values = {f"impact_{d}": a["impact"].get(d) for d in rules.DIM_ORDER}
        values.update({k: a.get(k) for k in ("harm_scored", "unit_of_exposure", "likelihood",
                                            "vulnerability", "speed", "data_quality",
                                            "data_quality_basis", "dominant_reasoning",
                                            "model_vendor_dependency")})
    return _form_page(request, store, line_id, line, values)


@router.post("/assess/{line_id}")
async def assess_save(line_id: str, request: Request, store: Store = Depends(get_store)):
    line = _line(store, line_id)
    if line.get("status") == "retired":
        raise HTTPException(409, f"{line_id} is retired; its assessments stand as they were.")
    form = {k: str(v) for k, v in (await request.form()).items()}
    system = store.state().get("system", {}).get(line.get("system_id")) or {}
    assessment, reasons, disagreement = parse_assessment(form, line_id, _controls(store, line_id),
                                                         FLAGS, system)
    if reasons:
        return _form_page(request, store, line_id, line, form, reasons, 422)
    actor = request.app.state.actor
    assessment.assessor = actor
    as_id = store.next_id("assessment", "AS")
    with store.transaction():
        store.append(Event(entity="assessment", entity_id=as_id, new=assessment.to_dict(), actor=actor,
                           reason=f"assessment of {line_id}"))
        if disagreement:
            dl_id = store.next_id("disagreement", "DL")
            entry = Disagreement(line_id=line_id, raised_in=as_id, **disagreement)
            store.append(Event(entity="disagreement", entity_id=dl_id, new=entry.to_dict(), actor=actor,
                               reason=f"minority view recorded in {as_id}"))
    return RedirectResponse(f"/assess/{line_id}/record", status_code=303)


@router.post("/assess/{line_id}/controls")
async def control_add(line_id: str, request: Request, store: Store = Depends(get_store)):
    line = _line(store, line_id)
    form = {k: str(v).strip() for k, v in (await request.form()).items()}
    reasons = []
    if not form.get("name"):
        reasons.append("Control: give it a name.")
    if form.get("type") not in CONTROL_TYPES:
        reasons.append("Control: the type is preventive, detective or corrective.")
    if reasons:
        return _form_page(request, store, line_id, line, {}, reasons, 422)
    control = Control(line_id=line_id, name=form["name"], type=form["type"],
                      owner=form.get("owner") or None, evidence_ref=form.get("evidence_ref") or None,
                      annex_a_ref=form.get("annex_a_ref") or None)
    store.append(Event(entity="control", entity_id=store.next_id("control", "CT"),
                       new=control.to_dict(), actor=request.app.state.actor,
                       reason=f"control listed for {line_id}"))
    return RedirectResponse(f"/assess/{line_id}#controls", status_code=303)


@router.post("/assess/{line_id}/controls/{ct_id}/test")
async def control_test(line_id: str, ct_id: str, request: Request, store: Store = Depends(get_store)):
    line = _line(store, line_id)
    control = store.state().get("control", {}).get(ct_id)
    if control is None or control.get("line_id") != line_id:
        raise HTTPException(404, f"No control {ct_id} on {line_id}.")
    form = {k: str(v).strip() for k, v in (await request.form()).items()}
    reasons = []
    try:
        tested = date.fromisoformat(form.get("test_date", "")).isoformat()
    except ValueError:
        tested = None
        reasons.append("Test: give the date as YYYY-MM-DD.")
    if form.get("outcome") not in ("passed", "failed"):
        reasons.append("Test: did the control pass or fail? A failed test leaves the residual locked.")
    if reasons:
        return _form_page(request, store, line_id, line, {}, reasons, 422)
    actor = request.app.state.actor
    with store.transaction():
        result = f"{form['outcome']}: {form['test_result']}" if form.get("test_result") else form["outcome"]
        for field, value in (("last_test_date", tested), ("last_test_result", result),
                             ("evidence_ref", form.get("evidence_ref") or control.get("evidence_ref"))):
            if value != control.get(field):
                store.append(Event(entity="control", entity_id=ct_id, field=field,
                                   old=control.get(field), new=value, actor=actor,
                                   reason=f"control test recorded for {line_id}"))
    return RedirectResponse(f"/assess/{line_id}#controls", status_code=303)


@router.get("/assess/{line_id}/record")
async def assess_record(line_id: str, request: Request, store: Store = Depends(get_store)):
    line = _line(store, line_id)
    latest = latest_assessments(store.state()).get(line_id)
    if latest is None:
        raise HTTPException(404, f"{line_id} has not been assessed.")
    as_id, a = latest
    return render_page(request, "assess_record.html", "assess", line_id=line_id, line=line,
                       title=_title(store, line_id, line), as_id=as_id, a=a,
                       controls=_controls(store, line_id), scales=SCALES,
                       residual_band=rules.band(a["residual"]) if a["residual"] else None,
                       escalates=escalates(a))
