"""Use cases (SPEC.md 6.5, template B.2, chapter 7): bottom-up submissions per system.

Every submission is recorded. One returned for any reason keeps its reasons
and can be corrected and resubmitted on the same record (UC-nnn). One
accepted becomes a candidate register line with source bottom-up: a new
ORG-nnn line, or the library ID given in field 1; a risk already in the
register is supported by the submission rather than entered twice.

With the assistant on, a use case can be drafted from the system's header
lines (SPEC.md section 8). The draft is recorded with status ``draft`` and
``ai_draft`` (model, version, date, the fields drafted), counts as Very Low
data quality until a person accepts it (SPEC.md 5.9), and is shown in the form
to accept as it stands, edit, or discard. Submitting it is the acceptance: the
person is recorded in ``ai_draft`` and the submission is checked as any other.
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from starlette.concurrency import run_in_threadpool

from riskid import rules
from riskid.ai import adapter
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


def _form_page(request, store, system, values, reasons, uc_id=None, status_code=200, draft=None):
    taxonomy = sorted(store.taxonomy(), key=lambda t: [int(p) for p in t["l2_code"].split(".")])
    settings = adapter.assistant_settings(store.state())
    on = adapter.is_on(settings)
    counts_as = (rules.ai_draft_quality({"ai_draft": draft, "data_quality": values.get("data_quality")})
                 if draft else None)
    return render(request, "usecase_form.html", "usecases", status_code=status_code, draft=draft,
                  counts_as=counts_as, assistant_on=on, assistant_endpoint=settings.get("endpoint"),
                  system=system, values=values, reasons=reasons, uc_id=uc_id, headers=HEADERS,
                  fields=FIELDS, taxonomy=taxonomy, roles=ROLES, stages=LIFECYCLE_STAGES,
                  sources=SOURCES, data_quality=DATA_QUALITY, control_types=CONTROL_TYPES,
                  control_rows=range(1, CONTROL_ROWS + 1), control_examples=CONTROL_EXAMPLES)


def _submit(request, store, system, values, uc_id=None, ai_draft=None):
    """Check a submission, record it, and on acceptance record its register line."""
    record, reasons = parse_usecase(values, _taxonomy(store), _known_lines(store))
    actor = request.app.state.actor
    new_record = uc_id is None
    uc_id = uc_id or store.next_id("usecase", "UC")
    usecase = UseCase(system_id=system["id"], submitted_by=actor, date=date.today().isoformat(),
                      ai_draft=ai_draft or {}, **record)
    reason = ("submitted" if new_record else "draft accepted and submitted" if ai_draft
              else "resubmitted after return")
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


def _draft_values(draft: dict, headers: dict) -> dict:
    """The drafted fields as form values beside the header lines; owner and rating stay for the person."""
    values = {f"header_{k}": v for k, v in headers.items()}
    values.update({k: draft.get(k) or "" for k in ("risk_id", "taxonomy", "definition", "drivers_direct",
                                                    "drivers_indirect", "metrics", "qualitative",
                                                    "indicators", "data_quality_basis")})
    for i, control in enumerate(draft.get("controls") or [], start=1):
        values.update({f"control_{i}_{k}": control.get(k) or "" for k in ("name", "type", "evidence")})
    return values


@router.post("/usecases/draft")
async def usecase_draft(request: Request, store: Store = Depends(get_store)):
    values = await _submitted(request)
    system = _system(store, values.get("system_id", ""))
    settings = adapter.assistant_settings(store.state())
    if not adapter.is_on(settings):
        raise HTTPException(409, "The assistant is off; Settings switches it on.")
    headers = header_defaults(system)
    # Only what the new-use-case screen shows: the header lines and the taxonomy codes to choose from.
    sent = {"header_lines": headers,
            "taxonomy": {t["l2_code"]: t["l2"] for t in store.taxonomy()}}
    actor = request.app.state.actor
    try:
        # A worker thread waits for the model, so the workbench stays responsive meanwhile.
        result = await run_in_threadpool(adapter.draft, settings, "use_case", sent)
    except adapter.AssistantError as exc:
        store.append(Event(entity="ai_request", entity_id=store.next_id("ai_request", "AIR"),
                           new={"kind": "use_case", "model": settings.get("model"), "sent": sorted(sent),
                                "outcome": str(exc)}, actor=actor, reason="assistant request failed"))
        return _form_page(request, store, system, {f"header_{k}": v for k, v in headers.items()},
                          [str(exc)], status_code=502)
    form = _draft_values(result["draft"], headers)
    record, _ = parse_usecase(form, _taxonomy(store), _known_lines(store))
    today = date.today().isoformat()
    drafted = sorted(k for k, v in result["draft"].items() if v)
    ai_draft = {"model": result["model"], "version": result["version"], "date": today, "fields": drafted}
    uc_id = store.next_id("usecase", "UC")
    with store.transaction():
        store.append(Event(entity="ai_request", entity_id=store.next_id("ai_request", "AIR"),
                           new={"kind": "use_case", "model": result["model"], "version": result["version"],
                                "tokens": result["tokens"], "sent": sorted(sent), "outcome": f"draft {uc_id}"},
                           actor=actor, reason=f"assistant drafted {uc_id} for {system['id']}"))
        store.append(Event(entity="usecase", entity_id=uc_id,
                           new=UseCase(system_id=system["id"], date=today, status="draft", ai_draft=ai_draft,
                                       **record).to_dict(),
                           actor=actor, reason=f"drafted by the assistant at the request of {actor}",
                           ai_draft={"model": result["model"], "version": result["version"]}))
    return RedirectResponse(f"/usecases/{uc_id}", status_code=303)


@router.post("/usecases/{uc_id}/discard")
async def usecase_discard(uc_id: str, request: Request, store: Store = Depends(get_store)):
    await request.form()
    usecase = store.state().get("usecase", {}).get(uc_id)
    if usecase is None or usecase["status"] != "draft":
        raise HTTPException(409, f"Only a draft is discarded; {uc_id} is not one.")
    store.append(Event(entity="usecase", entity_id=uc_id, field="status", old="draft", new="discarded",
                       actor=request.app.state.actor, reason="assistant draft discarded"))
    return RedirectResponse("/usecases", status_code=303)


@router.get("/usecases/{uc_id}")
async def usecase_view(uc_id: str, request: Request, store: Store = Depends(get_store)):
    usecase = store.state().get("usecase", {}).get(uc_id)
    if usecase is None:
        raise HTTPException(404, f"No use case {uc_id}.")
    system = _system(store, usecase["system_id"])
    if usecase["status"] == "draft":
        return _form_page(request, store, system, form_values(usecase), [], uc_id=uc_id,
                          draft=usecase["ai_draft"])
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
    if usecase["status"] not in ("returned", "draft"):
        raise HTTPException(409, f"{uc_id} is {usecase['status']}; only a returned submission or a draft "
                                 "is submitted again.")
    values = await _submitted(request)
    ai_draft = usecase.get("ai_draft") or None
    if ai_draft and not ai_draft.get("accepted_by"):
        ai_draft = dict(ai_draft, accepted_by=request.app.state.actor, accepted_date=date.today().isoformat())
    return _submit(request, store, _system(store, usecase["system_id"]), values, uc_id=uc_id, ai_draft=ai_draft)
