"""Round 4 web shell and Inventory tests (PLAN.md section 4, round 4; SPEC.md 6.2, B.1).

The plan's checks: the list renders empty and with the fixture; the form
refuses a save without owner, role and Article 6 outcome and shows the reason;
a saved system appears in the list with its ID SYS-001. Also: the form is the
B.1 template, edits are field events in the audit trail, IDs are never
reused, the discovery ratio, the chapter header and "why" panel, escaping,
the loopback-only guards, the vendored static files and ``riskid serve``.
"""

import hashlib
import socket
import subprocess
import sys
import time

import httpx
import pytest
from fastapi.testclient import TestClient

from riskid.app import create_app
from riskid.cli import main
from riskid.store import Store, init

BASE = "http://127.0.0.1:8765"

# The vendored htmx.org 2.0.11 dist/htmx.min.js (docs/DECISIONS.md, round 4).
HTMX_SHA256 = "d6fdc75f204e6bdefa99b69bf1e6d4ac69b8a364f77929f45c13476b4000f717"

COMPLETE = {
    "name": "Fraud scoring",
    "function": "flag suspicious card transactions",
    "owner": "Head of Fraud",
    "role_under_act": "deployer",
    "article_6_outcome": "no further class",
    "lifecycle_stage": "operation and monitoring",
}

# The three return reasons of the Day-one journey (SPEC.md section 3).
NO_OWNER = "name the one person accountable for this system"
NO_ROLE = "choose provider, deployer or both"
NO_CLASS = "choose the Article 6 outcome"


@pytest.fixture
def empty_org(tmp_path):
    path = tmp_path / "empty.riskid"
    init(path).close()
    return path


def _client(path):
    return TestClient(create_app(path, actor="tester"), base_url=BASE)


def _system_events(path):
    with Store(path) as store:
        return store._conn.execute(
            "SELECT entity_id, field, old, new, actor, reason FROM events "
            "WHERE entity = 'system' ORDER BY seq").fetchall()


# --- the list -------------------------------------------------------------

def test_list_renders_empty(empty_org):
    resp = _client(empty_org).get("/inventory")
    assert resp.status_code == 200
    assert "No systems yet" in resp.text
    assert "SYS-" not in resp.text


def test_list_renders_the_fixture(fixture_org):
    resp = _client(fixture_org.path).get("/inventory")
    assert resp.status_code == 200
    for sys_id, name in (("SYS-001", "Credit-scoring model"),
                         ("SYS-002", "Customer-service chatbot"),
                         ("SYS-003", "CV-screening tool")):
        assert sys_id in resp.text and name in resp.text
    assert "No systems yet" not in resp.text
    # Only the CV-screening pilot is past its end date and before deployment.
    assert resp.text.count("Pilot overdue") == 1


def test_header_names_chapter_and_template_with_why_panel(empty_org):
    text = _client(empty_org).get("/inventory").text
    assert "Chapter 5" in text and "B.1" in text
    assert "You cannot identify the risks of a system you have not listed." in text
    assert 'src="/static/htmx.min.js"' in text


# --- the form -------------------------------------------------------------

def test_form_is_the_b1_template(empty_org):
    text = _client(empty_org).get("/inventory/new").text
    rows = ["System", "Vendor or built", "Model and version", "Purpose", "Users",
            "Persons affected", "Data", "Role under the Act", "Classification",
            "Owner", "Stage", "Jurisdictions", "Period and frequency of use",
            "Impact assessments", "Last risk assessment", "Discovery source",
            "Pilot end date", "Logs"]
    positions = [text.find(f"<h3>{n}. {row}</h3>") for n, row in enumerate(rows, 1)]
    assert -1 not in positions, list(zip(rows, positions))
    assert positions == sorted(positions)


def test_form_refuses_save_without_owner_role_and_classification(empty_org):
    client = _client(empty_org)
    resp = client.post("/inventory", data={"name": "Fraud scoring"})
    assert resp.status_code == 422
    for reason in (NO_OWNER, NO_ROLE, NO_CLASS):
        assert reason in resp.text
    assert 'value="Fraud scoring"' in resp.text      # what was typed is kept
    assert _system_events(empty_org) == []


@pytest.mark.parametrize("missing, reason", [
    ("owner", NO_OWNER), ("role_under_act", NO_ROLE), ("article_6_outcome", NO_CLASS)])
def test_each_required_field_is_refused_alone(empty_org, missing, reason):
    data = {k: v for k, v in COMPLETE.items() if k != missing}
    resp = _client(empty_org).post("/inventory", data=data)
    assert resp.status_code == 422
    assert reason in resp.text
    assert _system_events(empty_org) == []


def test_complete_form_has_no_return_reasons(empty_org):
    resp = _client(empty_org).post("/inventory", data=COMPLETE)
    assert resp.status_code == 200          # followed the redirect to the list
    for reason in (NO_OWNER, NO_ROLE, NO_CLASS):
        assert reason not in resp.text


