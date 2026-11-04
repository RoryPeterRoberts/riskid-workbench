"""What every document records about what it was built from (SPEC.md section 7).

"Every document records the data-pack versions and the register state hash it
was built from." The hash covers the whole state except the records of
documents themselves, so generating a document does not change it. Each
generation is recorded as a Document event (SPEC.md section 4).
"""

from __future__ import annotations

import hashlib
import json

from riskid.model import Document, Event
from riskid.timestamps import now


def state_hash(state: dict) -> str:
    """SHA-256 of the state, documents excluded, in a canonical JSON form."""
    body = {entity: rows for entity, rows in state.items() if entity != "document"}
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def pack_versions(state: dict) -> str:
    """The data packs and their versions, for example ``library 1.0, scales 1.0, indicators 1.0``."""
    packs = state.get("pack", {})
    return ", ".join(f"{name} {packs[name].get('version')}" for name in ("library", "scales", "indicators")
                     if name in packs) or "no data packs recorded"


def provenance(state: dict, actor: str) -> dict:
    """The lines a document carries about its own making."""
    return {"state_hash": state_hash(state), "pack_versions": pack_versions(state),
            "generated_at": now(), "generated_by": actor}


def record(store, kind: str, filename: str, prov: dict, actor: str) -> str:
    """Record a generated document in the audit trail; return its ID (DOC-nnn)."""
    doc_id = store.next_id("document", "DOC")
    doc = Document(kind=kind, generated_at=prov["generated_at"], inputs_hash=prov["state_hash"],
                   file_path=filename)
    store.append(Event(entity="document", entity_id=doc_id, new=doc.to_dict(), actor=actor,
                       reason=f"{kind} generated ({prov['pack_versions']})"))
    return doc_id
