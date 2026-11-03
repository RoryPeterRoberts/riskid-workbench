"""Round 3 store and audit-trail tests (PLAN.md section 4, round 3).

Covers the done-when checks: events append and project; a change then
``replay(before)`` shows the old value; ``retire`` keeps the line in replay
and removes it from the live view; any call that would delete raises;
``riskid init`` on a temp path yields 91 library lines and 42 taxonomy lines;
the fixture builds. Plus the round 2 ``pilot_overdue`` check on the fixture's
CV-screening system.
"""

from datetime import date, datetime, timezone

import pytest

from riskid import rules
from riskid.model import Event
from riskid.store import NoDeleteError, Store, init, rebuild


def _store(tmp_path):
    return Store(tmp_path / "s.riskid")


def test_events_append_and_project(tmp_path):
    store = _store(tmp_path)
    store.append(Event(
        entity="system", entity_id="SYS-001",
        new={"name": "Demo", "owner": "alice"},
        timestamp="2026-11-01", actor="t",
    ))
    assert store.systems() == [{"name": "Demo", "owner": "alice"}]
    # a field change updates the projection in place
    store.append(Event(
        entity="system", entity_id="SYS-001",
        field="owner", old="alice", new="bob",
        timestamp="2026-11-05", actor="t",
    ))
    assert store.systems()[0]["owner"] == "bob"
    store.close()


def test_change_then_replay_before_shows_old_value(tmp_path):
    store = _store(tmp_path)
    store.append(Event(
        entity="system", entity_id="SYS-001",
        new={"owner": "alice"},
        timestamp="2026-11-01", actor="t",
    ))
    store.append(Event(
        entity="system", entity_id="SYS-001",
        field="owner", old="alice", new="bob",
        timestamp="2026-11-05", actor="t",
    ))
    assert store.systems()[0]["owner"] == "bob"          # live view
    before = store.replay("2026-11-03")                  # before the change
    assert before["system"]["SYS-001"]["owner"] == "alice"
    store.close()


def test_retire_keeps_line_in_replay_and_removes_from_live(tmp_path):
    store = _store(tmp_path)
    store.append(Event(
        entity="register", entity_id="RL-1",
        new={"id": "RL-1", "status": "active", "definition": "fraud"},
        timestamp="2026-11-01", actor="t",
    ))
    assert [r["id"] for r in store.register_live()] == ["RL-1"]

    store.retire("RL-1", reason="superseded by RL-7", actor="rory", when="2026-11-10")

    # the live register no longer shows it ...
    assert store.register_live() == []
    # ... but the audit trail keeps it, so a replay before the retirement
    # reconstructs the line as it then stood (active), and one after shows
    # it retired.
    before = store.replay("2026-11-05")
    assert before["register"]["RL-1"]["status"] == "active"
    after = store.replay("2026-11-20")
    assert after["register"]["RL-1"]["status"] == "retired"
    store.close()


def test_any_delete_raises(tmp_path):
    store = _store(tmp_path)
    store.append(Event(
        entity="register", entity_id="RL-1",
        new={"id": "RL-1", "status": "active"},
        timestamp="2026-11-01", actor="t",
    ))
    with pytest.raises(NoDeleteError):
        store.delete("RL-1")
    # the refused delete left the line intact
    assert store.state()["register"]["RL-1"]["status"] == "active"
    store.close()


def test_rebuild_regenerates_projections(tmp_path):
    store = _store(tmp_path)
    store.append(Event(
        entity="system", entity_id="SYS-001",
        new={"owner": "alice"},
        timestamp="2026-11-01", actor="t",
    ))
    store.rebuild()  # projections regenerated from the event table alone
    assert store.systems() == [{"owner": "alice"}]
    store.close()


def test_init_yields_91_library_and_42_taxonomy(tmp_path):
    store = init(tmp_path / "org.riskid")
    assert len(store.library()) == 91
    assert len(store.taxonomy()) == 42
    store.close()


