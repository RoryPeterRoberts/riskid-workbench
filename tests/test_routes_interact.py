"""Round 10 Interact (PLAN.md round 10; SPEC.md 6.8; chapter 10).

The plan's checks: an interaction is stored with its kind; a bow-tie saves
causes, controls and consequences; the concentration view counts systems per
vendor and per model. Also: the matrix is not symmetric, a link needs its
mechanism, a cell can be cleared without deleting, propagation and
vulnerable nodes, candidate links from shared controls, hidden concentration.
"""

import pytest
from fastapi.testclient import TestClient

from riskid.app import create_app
from riskid.store import Store

BASE = "http://127.0.0.1:8765"
LINK = {"from_line": "MOD-05", "to_line": "HUM-01", "kind": "amplifies",
        "mechanism": "degraded output reaches reviewers who have stopped checking",
        "delay": "days"}
BOWTIE = {"line_id": "HUM-01", "owner": "Head of Lending Operations",
          "event": "Wrong decisions about individuals are issued at volume and stay uncorrected",
          "cause_1": "The vendor replaces the model behind the API (MOD-05)",
          "preventive_1": "Contractual notice; version pinning; regression suite on every version",
          "cause_2": "Inputs drift away from the training data (DAT-05, MOD-06)",
          "preventive_2": "Drift thresholds on input data",
          "consequence_1": "Wrong decisions about individuals",
          "recovery_1": "Suspend the automated route (Article 26(5)); roll back to the pinned version",
          "escalation_factors": "Automation bias defeats the review barrier"}


@pytest.fixture
def org(fixture_org):
    client = TestClient(create_app(fixture_org.path, actor="tester"), base_url=BASE)
    for line in ("MOD-05", "HUM-01", "TRA-02", "OPS-05"):
        client.post("/library/adopt", data={"line_id": line, "system_id": "SYS-001"})
    return client, fixture_org.path


def _state(path):
    with Store(path) as store:
        return store.state()


def _cell(text, pair):
    return text.split(f'data-pair="{pair}"')[1].split("</td>")[0]


def test_an_interaction_is_stored_with_its_kind(org):
    client, path = org
    resp = client.post("/interact/links", data=LINK, follow_redirects=False)
    assert resp.status_code == 303
    link = _state(path)["interaction"]["MOD-05>HUM-01"]
    assert (link["from_line"], link["to_line"], link["kind"]) == ("MOD-05", "HUM-01", "amplifies")
    assert link["mechanism"].startswith("degraded output") and link["delay"] == "days"
    text = client.get("/interact").text
    assert ">A<" in _cell(text, "MOD-05>HUM-01")
    assert ">A<" not in _cell(text, "HUM-01>MOD-05")          # not symmetric


def test_a_link_needs_its_mechanism_and_real_lines(org):
    client, path = org
    for bad in ({"mechanism": ""}, {"to_line": "MOD-05"}, {"to_line": "NOPE-01"}, {"kind": "causes"}):
        assert client.post("/interact/links", data=dict(LINK, **bad)).status_code == 422, bad
    assert "interaction" not in _state(path)


def test_a_cell_is_changed_or_cleared_without_deleting(org):
    client, path = org
    client.post("/interact/links", data=LINK)
    client.post("/interact/links", data=dict(LINK, kind="triggers"))
    assert _state(path)["interaction"]["MOD-05>HUM-01"]["kind"] == "triggers"
    client.post("/interact/links", data=dict(LINK, kind="none", mechanism="no mechanism found"))
    text = client.get("/interact").text
    # Neither line is material and no live link is left, so the pair leaves the matrix.
    assert 'data-pair="MOD-05>HUM-01"' not in text
    assert _state(path)["interaction"]["MOD-05>HUM-01"]["kind"] == "none"
    with Store(path) as store:
        kinds = [r[0] for r in store._conn.execute(
            "SELECT new FROM events WHERE entity = 'interaction' ORDER BY seq")]
    assert len(kinds) == 3                                       # every judgement kept


