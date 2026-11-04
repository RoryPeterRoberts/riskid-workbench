"""Round 9 Assess screens (PLAN.md round 9; SPEC.md 6.7; B.6).

The plan's checks: inherent, band and materiality shown match `rules`;
residual pickers are locked until a control has a test result; the record
view has the seven fields of B.6; the heat map PNG renders for the fixture and
places each line in the right cell. Also the controls table and its tests,
the disagreement going to the log, and the escalation of a speed or
vulnerability of 5.
"""

import pytest
from fastapi.testclient import TestClient

from riskid import rules
from riskid.app import create_app
from riskid.store import Store

BASE = "http://127.0.0.1:8765"
FORM = {"harm_scored": "wrongful refusals of credit", "unit_of_exposure": "applications per year",
        "impact_FIN": "2", "impact_REG": "3", "impact_REP": "2", "impact_IND": "4", "impact_OPS": "1",
        "likelihood": "3", "vulnerability": "3", "speed": "2", "data_quality": "Medium",
        "data_quality_basis": "partial test results on our own applications"}


@pytest.fixture
def org(fixture_org):
    client = TestClient(create_app(fixture_org.path, actor="tester"), base_url=BASE)
    for line in ("HUM-01", "MOD-05"):
        client.post("/library/adopt", data={"line_id": line, "system_id": "SYS-001"})
    return client, fixture_org.path


def _state(path):
    with Store(path) as store:
        return store.state()


def test_inherent_band_and_materiality_shown_match_the_rules(org):
    client, path = org
    resp = client.post("/assess/HUM-01", data=FORM, follow_redirects=False)
    assert resp.status_code == 303
    (as_id, a), = _state(path)["assessment"].items()
    assert (a["line_id"], a["inherent"], a["inherent_band"], a["material"]) == (
        "HUM-01", rules.score(3, 4), rules.band(12), rules.material(12, 4))
    listing = client.get("/assess").text
    row = next(r for r in listing.split("<tr>") if 'href="/assess/HUM-01"' in r)
    assert ">12<" in row and "High" in row and "not material" in row


def test_residual_pickers_are_locked_until_a_control_has_a_test_result(org):
    client, path = org
    form = client.get("/assess/HUM-01").text
    assert 'name="residual_L" disabled' in form and "locked" in form
    lowered = dict(FORM, residual_L="2", residual_I="4",
                   data_quality_basis="Override-rate monitoring test, 2026-10-01")
    refused = client.post("/assess/HUM-01", data=lowered)
    assert refused.status_code == 422 and "locked at the inherent" in refused.text
    client.post("/assess/HUM-01/controls", data={"name": "Override-rate monitoring",
                                                 "type": "detective", "owner": "Head of Credit Ops"})
    still = client.get("/assess/HUM-01").text
    assert 'name="residual_L" disabled' in still                 # no test result yet
    client.post("/assess/HUM-01/controls/CT-001/test",
                data={"test_date": "2026-10-01", "outcome": "passed", "test_result": "overrides 4.1%"})
    assert 'name="residual_L" disabled' not in client.get("/assess/HUM-01").text
    assert client.post("/assess/HUM-01", data=lowered, follow_redirects=False).status_code == 303
    latest = sorted(_state(path)["assessment"].items())[-1][1]
    assert (latest["residual_L"], latest["residual_I"], latest["residual"]) == (2, 4, 8)


def test_the_record_view_has_the_seven_fields_of_b6(org):
    client, _ = org
    client.post("/assess/HUM-01", data=FORM)
    record = client.get("/assess/HUM-01/record")
    assert record.status_code == 200
    for n, field in enumerate(("Inherent risk score", "Control effectiveness", "Residual risk score",
                               "Data quality rating", "Materiality", "Model and vendor dependency",
                               "Disagreement record"), start=1):
        assert f"{n}. {field}" in record.text
    assert client.get("/assess/MOD-05/record").status_code == 404     # not assessed yet


