"""Round 7 Workshop screens (PLAN.md round 7; SPEC.md 6.4; B.4, B.5).

The plan's checks: pre-lists are hidden until stage 2; all 23 prompts render
with their lines; each answer stores covered/not known with control and
evidence; votes are stored per participant and never summed into an average
in the record; the workshop record renders as HTML with every stage. Also the
stage gates, the participant entry view and the top-down candidates at close.
"""

import re

import pytest
from fastapi.testclient import TestClient

from riskid.app import create_app
from riskid.store import Store

BASE = "http://127.0.0.1:8765"
SEATED = {"system_ids": "SYS-001", "date": "2026-11-20", "facilitator": "Fiona Hayes",
          "vote_allowance": "5", "seat_1": "Ann Owner", "seat_5": "Ola Overseer",
          "seat_6": "Sid Sceptic"}


def _client(path):
    return TestClient(create_app(path, actor="tester"), base_url=BASE)


def _workshop(path):
    with Store(path) as store:
        return store.state()["workshop"]["WS-001"]


@pytest.fixture
def ws(fixture_org):
    client = _client(fixture_org.path)
    resp = client.post("/workshops", data=SEATED, follow_redirects=False)
    assert resp.status_code == 303 and resp.headers["location"] == "/workshops/WS-001"
    return client, fixture_org.path


def _advance(client, times):
    for _ in range(times):
        assert client.post("/workshops/WS-001/advance", follow_redirects=False).status_code == 303


def test_pre_lists_are_hidden_until_stage_2(ws):
    client, path = ws
    resp = client.post("/workshops/WS-001/participant",
                       data={"participant": "Ola Overseer", "pre_list": "MOD-05 secret worry\nHUM-01"},
                       follow_redirects=False)
    assert resp.status_code == 303
    for page in ("/workshops/WS-001", "/workshops/WS-001/record", "/workshops/WS-001/participant"):
        assert "secret worry" not in client.get(page).text, page
    assert "1 list received" in client.get("/workshops/WS-001").text
    _advance(client, 1)
    text = client.get("/workshops/WS-001").text
    review = text.split('id="stage-2"')[1].split('id="stage-3"')[0]
    assert "secret worry" in review and "Ola Overseer" not in review    # anonymised


def test_pre_lists_close_at_stage_2(ws):
    client, _ = ws
    _advance(client, 1)
    resp = client.post("/workshops/WS-001/participant",
                       data={"participant": "Ann Owner", "pre_list": "MOD-05"})
    assert resp.status_code == 409


def test_all_23_prompts_render_with_their_lines(ws):
    client, _ = ws
    _advance(client, 2)
    text = client.get("/workshops/WS-001").text
    assert text.count('class="swift-prompt"') == 23
    assert "What if the vendor changes the model behind the service and does not tell us?" in text
    assert "MOD-05" in text and "OPS-03, HUM-06" in text


def test_answers_store_covered_or_not_known_with_control_and_evidence(ws):
    client, path = ws
    assert client.post("/workshops/WS-001/swift/1", data={"status": "covered"}).status_code == 409
    _advance(client, 2)
    resp = client.post("/workshops/WS-001/swift/1",
                       data={"status": "covered", "control": "version pinning",
                             "evidence": "release checklist RC-12"}, follow_redirects=False)
    assert resp.status_code == 303
    client.post("/workshops/WS-001/swift/6", data={"status": "not known"})
    refused = client.post("/workshops/WS-001/swift/4", data={"status": "covered"})
    assert refused.status_code == 422 and "Covered needs the control and its evidence" in refused.text
    answers = _workshop(path)["swift_answers"]
    assert answers["1"] == {"status": "covered", "control": "version pinning",
                            "evidence": "release checklist RC-12", "note": None}
    assert answers["6"]["status"] == "not known" and "4" not in answers


def test_votes_are_per_participant_and_the_record_has_no_average(ws):
    client, path = ws
    client.post("/workshops/WS-001/participant", data={"participant": "Ann Owner", "pre_list": "MOD-05"})
    _advance(client, 2)
    client.post("/workshops/WS-001/swift/6", data={"status": "not known"})
    _advance(client, 2)                                   # to stage 5, multivoting
    client.post("/workshops/WS-001/participant",
                data={"participant": "Ann Owner", "vote_MOD-05": "5"})
    client.post("/workshops/WS-001/participant",
                data={"participant": "Ola Overseer", "vote_HUM-01": "1"})
    client.post("/workshops/WS-001/participant",
                data={"participant": "Sid Sceptic", "vote_HUM-01": "1"})
    over = client.post("/workshops/WS-001/participant",
                       data={"participant": "Sid Sceptic", "vote_HUM-01": "9"})
    assert over.status_code == 422
    assert _workshop(path)["votes"] == {"Ann Owner": {"MOD-05": 5}, "Ola Overseer": {"HUM-01": 1},
                                        "Sid Sceptic": {"HUM-01": 1}}
    record = client.get("/workshops/WS-001/record").text
    multivote = record.split('id="stage-5"')[1].split('id="stage-6"')[0]
    # SWIFT prompt 11 says "on average", so the check is on the multivoting record.
    assert not re.search(r"\b(average|mean)\b", multivote, re.I)
    assert multivote.index("HUM-01") < multivote.index("MOD-05")    # two voters outrank one
    assert "Ann Owner" in multivote and "Ola Overseer" in multivote