def test_fixture_builds_three_systems(fixture_org):
    names = {s["name"] for s in fixture_org.systems()}
    assert names == {"Credit-scoring model", "Customer-service chatbot",
                     "CV-screening tool"}
    assert fixture_org.organisation()["name"] == "Northwind Analytics Ltd"


def test_pilot_overdue_flags_cv_screening_only(fixture_org):
    systems = {s["name"]: s for s in fixture_org.systems()}
    today = "2026-11-03"
    assert rules.pilot_overdue(systems["CV-screening tool"], today) is True
    assert rules.pilot_overdue(systems["Credit-scoring model"], today) is False
    assert rules.pilot_overdue(systems["Customer-service chatbot"], today) is False


def test_rebuild_module_function(tmp_path):
    store = _store(tmp_path)
    store.append(Event(
        entity="system", entity_id="SYS-001",
        new={"owner": "alice"},
        timestamp="2026-11-01", actor="t",
    ))
    store.close()
    assert rebuild(tmp_path / "s.riskid") >= 1


def test_replay_includes_the_whole_day_asked_for(tmp_path):
    store = _store(tmp_path)
    store.append(Event(
        entity="system", entity_id="SYS-001",
        new={"owner": "alice"},
        timestamp="2026-06-30T09:00:00Z", actor="t",
    ))
    store.append(Event(
        entity="system", entity_id="SYS-001",
        field="owner", old="alice", new="bob",
        timestamp="2026-06-30T10:00:00Z", actor="t",   # the 10:00 change
    ))
    store.append(Event(
        entity="system", entity_id="SYS-001",
        field="owner", old="bob", new="carol",
        timestamp="2026-07-01T00:00:00Z", actor="t",   # the next day
    ))

    # A bare date asks for the whole of that UTC day: the 10:00 change is in,
    # the 1 July change is not.
    assert store.replay("2026-06-30")["system"]["SYS-001"]["owner"] == "bob"
    assert store.replay(date(2026, 6, 30))["system"]["SYS-001"]["owner"] == "bob"

    # ... but the 10:00 change is not in a replay up to 09:00 that same day.
    at_nine = store.replay(datetime(2026, 6, 30, 9, 0, tzinfo=timezone.utc))
    assert at_nine["system"]["SYS-001"]["owner"] == "alice"
    store.close()


def test_init_stamps_the_pack_load_from_today(tmp_path):
    store = init(tmp_path / "org.riskid")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    # with no when, the packs are recorded as loaded right now, not on some
    # back-dated date
    assert store.state()["pack"]["library"]["date"].startswith(today)
    store.close()


def test_init_refuses_an_existing_file(tmp_path):
    from riskid.cli import main

    target = tmp_path / "org.riskid"
    assert main(["init", str(target)]) == 0
    assert main(["init", str(target)]) == 1   # a second init is refused


def test_rebuild_refuses_a_missing_file(tmp_path):
    from riskid.cli import main

    assert main(["rebuild", str(tmp_path / "nope.riskid")]) == 1


def test_retire_refuses_a_line_not_in_the_register(tmp_path):
    store = _store(tmp_path)
    store.append(Event(
        entity="register", entity_id="RL-1",
        new={"id": "RL-1", "status": "active"},
        timestamp="2026-11-01", actor="t",
    ))
    with pytest.raises(KeyError):
        store.retire("RL-TYPO", reason="never existed", actor="rory")
    # nothing was appended: the register is unchanged
    assert [r["id"] for r in store.register_live()] == ["RL-1"]
    store.close()


def test_fixture_risk_criteria_match_the_rules(fixture_org):
    criteria = fixture_org.organisation()["risk_criteria"].lower()
    assert "15 or more" in criteria      # §5.3: material at inherent >= 15
    assert "impact is 5" in criteria     # §5.3: ...or impact 5
    assert "article 5" in criteria       # ch 5: a prohibited practice is not accepted
