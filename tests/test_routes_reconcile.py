"""Round 8 Reconcile (PLAN.md round 8; SPEC.md 6.6; chapter 8).

The plan's checks: a candidate with no matching line shows as a gap; a line
with no submission shows as a gap; resolving requires a reason and records
who; the disagreement log lists the minority score and the dimension. Also:
the match on taxonomy node and system, blind spots from the starting
universe, the five dispositions and their effect on the register, the
workshop's seat differences as the challenge agenda, and the signed record.
"""

import pytest
from fastapi.testclient import TestClient

from riskid.app import create_app
from riskid.store import Store

BASE = "http://127.0.0.1:8765"
USECASE = {  # a bottom-up submission at MOD-05's node, 2.3, for SYS-001
    "system_id": "SYS-001", "taxonomy": "2.3", "owner": "Aoife Byrne",
    "definition": "The supplier swaps the model and our cut-offs stop holding",
    "drivers_direct": "The contract allows changes without notice", "data_quality": "Low",
}


def _client(path):
    return TestClient(create_app(path, actor="tester"), base_url=BASE)


def _state(path):
    with Store(path) as store:
        return store.state()


def _workshop_voting(client, votes):
    """Run WS-001 for SYS-001 to the close, with the given votes from Ann (business owner)."""
    client.post("/workshops", data={"system_ids": "SYS-001", "date": "2026-11-20",
                                    "facilitator": "Fiona", "vote_allowance": "5",
                                    "seat_1": "Ann", "seat_5": "Ola"})
    client.post("/workshops/WS-001/participant", data={"participant": "Ann",
                                                       "pre_list": "\n".join(votes)})
    for _ in range(4):
        client.post("/workshops/WS-001/advance")
    client.post("/workshops/WS-001/participant",
                data={"participant": "Ann", **{f"vote_{v}": "1" for v in votes}})
    client.post("/workshops/WS-001/participant", data={"participant": "Ola", f"vote_{votes[0]}": "2"})
    client.post("/workshops/WS-001/advance")
    client.post("/workshops/WS-001/close")


def test_a_bottom_up_candidate_with_no_matching_line_is_a_gap(fixture_org):
    client = _client(fixture_org.path)
    client.post("/usecases", data=USECASE)                     # ORG-001, nothing top-down
    gap = client.get("/reconcile").text.split('id="gap"')[1].split('id="challenge"')[0]
    assert "ORG-001" in gap and "no top-down line at this node" in gap


def test_a_line_with_no_submission_is_a_gap(fixture_org):
    client = _client(fixture_org.path)
    client.post("/library/adopt", data={"line_id": "HUM-01", "system_id": "SYS-001"})
    gap = client.get("/reconcile").text.split('id="gap"')[1].split('id="challenge"')[0]
    assert "HUM-01" in gap and "no submission" in gap


def test_top_down_and_bottom_up_match_on_node_and_system(fixture_org):
    client = _client(fixture_org.path)
    _workshop_voting(client, ["MOD-05"])                        # top-down MOD-05, node 2.3
    client.post("/usecases", data=USECASE)                      # bottom-up ORG-001, node 2.3
    text = client.get("/reconcile").text
    match = text.split('id="match"')[1].split('id="gap"')[0]
    assert "MOD-05" in match and "UC-001" in match and "ORG-001" in match
    gap = text.split('id="gap"')[1].split('id="challenge"')[0]
    assert "MOD-05" not in gap and "ORG-001" not in gap


def test_resolving_requires_a_reason_and_records_who(fixture_org):
    client = _client(fixture_org.path)
    client.post("/library/adopt", data={"line_id": "HUM-01", "system_id": "SYS-001"})
    refused = client.post("/reconcile/resolve", data={"subject": "HUM-01", "disposition": "local",
                                                      "reason": ""})
    assert refused.status_code == 422 and "give the reason" in refused.text
    resp = client.post("/reconcile/resolve", data={
        "subject": "HUM-01", "disposition": "local",
        "reason": "only the credit model has human reviewers"}, follow_redirects=False)
    assert resp.status_code == 303
    state = _state(fixture_org.path)
    resolution = state["resolution"]["HUM-01"]
    assert (resolution["disposition"], resolution["decided_by"]) == ("local", "tester")
    assert resolution["reason"] == "only the credit model has human reviewers" and resolution["date"]
    assert state["register"]["HUM-01"]["status"] == "active"
    gap = client.get("/reconcile").text.split('id="gap"')[1].split('id="challenge"')[0]
    assert "accepted as local" in gap


def test_close_as_not_applicable_retires_and_merge_needs_a_target(fixture_org):
    client = _client(fixture_org.path)
    for line in ("HUM-01", "HUM-02"):
        client.post("/library/adopt", data={"line_id": line, "system_id": "SYS-001"})
    no_target = client.post("/reconcile/resolve", data={"subject": "HUM-02", "disposition": "merge",
                                                        "reason": "same risk"})
    assert no_target.status_code == 422 and "name the line it merges into" in no_target.text
    client.post("/reconcile/resolve", data={"subject": "HUM-02", "disposition": "merge",
                                            "reason": "same risk", "target": "HUM-01"})
    client.post("/reconcile/resolve", data={"subject": "HUM-01", "disposition": "not applicable",
                                            "reason": "no human review in this process"})
    register = _state(fixture_org.path)["register"]
    assert register["HUM-02"]["status"] == "retired"
    assert register["HUM-02"]["retired_reason"].startswith("merged into HUM-01")
    assert register["HUM-01"]["status"] == "retired"


