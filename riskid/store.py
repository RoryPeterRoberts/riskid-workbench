"""The store and the audit trail (PLAN.md section 4, round 3).

SPEC.md section 4: one SQLite file per organisation, holding an event table
that is the source of truth plus tables that are projections of it. The event
table is append-only (SPEC.md 5.6, nothing is ever deleted; retirement is
itself an event) and the projections are rebuilt from it on demand
(SPEC.md section 9, ``riskid rebuild``).

The module is a thin repo layer over the standard-library ``sqlite3`` driver
(SPEC.md section 9): the event table, a single generic projection table that
covers every entity, and a few read views. There is no ORM.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import date
from pathlib import Path

from riskid import importers
from riskid.model import DataPack, Event
from riskid.timestamps import now as _now
from riskid.timestamps import replay_cutoff as _replay_cutoff
from riskid.timestamps import stamp as _stamp

__all__ = ["Store", "NoDeleteError", "init", "rebuild"]


class NoDeleteError(Exception):
    """Raised when a call would delete data (SPEC.md 5.6: retirement is an event)."""


_SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    seq          INTEGER PRIMARY KEY AUTOINCREMENT,
    ts           TEXT NOT NULL,
    actor        TEXT,
    entity       TEXT NOT NULL,
    entity_id    TEXT NOT NULL,
    field        TEXT,
    old          TEXT,
    new          TEXT,
    reason       TEXT,
    evidence_ref TEXT,
    ai_draft     TEXT
);
CREATE TABLE IF NOT EXISTS projection (
    entity    TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    state     TEXT NOT NULL,
    PRIMARY KEY (entity, entity_id)
);
CREATE INDEX IF NOT EXISTS events_ts ON events (ts, seq);
"""

# Entity names (event.entity); one projection table covers them all, so the set only grows.
_ENTITY_NAMES = (
    "organisation", "system", "register", "assessment", "control", "indicator",
    "usecase", "workshop", "interaction", "bowtie", "trigger", "cycle",
    "contract", "document", "library", "taxonomy", "pack",
    "discovery", "disagreement", "resolution", "reconciliation",  # rounds 4 and 8
    "person", "settings", "ai_request",                          # round 14
)


def _json(value) -> str | None:
    """Serialise an event payload column; None stays NULL so columns stay compact."""
    if value is None:
        return None
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _loads(raw: str | None):
    if raw is None:
        return None
    return json.loads(raw)


