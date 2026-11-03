"""Inventory (SPEC.md 6.2, template B.1): the system list, the B.1 form and the discovery ratio.

A new system is one whole-entity event with the next SYS-nnn ID; an edit is
one field event per changed field, carrying the person and the reason, so the
audit trail shows who changed what and why (SPEC.md section 1, principle 2).
"""

from __future__ import annotations

import re
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse

from riskid import rules
from riskid.model import Event, System
from riskid.store import Store
from riskid.web import get_store, render
from riskid.web.system_form import B1_ROWS, REQUIRED_FIELDS, form_values, parse_system_form

router = APIRouter()

_SYSTEM_ID = re.compile(r"^SYS-\d{3,}$")
_QUARTER = re.compile(r"^\d{4}-Q[1-4]$")


def _systems(store: Store) -> dict:
    return store.state().get("system", {})


def _discovery_rows(store: Store) -> list:
    rows = sorted(store.state().get("discovery", {}).values(), key=lambda d: d["quarter"])
    return [dict(d, ratio=f"{d['found'] / d['inventoried']:.2f}") for d in rows]


def _list_page(request, store, status_code=200, **context):
    today = date.today().isoformat()
    rows = [{"system": s, "pilot_overdue": rules.pilot_overdue(s, today)}
            for _, s in sorted(_systems(store).items())]
    context.setdefault("discovery_values", {})
    context.setdefault("discovery_reasons", [])
    saved = request.query_params.get("saved", "")
    return render(request, "inventory_list.html", "inventory", status_code=status_code,
                  rows=rows, discovery=_discovery_rows(store),
                  saved=saved if _SYSTEM_ID.match(saved) else None, **context)


def _form_page(request, system_id, values, reasons, status_code=200):
    return render(request, "inventory_form.html", "inventory", status_code=status_code,
                  rows=B1_ROWS, required=REQUIRED_FIELDS, system_id=system_id,
                  values=values, reasons=reasons)


async def _submitted(request: Request) -> dict:
    form = await request.form()
    return {name: str(value) for name, value in form.items()}


@router.get("/inventory")
async def inventory_list(request: Request, store: Store = Depends(get_store)):
    return _list_page(request, store)


@router.get("/inventory/new")
async def inventory_new(request: Request, store: Store = Depends(get_store)):
    return _form_page(request, None, {}, [])


@router.post("/inventory")
async def inventory_create(request: Request, store: Store = Depends(get_store)):
    values = await _submitted(request)
    fields, reasons = parse_system_form(values)
    if reasons:
        return _form_page(request, None, values, reasons, status_code=422)
    system_id = store.next_id("system", "SYS")
    system = System.from_dict({**fields, "id": system_id}).to_dict()
    store.append(Event(entity="system", entity_id=system_id, new=system,
                       actor=request.app.state.actor, reason="added to the inventory"))
    return RedirectResponse(f"/inventory?saved={system_id}", status_code=303)


@router.post("/inventory/discovery")
async def discovery_record(request: Request, store: Store = Depends(get_store)):
    """Record a quarter's discovery ratio: tools found against tools inventoried."""
    values = await _submitted(request)
    quarter = values.get("quarter", "").strip()
    found, inventoried = values.get("found", "").strip(), values.get("inventoried", "").strip()
    reasons = []
    if not _QUARTER.match(quarter):
        reasons.append("Quarter: give it as year and quarter, for example 2026-Q4.")
    if not found.isdigit():
        reasons.append("Tools found: give a whole number, 0 or more.")
    if not inventoried.isdigit() or int(inventoried) < 1:
        reasons.append("Tools inventoried: give a whole number, 1 or more.")
    if reasons:
        return _list_page(request, store, status_code=422,
                          discovery_values=values, discovery_reasons=reasons)
    store.append(Event(
        entity="discovery", entity_id=quarter, actor=request.app.state.actor,
        reason="discovery ratio recorded",
        new={"quarter": quarter, "found": int(found), "inventoried": int(inventoried),
             "method": values.get("method", "").strip() or None}))
    return RedirectResponse("/inventory#discovery", status_code=303)


@router.get("/inventory/{system_id}")
async def inventory_edit(system_id: str, request: Request, store: Store = Depends(get_store)):
    current = _systems(store).get(system_id)
    if current is None:
        raise HTTPException(404, f"No system {system_id} in this inventory.")
    return _form_page(request, system_id, form_values(current), [])


@router.post("/inventory/{system_id}")
async def inventory_update(system_id: str, request: Request, store: Store = Depends(get_store)):
    current = _systems(store).get(system_id)
    if current is None:
        raise HTTPException(404, f"No system {system_id} in this inventory.")
    values = await _submitted(request)
    fields, reasons = parse_system_form(values)
    if reasons:
        return _form_page(request, system_id, values, reasons, status_code=422)
    updated = System.from_dict({**fields, "id": system_id}).to_dict()
    reason = values.get("change_reason", "").strip() or "inventory edit"
    for name, value in updated.items():
        if value != current.get(name):
            store.append(Event(entity="system", entity_id=system_id, field=name,
                               old=current.get(name), new=value,
                               actor=request.app.state.actor, reason=reason))
    return RedirectResponse(f"/inventory?saved={system_id}", status_code=303)
