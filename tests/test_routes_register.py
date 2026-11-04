"""Round 11 Register (PLAN.md round 11; SPEC.md 6.9; B.3; chapter 11).

The plan's checks: the grid shows the fixture's live lines and not retired
ones; a profile shows every assessment and control with dates and actors;
replay to a date before a change shows the earlier score. Also: the 14 + 5
columns of B.3, the trend, editing the owner and COSO category with a reason,
retiring with a reason, and chapter 11's signs of a living inventory.
"""

import pytest
from fastapi.testclient import TestClient

from riskid.app import create_app
from riskid.model import Assessment, Event
from riskid.store import Store

BASE = "http://127.0.0.1:8765"
FORM = {"harm_scored": "wrongful refusals", "unit_of_exposure": "applications a year",
        "impact_FIN": "2", "impact_REG": "3", "impact_REP": "2", "impact_IND": "4", "impact_OPS": "1",
        "likelihood": "3", "vulnerability": "3", "speed": "2", "data_quality": "Medium",
        "data_quality_basis": "partial tests on our own applications"}
B3_COLUMNS = ("Risk ID", "Taxonomy", "Risk definition", "COSO", "Risk owner", "Inherent",
              "Controls", "Residual", "Material", "Data quality", "Interactions", "Indicators",
              "Trend", "Review", "Lifecycle", "Role", "Persons affected", "Regulatory hooks",
              "Annex A")


@pytest.fixture
def org(fixture_org):
    client = TestClient(create_app(fixture_org.path, actor="tester"), base_url=BASE)
    for line in ("HUM-01", "MOD-05"):
        client.post("/library/adopt", data={"line_id": line, "system_id": "SYS-001"})
    return client, fixture_org.path


def test_the_grid_shows_live_lines_and_not_retired_ones(org):
    client, _ = org
    client.post("/reconcile/resolve", data={"subject": "MOD-05", "disposition": "not applicable",
                                            "reason": "the version is pinned by contract"})
    grid = client.get("/register").text.split('id="grid"')[1].split("</table>")[0]
    assert 'href="/register/HUM-01"' in grid and 'href="/register/MOD-05"' not in grid
    for column in B3_COLUMNS:
        assert column in grid, column
    retired = client.get("/register").text.split('id="retired"')[1]
    assert "MOD-05" in retired and "the version is pinned by contract" in retired


def test_a_profile_shows_every_assessment_and_control_with_dates_and_actors(org):
    client, _ = org
    client.post("/assess/HUM-01/controls", data={"name": "Override-rate monitoring", "type": "detective"})
    client.post("/assess/HUM-01/controls/CT-001/test",
                data={"test_date": "2026-10-01", "outcome": "passed", "test_result": "4.1%"})
    client.post("/assess/HUM-01", data=FORM)
    client.post("/assess/HUM-01", data=dict(FORM, likelihood="4"))
    profile = client.get("/register/HUM-01")
    assert profile.status_code == 200
    text = profile.text
    for needle in ("AS-001", "AS-002", "CT-001", "Override-rate monitoring", "2026-10-01", "tester"):
        assert needle in text, needle
    trail = text.split('id="trail"')[1]
    assert "assessment of HUM-01" in trail and "control test recorded" in trail
    assert client.get("/register/NOPE-01").status_code == 404


