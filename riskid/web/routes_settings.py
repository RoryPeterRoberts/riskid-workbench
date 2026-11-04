"""Settings (SPEC.md 6.13, 8 and 10): the organisation, people, the assistant, packs and backup.

The people listed here can be chosen as the person recording; until one is,
it is the one the workbench started with (``RISKID_ACTOR`` or the account).
The choice holds for this run of the workbench and is not itself an event:
every change already records who made it.

The assistant is off until an endpoint and a model are set and it is switched
on; the setting is an event like any other, so the trail shows who turned it
on and when. Its API key is never stored: the adapter reads it from the
environment variable named here.

A backup is a plain copy of the organisation file, made with SQLite's backup
so it is consistent, and recorded as a document like any other download.
"""

from __future__ import annotations

import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse

from riskid.ai.adapter import DEFAULT_KEY_ENV, KEY_ENV_PREFIX, assistant_settings, is_on
from riskid.documents.provenance import provenance
from riskid.model import Event, Organisation, Person
from riskid.store import Store
from riskid.web import get_store, render
from riskid.web.routes_documents import send_document

router = APIRouter()
ORG_FIELDS = ("name", "sector", "jurisdictions", "risk_criteria", "accountable_executive", "ai_officer",
              "facilitator")


async def _form(request: Request) -> dict:
    return {k: str(v).strip() for k, v in (await request.form()).items()}


def _people(state: dict) -> list:
    return sorted(state.get("person", {}).items())


def _page(request, store, reasons=(), status_code=200):
    state = store.state()
    assistant = assistant_settings(state)
    return render(request, "settings.html", "settings", status_code=status_code, reasons=list(reasons),
                  organisation=state.get("organisation", {}).get("organisation") or {},
                  people=_people(state), default_actor=request.app.state.default_actor,
                  assistant=assistant, assistant_on=is_on(assistant), default_key_env=DEFAULT_KEY_ENV,
                  packs=sorted(state.get("pack", {}).values(), key=lambda p: p["name"]))


@router.get("/settings")
async def settings(request: Request, store: Store = Depends(get_store)):
    return _page(request, store)


@router.post("/settings/organisation")
async def organisation_record(request: Request, store: Store = Depends(get_store)):
    form = await _form(request)
    old = store.state().get("organisation", {}).get("organisation") or {}
    if not form.get("name"):
        return _page(request, store, ["Organisation: give its name."], 422)
    # A field the form did not send keeps its value; one sent empty is cleared.
    values = {k: (form[k] or None) if k in form else old.get(k) for k in ORG_FIELDS}
    if "jurisdictions" in form:
        values["jurisdictions"] = [j.strip() for j in form["jurisdictions"].split(",") if j.strip()]
    store.append(Event(entity="organisation", entity_id="organisation", new=Organisation(**values).to_dict(),
                       actor=request.app.state.actor, reason="organisation settings recorded"))
    return RedirectResponse("/settings#organisation", status_code=303)


@router.post("/settings/people")
async def person_add(request: Request, store: Store = Depends(get_store)):
    form = await _form(request)
    if not form.get("name"):
        return _page(request, store, ["People: give the person's name."], 422)
    person_id = store.next_id("person", "P")
    store.append(Event(entity="person", entity_id=person_id,
                       new=Person(name=form["name"], role=form.get("role") or None).to_dict(),
                       actor=request.app.state.actor, reason=f"{form['name']} added to the people"))
    return RedirectResponse("/settings#people", status_code=303)


@router.post("/settings/actor")
async def actor_choose(request: Request, store: Store = Depends(get_store)):
    form = await _form(request)
    names = {p["name"] for _, p in _people(store.state())} | {request.app.state.default_actor}
    if form.get("name") not in names:
        return _page(request, store, ["Recording as: choose one of the people listed here."], 422)
    request.app.state.actor = form["name"]
    return RedirectResponse("/settings#people", status_code=303)


@router.post("/settings/assistant")
async def assistant_record(request: Request, store: Store = Depends(get_store)):
    form = await _form(request)
    endpoint = form.get("endpoint", "")
    url = urlsplit(endpoint)
    reasons = []
    if endpoint and (url.scheme not in ("http", "https") or not url.netloc):
        reasons.append("Assistant: the endpoint is a web address starting http:// or https://.")
    if form.get("key_env") and not form["key_env"].startswith(KEY_ENV_PREFIX):
        reasons.append(f"Assistant: the API key's environment variable must start {KEY_ENV_PREFIX}.")
    if form.get("enabled") == "on" and not (endpoint and form.get("model")):
        reasons.append("Assistant: set the endpoint and the model before switching it on.")
    if reasons:
        return _page(request, store, reasons, 422)
    assistant = {"enabled": form.get("enabled") == "on", "endpoint": endpoint or None,
                 "model": form.get("model") or None, "version": form.get("version") or None,
                 "local": form.get("local") == "on", "key_env": form.get("key_env") or DEFAULT_KEY_ENV}
    store.append(Event(entity="settings", entity_id="assistant", new=assistant, actor=request.app.state.actor,
                       reason=f"assistant switched {'on' if assistant['enabled'] else 'off'}"))
    return RedirectResponse("/settings#assistant", status_code=303)


def _backup(path: Path) -> bytes:
    """A consistent copy of the organisation file, read through SQLite's backup."""
    with tempfile.TemporaryDirectory() as tmp:
        copy = Path(tmp) / "backup.riskid"
        # as_uri() escapes a space, # or ? in the path, which a bare file: URI would misread.
        source, target = sqlite3.connect(Path(path).resolve().as_uri() + "?mode=ro", uri=True), sqlite3.connect(copy)
        try:
            source.backup(target)
        finally:
            target.close()
            source.close()
        return copy.read_bytes()


@router.get("/settings/backup.riskid")
async def backup(request: Request, store: Store = Depends(get_store)):
    state = store.state()
    body = _backup(request.app.state.store_path)
    stamp = datetime.now(timezone.utc).strftime("%H%M%S")
    return send_document(request, store, "backup", f"backup-{stamp}", "riskid", body,
                         provenance(state, request.app.state.actor))
