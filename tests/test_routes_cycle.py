"""Round 13 Cycle (PLAN.md round 13; SPEC.md 6.11; chapter 13; B.8).

The plan's checks: an indicator above its red threshold shows red; a trigger
lists the lines whose hooks or indicators it touches and opens an event
update; step 4 flags a version mismatch in the fixture; sign-off refuses while
a step lacks evidence; the quarterly pack ZIP contains the register, the
change list and the disagreement log. Also the data files against the book
tables, the significance decision, the calendar and the evidence pack.
"""

import io
import re
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from riskid import importers
from riskid.app import create_app
from riskid.store import Store

BASE = "http://127.0.0.1:8765"
TABLES = (Path(__file__).parent.parent / "docs" / "BOOK_TABLES.md").read_text(encoding="utf-8")
NOTICE = ("Supplier change notice: the model behind the chatbot API changes version on 1 December; "
          "the Article 50 notice wording is unaffected.")


@pytest.fixture
def org(fixture_org):
    client = TestClient(create_app(fixture_org.path, actor="tester"), base_url=BASE)
    for line, system in (("HUM-01", "SYS-001"), ("MOD-05", "SYS-002"), ("OPS-05", "SYS-002"),
                         ("LEG-09", "SYS-002"), ("FAI-04", "SYS-001")):
        client.post("/library/adopt", data={"line_id": line, "system_id": system})
    return client, fixture_org.path


def _state(path):
    with Store(path) as store:
        return store.state()


def test_the_checklist_and_calendar_are_the_book_tables():
    steps = importers.load_checklist()
    rows = re.findall(r"^\| (\d+) \| (.+?) \| (.+?) \| (.+?) \| (.+?) \|$",
                      TABLES[TABLES.index("## B.8"):TABLES.index("## B.9")], re.M)
    assert [(s["n"], s["step"], s["owner"]) for s in steps] == [(int(n), st, o) for n, _, st, _, o in rows]
    calendar = importers.load_calendar()
    assert len(calendar) == 7
    assert calendar[2]["applies_from"] == "2026-08-02" and calendar[2]["articles"] == "50"
    assert calendar[-1]["applies_from"] is None


def test_an_indicator_above_its_red_threshold_shows_red(org):
    client, _ = org
    client.post("/cycle/indicators", data={"line_id": "HUM-01", "name": "Override rate", "unit": "%",
                                           "amber": "5", "red": "10", "direction": "higher is worse",
                                           "read_by": "Business owner"})
    for value, colour in (("12", "red"), ("7", "amber"), ("3", "green")):
        client.post("/cycle/indicators/KRI-001/value", data={"value": value, "date": "2026-11-01"})
        sheet = client.get("/cycle").text.split('id="indicators"')[1].split("</section>")[0]
        row = next(r for r in sheet.split("<tr>") if "KRI-001" in r)
        assert f'class="rag {colour}"' in row, (value, colour)
    client.post("/cycle/indicators", data={"line_id": "HUM-01", "name": "Agreement on a blind sample",
                                           "unit": "%", "amber": "90", "red": "80", "direction": "lower is worse",
                                           "read_by": "Business owner"})
    client.post("/cycle/indicators/KRI-002/value", data={"value": "75", "date": "2026-11-01"})
    row = next(r for r in client.get("/cycle").text.split("<tr>") if "KRI-002" in r)
    assert 'class="rag red"' in row
    inconsistent = {"line_id": "HUM-01", "name": "x", "amber": "10", "red": "5", "direction": "higher is worse",
                    "read_by": "Business owner"}
    assert client.post("/cycle/indicators", data=inconsistent).status_code == 422
    unread = dict(inconsistent, amber="5", red="10", read_by="")
    assert client.post("/cycle/indicators", data=unread).status_code == 422      # no owner: decoration
    overflow = {"value": "9" * 400, "date": "2026-11-01"}       # float() would make it infinity
    assert client.post("/cycle/indicators/KRI-001/value", data=overflow).status_code == 422


def test_a_reading_that_turns_red_logs_one_trigger_on_its_line(org):
    client, path = org
    client.post("/cycle/indicators", data={"line_id": "HUM-01", "name": "Override rate", "unit": "%",
                                           "amber": "5", "red": "10", "direction": "higher is worse",
                                           "read_by": "Business owner"})
    for value, when in (("4", "2026-09-01"), ("12", "2026-10-01"), ("14", "2026-11-01")):
        client.post("/cycle/indicators/KRI-001/value", data={"value": value, "date": when})
    triggers = _state(path)["trigger"]
    assert list(triggers) == ["TR-001"]                       # turning red logs it; staying red does not
    assert triggers["TR-001"]["date"] == "2026-10-01" and triggers["TR-001"]["source"] == "indicator KRI-001"
    assert "HUM-01" in [t["line_id"] for t in triggers["TR-001"]["lines_touched"]]
    client.post("/cycle/indicators/KRI-001/value", data={"value": "3", "date": "2026-08-01"})
    kri = _state(path)["indicator"]["KRI-001"]
    assert kri["current_value"] == 14 and len(kri["history"]) == 4     # a late reading does not replace it


