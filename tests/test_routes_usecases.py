"""Round 6 Use cases (PLAN.md round 6; SPEC.md 6.5, 5.5; template B.2; chapter 7).

The plan's checks: a submission with driver "model error" is returned with the
reason; "human in the loop" with no override figure is returned; Medium data
quality without a basis is returned; a complete submission is accepted and
creates a candidate line with source=bottom-up. Also: returned submissions are
recorded and can be corrected, a register ID is kept where the risk adopts a
library line, the sub-process coverage of chapter 7, and the error cases.
"""

import pytest
from fastapi.testclient import TestClient

from riskid.app import create_app
from riskid.store import Store

BASE = "http://127.0.0.1:8765"

# The rules' own return reasons (riskid/rules.py, SPEC.md 5.5).
DRIVER_REASON = "the driver is empty or a stock phrase; name the specific driver"
OVERRIDE_REASON = "control has no override figure in its evidence"
MEDIUM_REASON = "a Medium data-quality rating needs its basis stated"

COMPLETE = {
    "system_id": "SYS-001",
    "taxonomy": "2.3",
    "definition": "The supplier replaces the model behind the interface without notice "
                  "and our thresholds stop holding",
    "drivers_direct": "The contract allows changes without notice; the version is not pinned",
    "drivers_indirect": "One supplier; no regression suite; nobody reads supplier notices",
    "control_1_name": "Version pinning", "control_1_type": "preventive",
    "control_1_test_date": "2026-09-30", "control_1_evidence": "release checklist RC-12",
    "owner": "Aoife Byrne, Head of Credit Models",
    "data_quality": "Medium",
    "data_quality_basis": "our own regression results exist, the supplier's change history does not",
}


def _client(path):
    return TestClient(create_app(path, actor="tester"), base_url=BASE)


def _state(path):
    with Store(path) as store:
        return store.state()


def test_stock_driver_is_returned_with_the_reason(fixture_org):
    resp = _client(fixture_org.path).post("/usecases", data=dict(COMPLETE, drivers_direct="model error"))
    assert resp.status_code == 422
    assert DRIVER_REASON in resp.text
    usecase = _state(fixture_org.path)["usecase"]["UC-001"]
    assert usecase["status"] == "returned" and DRIVER_REASON in usecase["return_reason"]
    assert "register" not in _state(fixture_org.path)


def test_human_in_the_loop_without_an_override_figure_is_returned(fixture_org):
    data = dict(COMPLETE, control_2_name="Human in the loop", control_2_type="detective",
                control_2_evidence="reviewers sign off each decision")
    resp = _client(fixture_org.path).post("/usecases", data=data)
    assert resp.status_code == 422 and OVERRIDE_REASON in resp.text
    data["control_2_evidence"] = "reviewers overturned 4.1% of decisions in Q3"
    assert _client(fixture_org.path).post("/usecases", data=data).status_code == 200


def test_medium_without_a_basis_is_returned(fixture_org):
    resp = _client(fixture_org.path).post("/usecases", data=dict(COMPLETE, data_quality_basis=""))
    assert resp.status_code == 422 and MEDIUM_REASON in resp.text


def test_complete_submission_creates_a_bottom_up_candidate_line(fixture_org):
    resp = _client(fixture_org.path).post("/usecases", data=COMPLETE, follow_redirects=False)
    assert resp.status_code == 303 and resp.headers["location"] == "/usecases/UC-001"
    state = _state(fixture_org.path)
    usecase = state["usecase"]["UC-001"]
    assert (usecase["status"], usecase["line_id"], usecase["submitted_by"]) == (
        "accepted", "ORG-001", "tester")
    line = state["register"]["ORG-001"]
    assert (line["source"], line["status"], line["system_id"]) == ("bottom-up", "candidate", "SYS-001")
    assert (line["l1"], line["l2"]) == ("MOD", "2.3")
    assert line["owner"] == "Aoife Byrne, Head of Credit Models"
    assert line["definition"].startswith("The supplier replaces the model")


