"""Contracts (SPEC.md 6.12; B.9; chapter 12): the clause checklist per supplied system.

One contract record per system (entity ``contract``, keyed by the system's ID):
each of B.9's 17 clauses is present, partial or absent, or blank until
reviewed, with the contract reference and a note. Every save is an event, so
the trail keeps each earlier reading of the contract.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse

from riskid import contracts, importers
from riskid.model import Contract, Event
from riskid.store import Store
from riskid.web import get_store, render

router = APIRouter()


def _system(state: dict, system_id: str) -> dict:
    system = state.get("system", {}).get(system_id)
    if system is None:
        raise HTTPException(404, f"No system {system_id} in this inventory.")
    return system


def _page(request, store, system_id: str, reasons=(), status_code=200, values=None):
    state = store.state()
    system = _system(state, system_id)
    clauses = importers.load_contract_clauses()
    contract = state.get("contract", {}).get(system_id)
    live = contracts.live_lines(state, system_id)
    recorded = (contract or {}).get("clauses") or {}
    return render(request, "contract.html", "contracts", status_code=status_code, reasons=list(reasons),
                  system=system, contract=contract or {}, clauses=clauses, live=live, statuses=contracts.STATUSES,
                  values=values or {f"clause_{n}": s for n, s in recorded.items()},
                  gaps=contracts.gaps(contract, live, clauses))


@router.get("/contracts")
async def contracts_list(request: Request, store: Store = Depends(get_store)):
    state = store.state()
    clauses = importers.load_contract_clauses()
    rows = []
    for sys_id, system in sorted(state.get("system", {}).items()):
        contract = state.get("contract", {}).get(sys_id)
        live = contracts.live_lines(state, sys_id)
        rows.append((system, contract, len(contracts.gaps(contract, live, clauses)),
                     contracts.needs_contract(system), contracts.meets_standard(contract, live, clauses)))
    supplied = [r for r in rows if r[3]]
    return render(request, "contracts.html", "contracts", rows=rows,
                  supplied=len(supplied), meeting=sum(r[4] for r in supplied))


@router.get("/contracts/{system_id}")
async def contract_view(system_id: str, request: Request, store: Store = Depends(get_store)):
    return _page(request, store, system_id)


@router.post("/contracts/{system_id}")
async def contract_record(system_id: str, request: Request, store: Store = Depends(get_store)):
    form = {k: str(v).strip() for k, v in (await request.form()).items()}
    _system(store.state(), system_id)
    statuses, reasons = {}, []
    for clause in importers.load_contract_clauses():
        value = form.get(f"clause_{clause['n']}", "")
        if value and value not in contracts.STATUSES:
            reasons.append(f"Clause {clause['n']}: present, partial or absent; leave it blank until it is reviewed.")
        elif value:
            statuses[str(clause["n"])] = value
    if reasons:
        return _page(request, store, system_id, reasons, 422, form)
    contract = Contract(system_id=system_id, clauses=statuses, reference=form.get("reference") or None,
                        gap_note=form.get("gap_note") or None)
    store.append(Event(entity="contract", entity_id=system_id, new=contract.to_dict(),
                       actor=request.app.state.actor, reason=f"B.9 checklist recorded for {system_id}"))
    return RedirectResponse(f"/contracts/{system_id}", status_code=303)