def test_a_trigger_lists_the_lines_it_touches_and_opens_an_event_update(org):
    client, path = org
    resp = client.post("/cycle/triggers", data={"date": "2026-11-20", "source": "Helix Conversations",
                                                "text": NOTICE}, follow_redirects=False)
    assert resp.status_code == 303
    trigger = _state(path)["trigger"]["TR-001"]
    touched = dict((t["line_id"], t["why"]) for t in trigger["lines_touched"])
    assert {"MOD-05", "OPS-05", "LEG-09"} <= set(touched)
    assert "AI Act Art 50" in touched["LEG-09"] and "indicator" in touched["MOD-05"]
    assert "HUM-01" not in touched and "FAI-04" not in touched
    register = _state(path)["register"]
    assert all(register[i]["next_review"] == "2026-11-20" for i in ("MOD-05", "OPS-05", "LEG-09"))
    with Store(path) as store:
        reasons = [e["reason"] for e in store.events() if e["entity"] == "register" and e["field"] == "next_review"]
    assert reasons.count("event-driven update opened by TR-001") == len(touched)
    log = client.get("/cycle").text.split('id="triggers"')[1].split("</section>")[0]
    assert "TR-001" in log and "MOD-05" in log


def test_the_significance_decision_is_recorded(org):
    client, path = org
    client.post("/cycle/triggers", data={"date": "2026-11-20", "source": "Helix", "text": NOTICE})
    assert client.post("/cycle/triggers/TR-001/decision", data={"significance": "maybe"}).status_code == 422
    client.post("/cycle/triggers/TR-001/decision", data={
        "significance": "significant", "decision": "re-assess MOD-05 on the new version before 1 December"})
    trigger = _state(path)["trigger"]["TR-001"]
    assert (trigger["significance"], trigger["decided_by"]) == ("significant", "tester")


def test_step_4_flags_a_version_mismatch_in_the_fixture(org):
    client, _ = org
    client.post("/cycle/runs", data={"kind": "quarterly", "date": "2026-12-15"})
    run = client.get("/cycle/runs/CR-001").text
    step4 = run.split('id="step-4"')[1].split('id="step-5"')[0]
    assert "SYS-002" in step4 and "2026-09" in step4 and "2026-05" in step4
    step2 = run.split('id="step-2"')[1].split('id="step-3"')[0]
    assert "SYS-003" in step2                     # the CV-screening pilot past its end date


def test_sign_off_refuses_while_a_step_lacks_evidence(org):
    client, path = org
    client.post("/cycle/runs", data={"kind": "quarterly", "date": "2026-12-15"})
    for n in range(1, 18):
        client.post(f"/cycle/runs/CR-001/steps/{n}", data={"evidence": f"evidence for step {n}",
                                                            "owner": "AI officer", "done": "on"})
    refused = client.post("/cycle/runs/CR-001/sign", data={"signed_by": "Chief Financial Officer",
                                                            "next_due": "2027-03-15"})
    assert refused.status_code == 422
    assert "18" in refused.text.split('class="reasons"')[1].split("</ul>")[0]
    client.post("/cycle/runs/CR-001/steps/18", data={"evidence": "signed record", "owner": "CFO"})
    not_done = client.post("/cycle/runs/CR-001/sign", data={"signed_by": "Chief Financial Officer",
                                                             "next_due": "2027-03-15"})
    assert not_done.status_code == 422 and "mark step 18 done" in not_done.text
    client.post("/cycle/runs/CR-001/steps/18", data={"evidence": "signed record", "owner": "CFO", "done": "on"})
    assert client.post("/cycle/runs/CR-001/sign", data={"signed_by": "Chief Financial Officer",
                                                        "next_due": "2026-12-01"}).status_code == 422
    assert client.post("/cycle/runs/CR-001/sign", data={"signed_by": "", "next_due": "2027-03-15"}).status_code == 422
    ok = client.post("/cycle/runs/CR-001/sign", data={"signed_by": "Chief Financial Officer",
                                                       "next_due": "2027-03-15"}, follow_redirects=False)
    assert ok.status_code == 303
    run = _state(path)["cycle"]["CR-001"]
    assert (run["signed_by"], run["next_due"]) == ("Chief Financial Officer", "2027-03-15") and run["signed_date"]
    assert _state(path)["register"]["HUM-01"]["next_review"] == "2027-03-15"
    assert client.post("/cycle/runs/CR-001/steps/1", data={"evidence": "late"}).status_code == 409