def test_a_returned_submission_is_corrected_on_the_same_record(fixture_org):
    client = _client(fixture_org.path)
    client.post("/usecases", data=dict(COMPLETE, drivers_direct="AI risk"))
    form = client.get("/usecases/UC-001").text
    assert DRIVER_REASON in form and ">AI risk</textarea>" in form
    resp = client.post("/usecases/UC-001", data=COMPLETE, follow_redirects=False)
    assert resp.status_code == 303
    state = _state(fixture_org.path)
    assert state["usecase"]["UC-001"]["status"] == "accepted"
    assert list(state["usecase"]) == ["UC-001"]
    assert state["register"]["ORG-001"]["source"] == "bottom-up"


def test_an_accepted_submission_cannot_be_resubmitted(fixture_org):
    client = _client(fixture_org.path)
    client.post("/usecases", data=COMPLETE)
    assert client.post("/usecases/UC-001", data=COMPLETE).status_code == 409


def test_a_library_id_is_kept(fixture_org):
    resp = _client(fixture_org.path).post(
        "/usecases", data=dict(COMPLETE, risk_id="MOD-05", taxonomy=""), follow_redirects=False)
    assert resp.status_code == 303
    line = _state(fixture_org.path)["register"]["MOD-05"]
    assert (line["source"], line["l1"], line["l2"]) == ("bottom-up", "MOD", "2.3")


def test_a_risk_already_in_the_register_is_supported_not_duplicated(fixture_org):
    client = _client(fixture_org.path)
    client.post("/library/adopt", data={"line_id": "MOD-05", "system_id": "SYS-001"})
    client.post("/usecases", data=dict(COMPLETE, risk_id="MOD-05"))
    state = _state(fixture_org.path)
    assert state["usecase"]["UC-001"]["line_id"] == "MOD-05"
    assert state["register"]["MOD-05"]["source"] == "library"
    assert list(state["register"]) == ["MOD-05"]


@pytest.mark.parametrize("change, reason", [
    ({"risk_id": "XYZ-99"}, "Risk ID: use a library or register ID"),
    ({"taxonomy": ""}, "Taxonomy classification: choose the Level 2 code"),
    ({"risk_id": "MOD-05", "taxonomy": "1.1"}, "MOD-05 is filed under 2.3"),
    ({"definition": ""}, "Risk definition: say what could happen"),
    ({"owner": ""}, "Risk owner: name one person"),
    ({"data_quality": ""}, "Data quality rating: choose High, Medium, Low or Very Low"),
    ({"control_1_type": "magic"}, "Control 1: the type is preventive, detective or corrective"),
])
def test_template_completeness_is_returned(fixture_org, change, reason):
    resp = _client(fixture_org.path).post("/usecases", data=dict(COMPLETE, **change))
    assert resp.status_code == 422 and reason in resp.text


def test_form_shows_mod05_examples_and_the_inventory_header(fixture_org):
    text = _client(fixture_org.path).get("/usecases/new", params={"system": "SYS-001"}).text
    assert 'placeholder="The contract allows changes without notice; the version is not pinned"' in text
    assert 'placeholder="Medium: our own regression results exist, the supplier' in text
    assert 'value="Credit-scoring model"' in text           # header 1 from the inventory
    assert 'value="deployer" selected' in text or 'value="deployer"' in text
    assert "Chapter 7" in text and "B.2" in text


def test_list_renders_empty_and_shows_sub_process_coverage(fixture_org):
    client = _client(fixture_org.path)
    empty = client.get("/usecases").text
    assert "No use cases yet" in empty
    client.post("/usecases", data=dict(COMPLETE, source="Third-party due diligence"))
    text = client.get("/usecases").text
    assert "UC-001" in text and "ORG-001" in text
    assert "Third-party due diligence" in text and "Human factors" in text
    assert "1 of 10" in text                                    # sub-processes that contributed


def test_unknown_system_or_use_case_is_404(fixture_org):
    client = _client(fixture_org.path)
    assert client.get("/usecases/new", params={"system": "SYS-404"}).status_code == 404
    assert client.post("/usecases", data=dict(COMPLETE, system_id="SYS-404")).status_code == 404
    assert client.get("/usecases/UC-404").status_code == 404