def test_replay_to_a_date_before_a_change_shows_the_earlier_score(org):
    client, path = org
    from riskid import importers
    from riskid.propose import register_line_from_library
    tra02 = next(line for line in importers.load_library() if line.id == "TRA-02")
    with Store(path) as store:      # TRA-02 adopted and assessed in June, stamped in June
        store.append(Event(entity="register", entity_id="TRA-02", actor="ann", reason="adopted",
                           new=register_line_from_library(tra02, "SYS-001").to_dict(),
                           timestamp="2026-06-01T09:00:00Z"))
        june = Assessment(line_id="TRA-02", date="2026-06-01", assessor="ann", impact={"IND": 4},
                          dominant_dimension="IND", likelihood=2, inherent=8, inherent_band="Moderate",
                          residual_L=2, residual_I=4, residual=8, data_quality="Low",
                          data_quality_basis="workshop judgement")
        store.append(Event(entity="assessment", entity_id="AS-001", new=june.to_dict(), actor="ann",
                           timestamp="2026-06-01T10:00:00Z", reason="assessment of TRA-02"))
    client.post("/assess/TRA-02", data=dict(FORM, likelihood="4"))      # today: 4 x 4 = 16
    live = client.get("/register").text.split('id="grid"')[1]
    then = client.get("/register", params={"as_of": "2026-06-30"})
    assert then.status_code == 200
    grid_then = then.text.split('id="grid"')[1]

    def row(grid):
        return next(r for r in grid.split("<tr>") if 'href="/register/TRA-02"' in r)

    assert ">16<" in row(live) and ">8<" in row(grid_then) and ">16<" not in row(grid_then)
    assert "as it stood on 2026-06-30" in then.text
    assert "MOD-05" not in grid_then          # adopted today, not yet in the register in June
    assert client.get("/register", params={"as_of": "30/06/2026"}).status_code == 422


def test_trend_compares_the_last_two_assessments(org):
    client, _ = org
    client.post("/assess/HUM-01", data=FORM)
    row = next(r for r in client.get("/register").text.split("<tr>") if 'href="/register/HUM-01"' in r)
    assert "new" in row
    client.post("/assess/HUM-01", data=dict(FORM, likelihood="4"))
    row = next(r for r in client.get("/register").text.split("<tr>") if 'href="/register/HUM-01"' in r)
    assert "increasing" in row


def test_owner_and_coso_category_are_edited_with_a_reason(org):
    client, path = org
    resp = client.post("/register/HUM-01", data={"owner": "Aoife Byrne, Head of Lending",
                                                 "coso_category": "operations",
                                                 "change_reason": "owner named at reconciliation"},
                       follow_redirects=False)
    assert resp.status_code == 303
    with Store(path) as store:
        line = store.state()["register"]["HUM-01"]
        events = store._conn.execute("SELECT field, reason, actor FROM events WHERE entity = 'register' "
                                     "AND entity_id = 'HUM-01' AND field IS NOT NULL").fetchall()
    assert (line["owner"], line["coso_category"]) == ("Aoife Byrne, Head of Lending", "operations")
    assert {(f, r, a) for f, r, a in events} == {("owner", "owner named at reconciliation", "tester"),
                                                ("coso_category", "owner named at reconciliation", "tester")}
    assert client.post("/register/HUM-01", data={"coso_category": "vibes"}).status_code == 422
    assert client.post("/register/HUM-01", data={"owner": "", "change_reason": "x"}).status_code == 422


def test_retiring_needs_a_reason_and_keeps_the_line(org):
    client, path = org
    assert client.post("/register/HUM-01/retire", data={"reason": ""}).status_code == 422
    client.post("/register/HUM-01/retire", data={"reason": "the process is closed"})
    with Store(path) as store:
        assert store.state()["register"]["HUM-01"]["status"] == "retired"
    assert client.get("/register/HUM-01").status_code == 200      # the profile and trail remain
    assert client.post("/register/HUM-01/retire", data={"reason": "again"}).status_code == 409


def test_signs_of_a_living_inventory(org):
    client, _ = org
    client.post("/assess/HUM-01", data=FORM)
    signs = client.get("/register").text.split('id="signs"')[1].split("</section>")[0]
    for sign in ("owner", "Medium", "interaction", "disagreement log", "review dates"):
        assert sign in signs, sign


def test_register_renders_for_an_empty_organisation(tmp_path):
    from riskid.store import init
    init(tmp_path / "e.riskid").close()
    client = TestClient(create_app(tmp_path / "e.riskid", actor="t"), base_url=BASE)
    assert client.get("/register").status_code == 200
    assert client.get("/register", params={"as_of": "2026-01-01"}).status_code == 200