def test_the_quarterly_pack_has_the_register_the_change_list_and_the_disagreement_log(org):
    client, _ = org
    client.post("/reconcile/disagreements", data={"line_id": "HUM-01", "holder": "Ola", "minority_score": "4",
                                                  "dimension": "IND", "evidence": "override log"})
    client.post("/cycle/runs", data={"kind": "quarterly", "date": "2026-12-15"})
    resp = client.get("/cycle/runs/CR-001/pack.zip")
    assert resp.status_code == 200 and resp.headers["content-type"] == "application/zip"
    names = set(zipfile.ZipFile(io.BytesIO(resp.content)).namelist())
    assert {"register.xlsx", "register.csv", "change_list.csv", "disagreement_log.csv", "checklist.html"} <= names
    pack = zipfile.ZipFile(io.BytesIO(resp.content))
    assert "DL-001" in pack.read("disagreement_log.csv").decode()
    assert "HUM-01" in pack.read("change_list.csv").decode()


def _sign(client, run="CR-001", next_due="2027-03-15"):
    for n in range(1, 19):
        client.post(f"/cycle/runs/{run}/steps/{n}", data={"evidence": f"evidence {n}", "done": "on"})
    return client.post(f"/cycle/runs/{run}/sign", data={"signed_by": "CFO", "next_due": next_due},
                       follow_redirects=False)


def test_a_signed_runs_pack_holds_the_register_as_signed(org):
    client, _ = org
    client.post("/cycle/runs", data={"kind": "quarterly", "date": "2026-12-15"})
    assert _sign(client).status_code == 303
    client.post("/library/adopt", data={"line_id": "OPS-01", "system_id": "SYS-001"})     # after the signing
    pack = zipfile.ZipFile(io.BytesIO(client.get("/cycle/runs/CR-001/pack.zip").content))
    assert "HUM-01" in pack.read("register.csv").decode() and "OPS-01" not in pack.read("register.csv").decode()
    assert "OPS-01" not in pack.read("change_list.csv").decode()
    client.post("/cycle/runs", data={"kind": "quarterly", "date": "2027-03-15"})
    pack = zipfile.ZipFile(io.BytesIO(client.get("/cycle/runs/CR-002/pack.zip").content))
    changes = pack.read("change_list.csv").decode()
    assert "OPS-01" in changes and "HUM-01" not in changes      # only what changed since CR-001 was signed


def test_a_trigger_awaiting_its_decision_keeps_its_date_through_the_sign_off(org):
    client, path = org
    client.post("/cycle/triggers", data={"date": "2026-11-20", "source": "Helix", "text": NOTICE})
    client.post("/cycle/runs", data={"kind": "quarterly", "date": "2026-12-15"})
    _sign(client)
    register = _state(path)["register"]
    assert register["MOD-05"]["next_review"] == "2026-11-20" and register["HUM-01"]["next_review"] == "2027-03-15"
    client.post("/cycle/triggers/TR-001/decision", data={"significance": "not", "decision": "no change in use"})
    client.post("/cycle/runs", data={"kind": "quarterly", "date": "2027-03-15"})
    _sign(client, "CR-002", "2027-06-15")
    assert _state(path)["register"]["MOD-05"]["next_review"] == "2027-06-15"


def test_the_evidence_pack_adds_the_audit_trail(org):
    client, _ = org
    resp = client.get("/cycle/evidence-pack.zip")
    names = set(zipfile.ZipFile(io.BytesIO(resp.content)).namelist())
    assert {"register.xlsx", "audit_trail.csv", "soa.xlsx", "disagreement_log.csv", "board_report.pdf"} <= names
    assert {"fria_SYS-001.docx", "fria_SYS-003.docx"} <= names and "fria_SYS-002.docx" not in names


def test_the_board_report_reads_the_cycle(org):
    client, _ = org
    client.post("/cycle/indicators", data={"line_id": "HUM-01", "name": "Override rate", "unit": "%", "amber": "5",
                                           "red": "10", "direction": "higher is worse", "read_by": "Business owner"})
    client.post("/cycle/indicators/KRI-001/value", data={"value": "12", "date": "2026-10-01"})
    client.post("/cycle/runs", data={"kind": "quarterly", "date": "2026-12-15"})
    _sign(client)
    text = client.get("/documents/report.html").text
    item5 = text.split("5. Incidents and monitoring")[1].split("6. Concentration")[0]
    assert "KRI-001 Override rate on HUM-01: 12% (red)" in item5 and "1 trigger since the last report" in item5
    assert "No indicator is set on OPS-05" in text.split("7. Change")[1].split("8. Evidence quality")[0]
    assert "CR-001 (quarterly) signed by CFO" in text.split("11. Process")[1].split("12. Decisions")[0]
    assert "come with the Cycle" not in text and "recorded with the Cycle" not in text


def test_the_calendar_is_shown(org):
    calendar = org[0].get("/cycle").text.split('id="calendar"')[1].split("</section>")[0]
    assert "2 December 2027" in calendar and "Deployers of those systems" in calendar


def test_cycle_renders_for_an_empty_organisation(tmp_path):
    from riskid.store import init
    init(tmp_path / "e.riskid").close()
    client = TestClient(create_app(tmp_path / "e.riskid", actor="t"), base_url=BASE)
    assert client.get("/cycle").status_code == 200
    client.post("/cycle/runs", data={"kind": "quarterly", "date": "2026-12-15"})
    assert client.get("/cycle/runs/CR-001").status_code == 200