class Store:
    """An organisation store: an append-only event table plus projections of it."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._conn = sqlite3.connect(self.path)
        self._conn.row_factory = sqlite3.Row
        self._depth = 0          # open transaction() blocks; append commits only at 0
        self._ensure_schema()

    # -- lifecycle ---------------------------------------------------------

    def _ensure_schema(self) -> None:
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    @contextmanager
    def transaction(self):
        """Append several events as one change: all of them are kept, or none.

        Inside the block :meth:`append` does not commit; the outermost block
        commits once at its end, or rolls everything back if an exception
        leaves it.
        """
        self._depth += 1
        try:
            yield self
        except BaseException:
            self._depth -= 1
            if self._depth == 0:
                self._conn.rollback()
            raise
        self._depth -= 1
        if self._depth == 0:
            self._conn.commit()

    # -- the append-only audit trail ---------------------------------------

    def append(self, event: Event) -> int:
        """Append one event to the audit trail and fold it into the projections.

        A whole-entity event carries ``field=None`` and a full state in
        ``new``; a field change carries the field name and the new value.
        Returns the ``seq`` of the stored row, which is the audit trail's order.
        """
        if event.entity not in _ENTITY_NAMES:
            raise ValueError(f"unknown event entity: {event.entity!r}")
        ts = _stamp(event.timestamp)
        row = self._conn.execute(
            "SELECT state FROM projection WHERE entity = ? AND entity_id = ?",
            (event.entity, event.entity_id),
        ).fetchone()
        state = json.loads(row["state"]) if row else {}
        if event.field is None:
            state = dict(event.new or {})
        else:
            state = {**state, event.field: event.new}
        self._conn.execute(
            "INSERT INTO projection (entity, entity_id, state) VALUES (?, ?, ?) "
            "ON CONFLICT (entity, entity_id) DO UPDATE SET state = excluded.state",
            (event.entity, event.entity_id, _json(state)),
        )
        cur = self._conn.execute(
            "INSERT INTO events (ts, actor, entity, entity_id, field, old, new, "
            "reason, evidence_ref, ai_draft) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                ts, event.actor, event.entity, event.entity_id, event.field,
                _json(event.old), _json(event.new), event.reason,
                event.evidence_ref, _json(event.ai_draft) if event.ai_draft else None,
            ),
        )
        if not self._depth:
            self._conn.commit()
        return cur.lastrowid

    # -- projections (the live view) --------------------------------------

    def _projections(self) -> dict:
        rows = self._conn.execute(
            "SELECT entity, entity_id, state FROM projection"
        ).fetchall()
        snap: dict = {}
        for r in rows:
            snap.setdefault(r["entity"], {})[r["entity_id"]] = json.loads(r["state"])
        return snap

    def state(self) -> dict:
        """The full current snapshot: {entity: {entity_id: state}}, including retired lines."""
        return self._projections()

    def systems(self) -> list:
        return [s for _, s in sorted(self._projections().get("system", {}).items())]

    def register_live(self) -> list:
        """Register lines that are still in the live register (not retired)."""
        return [
            s for _, s in sorted(self._projections().get("register", {}).items())
            if s.get("status") != "retired"
        ]

    def library(self) -> list:
        return [s for _, s in sorted(self._projections().get("library", {}).items())]

    def taxonomy(self) -> list:
        return [s for _, s in sorted(self._projections().get("taxonomy", {}).items())]

    def organisation(self) -> dict | None:
        return self._projections().get("organisation", {}).get("organisation")

    def events(self) -> list:
        """Every event in the audit trail, in order, as dicts (the trail itself, read-only)."""
        return [dict(r) for r in self._conn.execute("SELECT * FROM events ORDER BY seq")]

    # -- time travel: the audit trail replayed ----------------------------

    def replay(self, when=None, *, seq: int | None = None) -> dict:
        """Reconstruct every entity as it stood on ``when``, from the event table only.

        Returns the same {entity: {entity_id: state}} shape as :meth:`state`,
        but rebuilt from events up to and including ``when``. A bare date means
        the whole of that UTC day (so everything on it is included, not just
        its midnight); a datetime means up to that instant. With ``seq``, it is
        as things stood just after that event. A line retired later still
        appears here (its events are never deleted); a line not yet created is absent.
        """
        where, arg = ("seq <= ?", seq) if seq is not None else ("ts <= ?", _replay_cutoff(when))
        rows = self._conn.execute(
            f"SELECT entity, entity_id, field, new FROM events WHERE {where} ORDER BY seq", (arg,)).fetchall()
        snap: dict = {}
        for r in rows:
            _apply_event(snap, _EventRow(r))
        return snap

    # -- identifiers: never reused (SPEC.md section 4) ----------------------

    def next_id(self, entity: str, prefix: str) -> str:
        """The next ``PREFIX-nnn`` ID for ``entity``, one above any ever recorded.

        Read from the event table, so an ID stays used even after its line is
        retired: IDs are never reused.
        """
        rows = self._conn.execute(
            "SELECT DISTINCT entity_id FROM events WHERE entity = ? AND entity_id LIKE ?",
            (entity, f"{prefix}-%"),
        ).fetchall()
        numbers = [int(r[0][len(prefix) + 1:]) for r in rows
                   if r[0][len(prefix) + 1:].isdigit()]
        return f"{prefix}-{max(numbers, default=0) + 1:03d}"

    # -- retirement: an event, never a deletion ---------------------------

    def retire(self, line_id: str, reason: str, actor: str,
               when: str | date | None = None) -> list:
        """Retire a register line: keep its full history, flag it out of the live view.

        Emits a status event and a retired_reason event so the line stays
        present in every replay while :meth:`register_live` excludes it.
        Raises :class:`KeyError` if ``line_id`` is not in the register, so a
        typo cannot retire a line that does not exist.
        Returns the seqs of the two events.
        """
        snap = self._projections().get("register", {})
        if line_id not in snap:
            raise KeyError(f"cannot retire {line_id!r}: it is not in the register")
        base = _stamp(when)
        old_status = snap[line_id].get("status")
        seqs = []
        for field, value in (("status", "retired"), ("retired_reason", reason)):
            ev = Event(
                timestamp=base, actor=actor, entity="register", entity_id=line_id,
                field=field, old=(old_status if field == "status" else None),
                new=value, reason=reason,
            )
            seqs.append(self.append(ev))
        return seqs

    def delete(self, *args, **kwargs) -> None:
        """The store never deletes; SPEC.md 5.6. Raises on any attempt."""
        raise NoDeleteError(
            "the store never deletes data; retirement is an event (SPEC.md 5.6)"
        )

    # -- projections rebuilt from the event table (riskid rebuild) --------

    def rebuild(self) -> int:
        """Drop and regenerate the projection tables from the event table.

        This is what ``riskid rebuild`` runs: the projections are disposable
        because the event table is the source of truth.
        """
        self._conn.execute("DELETE FROM projection")
        rows = self._conn.execute(
            "SELECT entity, entity_id, field, new FROM events ORDER BY seq"
        ).fetchall()
        snap: dict = {}
        for r in rows:
            _apply_event(snap, _EventRow(r))
        for entity, by_id in snap.items():
            for entity_id, state in by_id.items():
                self._conn.execute(
                    "INSERT OR REPLACE INTO projection (entity, entity_id, state) "
                    "VALUES (?, ?, ?)",
                    (entity, entity_id, _json(state)),
                )
        self._conn.commit()
        return len(rows)

    # -- loading the data packs (riskid init) -----------------------------

    def load_packs(self, when=None, actor: str = "riskid") -> dict:
        """Load the bundled data packs as events (SPEC.md 7.1, 8.3).

        Records the 91 library lines, the 42 taxonomy lines and the versions
        of the scales and indicator presets. ``when`` is when the packs are
        recorded as loaded; with no value the current UTC time is used, so a
        new file never back-dates its own load. Idempotent only on a fresh
        file; run it on a freshly created store.
        """
        if when is None:
            when = _now()
        with self.transaction():
            return self._load_packs(when, actor)

    def _load_packs(self, when, actor) -> dict:
        version = importers.load_version()
        n_library = n_taxonomy = 0
        for line in importers.load_library():
            self.append(Event(
                timestamp=when, actor=actor, entity="library",
                entity_id=line.id, new=line.to_dict(),
                reason="library pack load",
            ))
            n_library += 1
        for row in importers.load_taxonomy():
            self.append(Event(
                timestamp=when, actor=actor, entity="taxonomy",
                entity_id=row.l2_code, new=row.to_dict(),
                reason="taxonomy pack load",
            ))
            n_taxonomy += 1
        for pack in ("library", "scales", "indicators"):
            self.append(Event(
                timestamp=when, actor=actor, entity="pack", entity_id=pack,
                new=DataPack(
                    name=pack, version=version, date=when, source="bundled"
                ).to_dict(),
                reason="data pack version",
            ))
        return {"library": n_library, "taxonomy": n_taxonomy, "version": version}


# -- helpers ----------------------------------------------------------------


def _apply_event(snap: dict, event) -> None:
    """Fold one event into a {entity: {entity_id: state}} snapshot, in place."""
    by_id = snap.setdefault(event.entity, {})
    if event.field is None:
        by_id[event.entity_id] = dict(event.new or {})
    else:
        by_id.setdefault(event.entity_id, {})[event.field] = event.new


class _EventRow:
    """Adapts an events-table row to the (entity, entity_id, field, new) shape."""

    def __init__(self, row):
        self.entity = row["entity"]
        self.entity_id = row["entity_id"]
        self.field = row["field"]
        self.new = _loads(row["new"])


# -- module-level entry points for the CLI ---------------------------------


def init(path: str | Path, when=None) -> Store:
    """Create the organisation file and load the data packs (PLAN.md round 3).

    ``init`` only creates a new file; a path that already holds an organisation
    is refused (rebuild it instead of re-initialising). ``when`` fixes when the
    packs are recorded as loaded; with no value the current UTC time is used.
    """
    target = Path(path)
    if target.exists():
        raise FileExistsError(
            f"an organisation file already exists at {target}; "
            "rebuild it instead of re-initialising")
    store = Store(target)
    try:
        store.load_packs(when=when)
    except BaseException:
        # Created by this call and holding no events: removed, so a second init is not refused.
        store.close()
        target.unlink()
        raise
    return store


def rebuild(path: str | Path) -> int:
    """Rebuild the projections of an existing organisation file from its events.

    Refuses a path that does not exist: an append-only trail cannot be rebuilt
    from nothing, and creating an empty file here would hide the mistake.
    """
    target = Path(path)
    if not target.exists():
        raise FileNotFoundError(
            f"no organisation file at {target}; create it with `riskid init`")
    return Store(target).rebuild()
