"""Use cases (SPEC.md 6.5, template B.2, chapter 7): bottom-up submissions per system.

Every submission is recorded. One returned for any reason keeps its reasons
and can be corrected and resubmitted on the same record (UC-nnn). One
accepted becomes a candidate register line with source bottom-up: a new
ORG-nnn line, or the library ID given in field 1; a risk already in the
register is supported by the submission rather than entered twice.
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse

from riskid.model import Event, RegisterLine, UseCase
from riskid.propose import annex_a_refs
from riskid.store import Store
from riskid.web import get_store, render
from riskid.web.usecase_form import (CONTROL_EXAMPLES, CONTROL_ROWS, CONTROL_TYPES, DATA_QUALITY,
                                     FIELDS, HEADERS, SOURCES, SUB_PROCESSES, form_values,
                                     header_defaults, parse_usecase)
from riskid.rules import LIFECYCLE_STAGES
from riskid.web.system_form import ROLES

router = APIRouter()


def _system(store: Store, system_id: str) -> dict:
    system = store.state().get("system", {}).get(system_id)
    if system is None:
        raise HTTPException(404, f"No system {system_id} in this inventory.")
    return system


def _taxonomy(store: Store) -> dict:
    return {t["l2_code"]: t["l1_code"] for t in store.taxonomy()}


def _known_lines(store: Store) -> dict:
    """Library and register IDs with their Level 2 code; register entries win."""
    known = {line["id"]: line["l2"] for line in store.library()}
    known.update({i: line.get("l2") for i, line in store.state().get("register", {}).items()})
    return known


def _form_page(request, store, system, values, reasons, uc_id=None, status_code=200):
    taxonomy = sorted(store.taxonomy(), key=lambda t: [int(p) for p in t["l2_code"].split(".")])
    return render(request, "usecase_form.html", "usecases", status_code=status_code,
                  system=system, values=values, reasons=reasons, uc_id=uc_id, headers=HEADERS,
                  fields=FIELDS, taxonomy=taxonomy, roles=ROLES, stages=LIFECYCLE_STAGES,
                  sources=SOURCES, data_quality=DATA_QUALITY, control_types=CONTROL_TYPES,
                  control_rows=range(1, CONTROL_ROWS + 1), control_examples=CONTROL_EXAMPLES)


def _submit(request, store, system, values, uc_id=None):
    """Check a submission, record it, and on acceptance record its register line."""
    record, reasons = parse_usecase(values, _taxonomy(store), _known_lines(store))
    actor = request.app.state.actor
    new_record = uc_id is None
    uc_id = uc_id or store.next_id("usecase", "UC")
    usecase = UseCase(system_id=system["id"], submitted_by=actor, date=date.today().isoformat(),
                      **record)
    reason = "submitted" if new_record else "resubmitted after return"
    if reasons:
        # One reason per line: a reason may itself contain a semicolon.
        usecase.status, usecase.return_reason = "returned", "\n".join(reasons)
        store.append(Event(entity="usecase", entity_id=uc_id, new=usecase.to_dict(), actor=actor,
                           reason=f"{reason}; returned: " + " | ".join(reasons)))
        return _form_page(request, store, system, values, reasons, uc_id=uc_id, status_code=422)
    with store.transaction():
        return _accept(request, store, system, record, usecase, uc_id, reason)


def _accept(request, store, system, record, usecase, uc_id, reason):
    """Record the accepted submission and its register line, inside one transaction."""
    actor = request.app.state.actor
    fields = record["fields_"]
    register = store.state().get("register", {})
    line_id = fields["risk_id"] or store.next_id("register", "ORG")
    if line_id not in register:
        l2 = fields["taxonomy"]
        line = RegisterLine(
            id=line_id, system_id=system["id"], l1=_taxonomy(store)[l2], l2=l2,
            definition=fields["definition"], owner=fields["owner"], status="candidate",
            source="bottom-up", trend="new", role=record["headers"]["role"] or None,
            lifecycle_stages=[s for s in [record["headers"]["lifecycle_stage"]] if s],
            persons_affected=[p for p in [record["headers"]["persons_affected"]] if p],
            annex_a_controls=annex_a_refs(" ".join(c["name"] + " " + c["evidence"]
                                                   for c in fields["controls"])))
        store.append(Event(entity="register", entity_id=line_id, new=line.to_dict(), actor=actor,
                           reason=f"bottom-up candidate from use case {uc_id}"))
    usecase.status, usecase.line_id = "accepted", line_id
    store.append(Event(entity="usecase", entity_id=uc_id, new=usecase.to_dict(), actor=actor,
                       reason=f"{reason}; accepted as {line_id}"))
    return RedirectResponse(f"/usecases/{uc_id}", status_code=303)


async def _submitted(request: Request) -> dict:
    form = await request.form()
    return {name: str(value) for name, value in form.items()}


@router.get("/usecases")
async def usecases_list(request: Request, store: Store = Depends(get_store)):
    state = store.state()
    systems = sorted(state.get("system", {}).values(), key=lambda s: s["id"])
    usecases = sorted(state.get("usecase", {}).items())
    coverage = []
    for system in systems:
        contributed = {u["source"] for _, u in usecases
                       if u["system_id"] == system["id"] and u["status"] == "accepted"}
        coverage.append((system, [(p, p in contributed) for p in SUB_PROCESSES],
                         sum(p in contributed for p in SUB_PROCESSES)))
    return render(request, "usecases_list.html", "usecases", systems=systems,
                  usecases=usecases, coverage=coverage,
                  names={s["id"]: s["name"] for s in systems})


@router.get("/usecases/new")
async def usecase_new(request: Request, system: str = "", store: Store = Depends(get_store)):
    found = _system(store, system)
    values = {f"header_{k}": v for k, v in header_defaults(found).items()}
    return _form_page(request, store, found, values, [])


@router.post("/usecases")
async def usecase_create(request: Request, store: Store = Depends(get_store)):
    values = await _submitted(request)
    return _submit(request, store, _system(store, values.get("system_id", "")), values)


@router.get("/usecases/{uc_id}")
async def usecase_view(uc_id: str, request: Request, store: Store = Depends(get_store)):
    usecase = store.state().get("usecase", {}).get(uc_id)
    if usecase is None:
        raise HTTPException(404, f"No use case {uc_id}.")
    system = _system(store, usecase["system_id"])
    if usecase["status"] == "returned":
        reasons = usecase["return_reason"].split("\n")
        return _form_page(request, store, system, form_values(usecase), reasons, uc_id=uc_id)
    line = store.state().get("register", {}).get(usecase["line_id"])
    return render(request, "usecase_view.html", "usecases", uc_id=uc_id, usecase=usecase,
                  system=system, line=line, headers=HEADERS, fields=FIELDS)


@router.post("/usecases/{uc_id}")
async def usecase_resubmit(uc_id: str, request: Request, store: Store = Depends(get_store)):
    usecase = store.state().get("usecase", {}).get(uc_id)
    if usecase is None:
        raise HTTPException(404, f"No use case {uc_id}.")
    if usecase["status"] != "returned":
        raise HTTPException(409, f"{uc_id} was accepted as {usecase.get('line_id')}; "
                                 "only a returned submission is resubmitted.")
    values = await _submitted(request)
    return _submit(request, store, _system(store, usecase["system_id"]), values, uc_id=uc_id)