def test_saved_system_appears_in_list_as_sys_001(empty_org):
    client = _client(empty_org)
    resp = client.post("/inventory", data=COMPLETE, follow_redirects=False)
    assert resp.status_code == 303
    listing = client.get("/inventory").text
    assert "SYS-001" in listing and "Fraud scoring" in listing
    (entity_id, field, _, new, actor, _), = _system_events(empty_org)
    assert (entity_id, field, actor) == ("SYS-001", None, "tester")
    assert '"owner":"Head of Fraud"' in new


def test_invalid_choice_and_date_are_refused(empty_org):
    data = dict(COMPLETE, role_under_act="vendor", pilot_end_date="30/06/2026")
    resp = _client(empty_org).post("/inventory", data=data)
    assert resp.status_code == 422
    assert NO_ROLE in resp.text
    assert "Pilot end date: use a date in the form YYYY-MM-DD" in resp.text


def test_structured_fields_are_parsed(empty_org):
    data = dict(COMPLETE, components="scoring model\nrules engine",
                users="fraud analyst, 12\nteam lead, 2",
                persons_affected="cardholders\nchildren with cards, vulnerable",
                jurisdictions="IE, UK", version_pinned="yes",
                **{"data.personal": "yes", "impact_assessments.DPIA.ref": "DPIA-7",
                   "impact_assessments.DPIA.date": "2026-03-01",
                   "last_risk_assessment.version": "4.2", "logs.retention": "6 months"})
    _client(empty_org).post("/inventory", data=data)
    with Store(empty_org) as store:
        system = store.systems()[0]
    assert system["components"] == ["scoring model", "rules engine"]
    assert system["users"] == [{"role": "fraud analyst", "number": 12},
                               {"role": "team lead", "number": 2}]
    assert system["persons_affected"] == [
        {"group": "cardholders", "vulnerable": False},
        {"group": "children with cards", "vulnerable": True}]
    assert system["jurisdictions"] == ["IE", "UK"]
    assert system["version_pinned"] is True and system["data"]["personal"] is True
    assert system["impact_assessments"]["DPIA"] == {"ref": "DPIA-7", "date": "2026-03-01"}
    assert system["last_risk_assessment"] == {"version": "4.2"}
    assert system["logs"] == {"retention": "6 months"}


def test_bad_user_count_is_refused(empty_org):
    resp = _client(empty_org).post("/inventory", data=dict(COMPLETE, users="analyst, many"))
    assert resp.status_code == 422
    assert "Users: give each line as role, number" in resp.text


# --- edits are field events; IDs are never reused ------------------------

def test_edit_records_a_field_event_with_reason(empty_org):
    client = _client(empty_org)
    client.post("/inventory", data=COMPLETE)
    form = client.get("/inventory/SYS-001").text
    assert 'value="Head of Fraud"' in form
    resp = client.post("/inventory/SYS-001", data=dict(
        COMPLETE, owner="Chief Risk Officer", change_reason="handover"),
        follow_redirects=False)
    assert resp.status_code == 303
    events = _system_events(empty_org)
    assert len(events) == 2
    entity_id, field, old, new, actor, reason = events[1]
    assert (entity_id, field, actor, reason) == ("SYS-001", "owner", "tester", "handover")
    assert (old, new) == ('"Head of Fraud"', '"Chief Risk Officer"')


def test_edit_without_change_records_nothing(empty_org):
    client = _client(empty_org)
    client.post("/inventory", data=COMPLETE)
    client.post("/inventory/SYS-001", data=COMPLETE)
    assert len(_system_events(empty_org)) == 1


def test_edit_refuses_clearing_the_owner(empty_org):
    client = _client(empty_org)
    client.post("/inventory", data=COMPLETE)
    resp = client.post("/inventory/SYS-001", data=dict(COMPLETE, owner=""))
    assert resp.status_code == 422 and NO_OWNER in resp.text
    with Store(empty_org) as store:
        assert store.systems()[0]["owner"] == "Head of Fraud"


def test_unknown_system_is_404(empty_org):
    client = _client(empty_org)
    assert client.get("/inventory/SYS-999").status_code == 404
    assert client.post("/inventory/SYS-999", data=COMPLETE).status_code == 404


def test_new_ids_continue_after_the_fixture(fixture_org):
    client = _client(fixture_org.path)
    client.post("/inventory", data=COMPLETE)
    assert "SYS-004" in client.get("/inventory").text


# --- the discovery ratio (SPEC.md 6.2) -------------------------------------