def test_propagation_and_vulnerable_nodes(org):
    client, _ = org
    for to_line, kind in (("HUM-01", "amplifies"), ("OPS-05", "triggers")):
        client.post("/interact/links", data=dict(LINK, to_line=to_line, kind=kind))
    client.post("/interact/links", data=dict(LINK, from_line="OPS-05", to_line="HUM-01", kind="amplifies"))
    client.post("/interact/links", data=dict(LINK, from_line="HUM-01", to_line="TRA-02", kind="triggers"))
    nodes = client.get("/interact").text.split('id="nodes"')[1].split("</section>")[0]
    assert "MOD-05" in nodes.split("Propagation")[1] and "HUM-01" in nodes.split("Vulnerable")[1]


def test_a_bow_tie_saves_causes_controls_and_consequences(org):
    client, path = org
    resp = client.post("/interact/bowties", data=BOWTIE, follow_redirects=False)
    assert resp.status_code == 303 and resp.headers["location"] == "/interact/bowties/BT-001"
    bowtie = _state(path)["bowtie"]["BT-001"]
    assert bowtie["causes"] == [BOWTIE["cause_1"], BOWTIE["cause_2"]]
    assert bowtie["preventive_controls"] == [BOWTIE["preventive_1"], BOWTIE["preventive_2"]]
    assert bowtie["consequences"] == [BOWTIE["consequence_1"]]
    assert bowtie["recovery_controls"] == [BOWTIE["recovery_1"]]
    assert (bowtie["event"], bowtie["owner"], bowtie["line_id"]) == (
        BOWTIE["event"], "Head of Lending Operations", "HUM-01")
    view = client.get("/interact/bowties/BT-001").text
    assert 'class="bowtie"' in view and BOWTIE["recovery_1"] in view and BOWTIE["preventive_2"] in view


def test_a_bow_tie_is_checked_and_updated(org):
    client, path = org
    for bad in ({"event": ""}, {"owner": ""}, {"cause_1": "", "cause_2": "", "preventive_1": "",
                                              "preventive_2": ""}, {"consequence_1": ""},
                {"line_id": "NOPE-01"}):
        assert client.post("/interact/bowties", data=dict(BOWTIE, **bad)).status_code == 422, bad
    client.post("/interact/bowties", data=BOWTIE)
    client.post("/interact/bowties/BT-001", data=dict(BOWTIE, consequence_2="Enforcement under the Act",
                                                      recovery_2="Report on the Article 73 clock"))
    assert _state(path)["bowtie"]["BT-001"]["consequences"][1] == "Enforcement under the Act"
    assert client.get("/interact/bowties/BT-404").status_code == 404


def test_concentration_counts_systems_per_vendor_and_per_model(org):
    client, _ = org
    client.post("/inventory", data={"name": "Complaints triage", "owner": "Head of Service",
                                    "role_under_act": "deployer", "article_6_outcome": "no further class",
                                    "supplier": "Northstar Support", "model_provider": "OpenAI",
                                    "model_name": "gpt-4o"})
    conc = client.get("/interact").text.split('id="concentration"')[1].split("</section>")[0]
    model_row = next(r for r in conc.split("<tr>") if "OpenAI gpt-4o" in r)
    assert ">2<" in model_row and "SYS-002" in model_row and "SYS-004" in model_row
    assert "Helix Conversations" in conc and "Meridian Financial Systems" in conc
    assert "hidden concentration" in conc                       # two suppliers, one model


def test_candidate_links_from_a_shared_control(org):
    client, _ = org
    # HUM-01 and TRA-02 both cite Annex A control A.9.3 in their controls.
    candidates = client.get("/interact").text.split('id="candidates"')[1].split("</section>")[0]
    assert "A.9.3" in candidates and "HUM-01" in candidates and "TRA-02" in candidates
    client.post("/interact/links", data=dict(LINK, from_line="HUM-01", to_line="TRA-02", kind="triggers"))
    candidates = client.get("/interact").text.split('id="candidates"')[1].split("</section>")[0]
    assert "A.9.3" not in candidates                            # judged, so no longer a candidate


def test_interact_renders_for_an_empty_organisation(tmp_path):
    from riskid.store import init
    init(tmp_path / "e.riskid").close()
    resp = TestClient(create_app(tmp_path / "e.riskid", actor="t"), base_url=BASE).get("/interact")
    assert resp.status_code == 200
    for section in ("matrix", "nodes", "bowties", "concentration"):
        assert f'id="{section}"' in resp.text