def test_record_renders_every_stage(ws):
    client, _ = ws
    record = client.get("/workshops/WS-001/record")
    assert record.status_code == 200
    for n in range(1, 7):
        assert f'id="stage-{n}"' in record.text
    for name in ("Opening", "Independent assessment review", "SWIFT rounds",
                 "Emerging risk session", "Multivoting", "Gap review"):
        assert name in record.text


def test_close_makes_top_down_candidates_from_voted_lines(ws):
    client, path = ws
    client.post("/workshops/WS-001/participant", data={"participant": "Ann Owner", "pre_list": "MOD-05"})
    client.post("/library/adopt", data={"line_id": "HUM-01", "system_id": "SYS-001"})
    _advance(client, 2)
    client.post("/workshops/WS-001/swift/6", data={"status": "not known"})
    _advance(client, 1)
    client.post("/workshops/WS-001/emerging", data={"title": "Agents that book travel", "note": ""})
    _advance(client, 1)
    client.post("/workshops/WS-001/participant", data={"participant": "Ann Owner",
                                                       "vote_MOD-05": "2", "vote_HUM-01": "1",
                                                       "vote_E1": "2"})
    _advance(client, 1)
    client.post("/workshops/WS-001/gap", data={"gap_review": "Agents fit no node."})
    resp = client.post("/workshops/WS-001/close", follow_redirects=False)
    assert resp.status_code == 303
    with Store(path) as store:
        register = store.state()["register"]
    assert register["MOD-05"]["source"] == "top-down"           # new from the workshop
    assert register["HUM-01"]["source"] == "library"             # already there, not entered twice
    assert "E1" not in register                                  # emerging risks go to the gap list
    assert _workshop(path)["status"] == "closed"
    assert client.post("/workshops/WS-001/swift/2", data={"status": "not known"}).status_code == 409


def test_workshops_list_and_errors(fixture_org):
    client = _client(fixture_org.path)
    assert "No workshops yet" in client.get("/workshops").text
    assert client.post("/workshops", data=dict(SEATED, system_ids="SYS-404")).status_code == 422
    assert client.post("/workshops", data=dict(SEATED, facilitator="")).status_code == 422
    assert client.get("/workshops/WS-404").status_code == 404


# --- fixes from the interim review -------------------------------------------

def test_attendance_is_recorded_and_absent_seats_do_not_take_part(fixture_org):
    client = _client(fixture_org.path)
    client.post("/workshops", data=dict(SEATED, seat_6_absent="on"))
    seats = {s["person"]: s["present"] for s in _workshop(fixture_org.path)["seats"]}
    assert seats == {"Ann Owner": True, "Ola Overseer": True, "Sid Sceptic": False}
    refused = client.post("/workshops/WS-001/participant",
                          data={"participant": "Sid Sceptic", "pre_list": "MOD-05"})
    assert refused.status_code == 422
    client.post("/workshops/WS-001/attendance", data={"present_0": "on", "present_2": "on"})
    seats = {s["person"]: s["present"] for s in _workshop(fixture_org.path)["seats"]}
    assert seats == {"Ann Owner": True, "Ola Overseer": False, "Sid Sceptic": True}
    assert "absent" in client.get("/workshops/WS-001/record").text
    _advance(client, 1)
    assert client.post("/workshops/WS-001/attendance", data={}).status_code == 409


def test_where_they_disagree_counts_lists(ws):
    client, _ = ws
    client.post("/workshops/WS-001/participant", data={"participant": "Ann Owner",
                                                       "pre_list": "MOD-05\nHUM-01"})
    client.post("/workshops/WS-001/participant", data={"participant": "Ola Overseer",
                                                       "pre_list": "MOD-05"})
    _advance(client, 1)
    review = client.get("/workshops/WS-001").text.split('id="stage-2"')[1].split('id="stage-3"')[0]
    assert "1 of 2 lists" in review and "2 of 2 lists (all agree)" in review
    table = review.split("Where they disagree")[1]
    assert table.index("HUM-01") < table.index("MOD-05")        # disagreement first


def test_a_top_down_line_goes_to_a_system_it_was_proposed_for(fixture_org):
    client = _client(fixture_org.path)
    client.post("/workshops", data={"system_ids": ["SYS-001", "SYS-003"], "date": "2026-11-20",
                                    "facilitator": "Fiona", "vote_allowance": "5", "seat_1": "Ann"})
    client.post("/workshops/WS-001/participant", data={"participant": "Ann", "pre_list": "MOD-08"})
    _advance(client, 4)
    client.post("/workshops/WS-001/participant", data={"participant": "Ann", "vote_MOD-08": "2"})
    _advance(client, 1)
    client.post("/workshops/WS-001/close")
    with Store(fixture_org.path) as store:
        assert store.state()["register"]["MOD-08"]["system_id"] == "SYS-003"   # not the first, SYS-001


def test_the_stage_event_names_the_stage_entered(ws):
    client, path = ws
    _advance(client, 1)
    with Store(path) as store:
        reason = store._conn.execute("SELECT reason FROM events WHERE entity = 'workshop' "
                                     "AND field = 'stage'").fetchone()[0]
    assert reason == "stage 2: Independent assessment review"