def test_discovery_ratio_is_recorded_per_quarter(empty_org):
    client = _client(empty_org)
    resp = client.post("/inventory/discovery", data={
        "quarter": "2026-Q4", "found": "40", "inventoried": "36",
        "method": "expenses and identity provider"}, follow_redirects=False)
    assert resp.status_code == 303
    text = client.get("/inventory").text
    assert "2026-Q4" in text and "1.11" in text
    with Store(empty_org) as store:
        assert store.state()["discovery"]["2026-Q4"]["found"] == 40


@pytest.mark.parametrize("bad", [
    {"quarter": "Q4", "found": "40", "inventoried": "36"},
    {"quarter": "2026-Q4", "found": "-1", "inventoried": "36"},
    {"quarter": "2026-Q4", "found": "40", "inventoried": "0"}])
def test_discovery_ratio_refuses_bad_input(empty_org, bad):
    resp = _client(empty_org).post("/inventory/discovery", data=bad)
    assert resp.status_code == 422
    with Store(empty_org) as store:
        assert "discovery" not in store.state()


# --- safety of the shell ---------------------------------------------------

def test_text_is_escaped(empty_org):
    client = _client(empty_org)
    client.post("/inventory", data=dict(COMPLETE, name="<script>alert(1)</script>"))
    text = client.get("/inventory").text
    assert "<script>alert(1)</script>" not in text
    assert "&lt;script&gt;" in text


def test_cross_origin_write_is_refused(empty_org):
    resp = _client(empty_org).post(
        "/inventory", data=COMPLETE, headers={"Origin": "http://evil.example"})
    assert resp.status_code == 403
    assert _system_events(empty_org) == []


def test_foreign_host_header_is_refused(empty_org):
    resp = _client(empty_org).get("/inventory", headers={"Host": "evil.example"})
    assert resp.status_code == 400


def test_static_files(empty_org):
    client = _client(empty_org)
    css = client.get("/static/style.css")
    assert css.status_code == 200 and "#1B2A4A" in css.text and "#C5A55A" in css.text
    js = client.get("/static/htmx.min.js")
    assert js.status_code == 200
    assert hashlib.sha256(js.content).hexdigest() == HTMX_SHA256


# --- riskid serve -----------------------------------------------------------

def test_serve_refuses_a_missing_file(tmp_path):
    assert main(["serve", str(tmp_path / "nope.riskid"), "--no-browser"]) == 1
    assert not (tmp_path / "nope.riskid").exists()


def test_serve_starts_and_serves_the_inventory(empty_org):
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    proc = subprocess.Popen(
        [sys.executable, "-m", "riskid", "serve", str(empty_org),
         "--port", str(port), "--no-browser"],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    try:
        deadline = time.time() + 20
        while True:
            try:
                resp = httpx.get(f"http://127.0.0.1:{port}/inventory", timeout=2)
                break
            except httpx.TransportError:
                assert time.time() < deadline, "server did not start"
                time.sleep(0.3)
        assert resp.status_code == 200 and "No systems yet" in resp.text
    finally:
        proc.terminate()
        proc.wait(timeout=10)


# --- fixes from the round 4 review ------------------------------------------

def test_non_ascii_digits_are_refused_not_a_crash(empty_org):
    client = _client(empty_org)
    resp = client.post("/inventory", data=dict(COMPLETE, users="analyst, ²"))
    assert resp.status_code == 422
    resp = client.post("/inventory/discovery",
                       data={"quarter": "2026-Q4", "found": "²", "inventoried": "3"})
    assert resp.status_code == 422
    resp = client.post("/inventory/discovery",
                       data={"quarter": "٢٠٢٦-Q4", "found": "4", "inventoried": "3"})
    assert resp.status_code == 422


def test_a_missing_file_is_not_recreated(tmp_path):
    path = tmp_path / "gone.riskid"
    init(path).close()
    client = _client(path)
    path.unlink()
    assert client.get("/inventory").status_code == 503
    assert client.post("/inventory", data=COMPLETE).status_code == 503
    assert not path.exists()


def test_actor_falls_back_when_the_account_has_no_name(monkeypatch):
    from riskid import config

    def no_name():
        raise OSError("no user name")

    monkeypatch.delenv("RISKID_ACTOR", raising=False)
    monkeypatch.setattr(config.getpass, "getuser", no_name)
    assert config.default_actor() == config.UNKNOWN_ACTOR
    monkeypatch.setenv("RISKID_ACTOR", "Ann Other")
    assert config.default_actor() == "Ann Other"


def test_every_interface_mode_never_allows_any_host():
    from riskid.cli import _allowed_hosts

    allowed = _allowed_hosts("0.0.0.0")
    assert "*" not in allowed
    assert "127.0.0.1" in allowed and "localhost" in allowed
    assert "evil.example" not in allowed
    assert _allowed_hosts("127.0.0.1") == ["127.0.0.1", "localhost"]
    assert _allowed_hosts("192.168.1.20") == ["127.0.0.1", "localhost", "192.168.1.20"]