def test_blind_spots_need_a_recorded_reason(fixture_org):
    client = _client(fixture_org.path)
    gap = client.get("/reconcile").text.split('id="gap"')[1].split('id="challenge"')[0]
    assert "SEC-04" in gap and "blind spot" in gap.lower()
    client.post("/reconcile/resolve", data={"subject": "SEC-04", "disposition": "not applicable",
                                            "reason": "no system reads a knowledge base"})
    state = _state(fixture_org.path)
    assert state["resolution"]["SEC-04"]["reason"] == "no system reads a knowledge base"
    assert "SEC-04" not in state.get("register", {})
    client.post("/reconcile/resolve", data={"subject": "SEC-07", "disposition": "add",
                                            "reason": "not previously considered"})
    added = _state(fixture_org.path)["register"]["SEC-07"]
    assert (added["status"], added["source"], added["system_id"]) == ("active", "library", "SYS-001")


def test_the_disagreement_log_lists_the_minority_score_and_the_dimension(fixture_org):
    client = _client(fixture_org.path)
    client.post("/library/adopt", data={"line_id": "HUM-01", "system_id": "SYS-001"})
    resp = client.post("/reconcile/disagreements", data={
        "line_id": "HUM-01", "holder": "Ola, overseer", "majority_score": "2",
        "minority_score": "4", "dimension": "IND",
        "evidence": "override rate fell to 0.3% in Q3"}, follow_redirects=False)
    assert resp.status_code == 303
    entry = _state(fixture_org.path)["disagreement"]["DL-001"]
    assert (entry["minority_score"], entry["dimension"], entry["status"]) == (4, "IND", "open")
    log = client.get("/reconcile").text.split('id="challenge"')[1].split('id="resolve"')[0]
    assert "DL-001" in log and "HUM-01" in log and "IND" in log and ">4<" in log
    for bad in ({"minority_score": "6"}, {"dimension": "XYZ"}, {"line_id": "NOPE-01"}):
        data = {"line_id": "HUM-01", "holder": "Ola", "minority_score": "4", "dimension": "IND",
                "evidence": "x", **bad}
        assert client.post("/reconcile/disagreements", data=data).status_code == 422


def test_resolving_a_disagreement_closes_it(fixture_org):
    client = _client(fixture_org.path)
    client.post("/library/adopt", data={"line_id": "HUM-01", "system_id": "SYS-001"})
    client.post("/reconcile/disagreements", data={"line_id": "HUM-01", "holder": "Ola",
                                                  "minority_score": "4", "dimension": "IND",
                                                  "evidence": "override log"})
    client.post("/reconcile/resolve", data={"subject": "DL-001", "disposition": "escalate",
                                            "reason": "evidence supports the overseer"})
    assert _state(fixture_org.path)["disagreement"]["DL-001"]["status"] == "resolved"


def test_workshop_seat_differences_are_the_challenge_agenda(fixture_org):
    client = _client(fixture_org.path)
    _workshop_voting(client, ["MOD-05", "HUM-01"])              # Ann votes both; Ola only MOD-05
    challenge = client.get("/reconcile").text.split('id="challenge"')[1].split('id="resolve"')[0]
    assert "WS-001" in challenge and "Overseer" in challenge and "HUM-01" in challenge


def test_record_a_signed_pass(fixture_org):
    client = _client(fixture_org.path)
    refused = client.post("/reconcile/record", data={"present": "Ann, Ola", "signed_by": ""})
    assert refused.status_code == 422
    client.post("/reconcile/record", data={"present": "Ann, Ola", "signed_by": "Chief Financial Officer"})
    run = _state(fixture_org.path)["reconciliation"]["RC-001"]
    assert run["signed_by"] == "Chief Financial Officer" and run["present"] == ["Ann", "Ola"]
    assert "open_gaps" in run["counts"]
    record = client.get("/reconcile").text.split('id="record"')[1]
    assert "RC-001" in record and "Chief Financial Officer" in record


def test_reconcile_renders_for_an_empty_organisation(tmp_path):
    from riskid.store import init
    init(tmp_path / "e.riskid").close()
    resp = _client(tmp_path / "e.riskid").get("/reconcile")
    assert resp.status_code == 200
    for section in ("match", "gap", "challenge", "resolve", "record"):
        assert f'id="{section}"' in resp.text


def test_retired_lines_and_closed_disagreements_are_not_resolved_again(fixture_org):
    client = _client(fixture_org.path)
    client.post("/library/adopt", data={"line_id": "HUM-01", "system_id": "SYS-001"})
    client.post("/reconcile/resolve", data={"subject": "HUM-01", "disposition": "not applicable",
                                            "reason": "no human review"})
    again = client.post("/reconcile/resolve", data={"subject": "HUM-01", "disposition": "add",
                                                    "reason": "changed my mind"})
    assert again.status_code == 422 and "is retired" in again.text
    client.post("/library/adopt", data={"line_id": "HUM-02", "system_id": "SYS-001"})
    client.post("/reconcile/disagreements", data={"line_id": "HUM-02", "holder": "Ola",
                                                  "minority_score": "4", "dimension": "IND"})
    client.post("/reconcile/resolve", data={"subject": "DL-001", "disposition": "local", "reason": "r"})
    twice = client.post("/reconcile/resolve", data={"subject": "DL-001", "disposition": "local",
                                                    "reason": "r"})
    assert twice.status_code == 422 and "already resolved" in twice.text


def test_add_needs_a_known_system(fixture_org):
    resp = _client(fixture_org.path).post("/reconcile/resolve", data={
        "subject": "SEC-05", "disposition": "add", "reason": "found in an audit", "system_id": "SYS-404"})
    assert resp.status_code == 422 and "choose the system" in resp.text