def test_heat_map_renders_for_the_fixture_and_places_each_line(org):
    client, _ = org
    client.post("/assess/HUM-01", data=FORM)                         # L3, I4
    client.post("/assess/MOD-05", data=dict(FORM, likelihood="4", impact_IND="5"))  # L4, I5
    page = client.get("/assess").text
    inherent = page.split('id="cells-inherent"')[1].split("</table>")[0]
    assert "HUM-01" in inherent.split('data-cell="3,4"')[1].split("</td>")[0]
    assert "MOD-05" in inherent.split('data-cell="4,5"')[1].split("</td>")[0]
    png = client.get("/assess/heatmap/inherent.png")
    assert png.status_code == 200 and png.headers["content-type"] == "image/png"
    assert png.content[:8] == b"\x89PNG\r\n\x1a\n"
    assert client.get("/assess/heatmap/residual.png").status_code == 200
    assert client.get("/assess/heatmap/other.png").status_code == 404


def test_scales_are_pickers_with_their_descriptions(org):
    text = org[0].get("/assess/HUM-01").text
    assert "More than 15%, or threatens the viability of the organisation" in text   # FIN 5
    assert "Frequent" in text and "Immediate" in text                              # likelihood, speed
    assert "Chapter 9" in text and "B.6" in text


def test_a_disagreement_in_the_assessment_goes_to_the_log(org):
    client, path = org
    client.post("/assess/HUM-01", data=dict(FORM, minority_holder="Ola, overseer", minority_score="5",
                                            minority_dimension="IND", minority_evidence="complaints"))
    entry = _state(path)["disagreement"]["DL-001"]
    assert (entry["line_id"], entry["raised_in"], entry["minority_score"]) == ("HUM-01", "AS-001", 5)


def test_speed_or_vulnerability_of_5_escalates(org):
    client, _ = org
    client.post("/assess/HUM-01", data=dict(FORM, speed="5"))
    assert "in front of the owner this week" in client.get("/assess").text


def test_controls_are_checked(org):
    client, path = org
    assert client.post("/assess/HUM-01/controls", data={"name": "", "type": "detective"}).status_code == 422
    assert client.post("/assess/HUM-01/controls", data={"name": "x", "type": "magic"}).status_code == 422
    client.post("/assess/HUM-01/controls", data={"name": "Blind re-checks", "type": "detective",
                                                 "annex_a_ref": "A.9.3"})
    bad = client.post("/assess/HUM-01/controls/CT-001/test", data={"test_date": "01/10/2026",
                                                                    "outcome": "passed"})
    assert bad.status_code == 422
    assert client.post("/assess/HUM-01/controls/CT-001/test",
                       data={"test_date": "2026-10-01", "outcome": ""}).status_code == 422
    client.post("/assess/HUM-01/controls/CT-001/test",
                data={"test_date": "2026-10-01", "outcome": "failed", "test_result": "missed 3 of 5"})
    assert 'name="residual_L" disabled' in client.get("/assess/HUM-01").text   # a failure unlocks nothing
    control = _state(path)["control"]["CT-001"]
    assert (control["line_id"], control["annex_a_ref"], control["last_test_result"]) == (
        "HUM-01", "A.9.3", "failed: missed 3 of 5")


def test_unknown_or_retired_lines(org):
    client, path = org
    assert client.get("/assess/NOPE-01").status_code == 404
    assert client.post("/assess/NOPE-01", data=FORM).status_code == 404
    client.post("/reconcile/resolve", data={"subject": "MOD-05", "disposition": "not applicable",
                                            "reason": "pinned version"})
    assert client.post("/assess/MOD-05", data=FORM).status_code == 409


def test_assess_renders_for_an_empty_organisation(tmp_path):
    from riskid.store import init
    init(tmp_path / "e.riskid").close()
    client = TestClient(create_app(tmp_path / "e.riskid", actor="t"), base_url=BASE)
    assert client.get("/assess").status_code == 200
    assert client.get("/assess/heatmap/inherent.png").status_code == 200
