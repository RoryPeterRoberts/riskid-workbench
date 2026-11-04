"""SPEC.md section 11, acceptance for version 1 (PLAN.md round 14).

"A practitioner following chapter 5 to chapter 13 with the fixture
organisation (three systems) reaches a signed quarterly pack without leaving
the tool, and the pack opens in Excel, a PDF reader and a browser." Every step
goes through the screens' routes, as the practitioner's browser would, and
every change must be accepted (303), not returned.
"""

import io
import zipfile
from html.parser import HTMLParser

import openpyxl
from fastapi.testclient import TestClient

from riskid.app import create_app
from riskid.store import Store

BASE = "http://127.0.0.1:8765"
ASSESSMENT = {"harm_scored": "wrongful refusals", "unit_of_exposure": "applications a year",
              "impact_FIN": "2", "impact_REG": "3", "impact_REP": "2", "impact_IND": "5", "impact_OPS": "1",
              "likelihood": "4", "vulnerability": "3", "speed": "2", "data_quality": "Medium",
              "data_quality_basis": "override log for 2026-Q3"}


class _Cells(HTMLParser):
    """Counts the table rows of a page, which a browser would lay out."""

    def __init__(self):
        super().__init__()
        self.rows = 0

    def handle_starttag(self, tag, attrs):
        self.rows += tag == "tr"


def _done(resp):
    assert resp.status_code == 303, (resp.status_code, resp.text[:600])
    return resp


def test_chapter_5_to_13_reaches_a_signed_quarterly_pack_that_opens(fixture_org):
    client = TestClient(create_app(fixture_org.path, actor="Ola Byrne"), base_url=BASE)
    before = max(e["seq"] for e in fixture_org.events())
    post = lambda url, **data: _done(client.post(url, data=data, follow_redirects=False))  # noqa: E731

    # Chapter 5, the context: three systems in the inventory, and the discovery ratio.
    assert client.get("/inventory").text.count("SYS-00") >= 3
    post("/inventory/discovery", quarter="2026-Q4", found="5", inventoried="3", method="expenses")
    # Chapters 4 and 5, the starting universe: library lines adopted per system.
    for line, system in (("HUM-01", "SYS-001"), ("FAI-04", "SYS-001"), ("MOD-05", "SYS-002"),
                         ("LEG-09", "SYS-002"), ("FAI-01", "SYS-003")):
        post("/library/adopt", line_id=line, system_id=system)

    # Chapter 6, top-down: a SWIFT workshop on the credit model, voted and closed.
    post("/workshops", system_ids="SYS-001", date="2026-11-20", facilitator="Fiona Hayes", vote_allowance="5",
         seat_1="Ann Owner", seat_5="Ola Overseer", seat_6="Sid Sceptic")
    post("/workshops/WS-001/participant", participant="Ann Owner", pre_list="MOD-06")
    for _ in range(2):
        post("/workshops/WS-001/advance")
    post("/workshops/WS-001/swift/6", status="not known")
    post("/workshops/WS-001/advance")
    post("/workshops/WS-001/advance")
    post("/workshops/WS-001/participant", participant="Ann Owner", **{"vote_MOD-06": "2", "vote_HUM-01": "1"})
    post("/workshops/WS-001/advance")
    post("/workshops/WS-001/gap", gap_review="No emerging risk without a node.")
    post("/workshops/WS-001/close")

    # Chapter 7, bottom-up: a use case on the chatbot, accepted as a candidate line.
    post("/usecases", system_id="SYS-002", taxonomy="2.1", owner="Head of Customer Service",
         definition="Customers act on a wrong answer from the chatbot about their account",
         drivers_direct="Answers are generated without a check against the account record",
         data_quality="Low")

    # Chapter 8, reconciliation: a disagreement logged and settled, and the record signed.
    post("/reconcile/disagreements", line_id="HUM-01", holder="Ola", minority_score="5", dimension="IND",
         evidence="override log")
    post("/reconcile/resolve", subject="DL-001", disposition="local", reason="settled on the override log")
    post("/reconcile/record", present="Ann, Ola", signed_by="Chief Financial Officer")

    # Chapter 9, assessment: a control tested, then the line scored with its residual lowered.
    post("/assess/HUM-01/controls", name="Override-rate monitoring", type="detective", annex_a_ref="A.9.3")
    post("/assess/HUM-01/controls/CT-001/test", test_date="2026-10-01", outcome="passed",
         test_result="override rate 4.1%")
    post("/assess/HUM-01", **dict(ASSESSMENT, residual_L="2",
                                  data_quality_basis="CT-001 tested 2026-10-01: override rate 4.1%"))
    post("/assess/FAI-04", **dict(ASSESSMENT, likelihood="3", impact_IND="4"))

    # Chapter 10, interaction: a link and a bow-tie on the material line.
    post("/interact/links", from_line="MOD-05", to_line="HUM-01", kind="triggers",
         mechanism="degraded output reaches reviewers who stopped checking")
    post("/interact/bowties", line_id="HUM-01", owner="Head of Lending Operations",
         event="Wrong decisions issued at volume", cause_1="The vendor replaces the model (MOD-05)",
         preventive_1="Contractual notice; version pinning", consequence_1="Wrong decisions about individuals",
         recovery_1="Suspend the automated route")

    # Chapter 11, the register: the owner named.
    post("/register/HUM-01", owner="Aoife Byrne, Head of Lending", coso_category="operations",
         change_reason="owner named at reconciliation")

    # Chapter 12, integration: the documents and the contract checklist.
    for url in ("/documents/register.xlsx", "/documents/fria/SYS-001.docx", "/documents/soa.xlsx",
                "/documents/report.pdf"):
        assert client.get(url).status_code == 200, url
    post("/contracts/SYS-002", reference="Helix MSA", **{f"clause_{n}": "present" for n in range(1, 18)})

    # Chapter 13, the cycle: an indicator read, a trigger decided, and the quarterly run signed.
    post("/cycle/indicators", line_id="HUM-01", name="Override rate", unit="%", amber="5", red="10",
         direction="higher is worse", read_by="Business owner")
    post("/cycle/indicators/KRI-001/value", value="4.1", date="2026-12-01")
    post("/cycle/triggers", date="2026-11-20", source="Helix Conversations",
         text="The model behind the chatbot API changes version on 1 December.")
    post("/cycle/triggers/TR-001/decision", significance="significant", decision="regression run first")
    post("/cycle/runs", kind="quarterly", date="2026-12-15")
    for n in range(1, 19):
        post(f"/cycle/runs/CR-001/steps/{n}", evidence=f"evidence for step {n}", done="on")
    post("/cycle/runs/CR-001/sign", signed_by="Chief Financial Officer", next_due="2027-03-15")

    resp = client.get("/cycle/runs/CR-001/pack.zip")
    assert resp.status_code == 200
    pack = zipfile.ZipFile(io.BytesIO(resp.content))
    # Excel: the register opens, with its lines.
    sheet = openpyxl.load_workbook(io.BytesIO(pack.read("register.xlsx"))).active
    ids = [row[0] for row in sheet.iter_rows(min_row=2, values_only=True)]
    assert {"HUM-01", "MOD-05", "MOD-06", "ORG-001"} <= set(ids)
    # A PDF reader: the signed checklist is a whole PDF.
    pdf = pack.read("checklist.pdf")
    assert pdf.startswith(b"%PDF-") and pdf.rstrip().endswith(b"%%EOF")
    # A browser: the checklist page parses, with the 18 steps and the signature.
    page = pack.read("checklist.html").decode()
    cells = _Cells()
    cells.feed(page)
    assert cells.rows == 19 and "Signed by Chief Financial Officer" in page
    assert "HUM-01" in pack.read("change_list.csv").decode() and "DL-001" in pack.read("disagreement_log.csv").decode()
    with Store(fixture_org.path) as store:                      # every change in the practitioner's name
        assert {e["actor"] for e in store.events() if e["seq"] > before} == {"Ola Byrne"}
        state = store.state()
    assert state["workshop"]["WS-001"]["status"] == "closed" and state["register"]["MOD-06"]["source"] == "top-down"
    assert state["usecase"]["UC-001"]["line_id"] == "ORG-001" and state["reconciliation"]["RC-001"]["signed_by"]
    hum = max((a for a in state["assessment"].values() if a["line_id"] == "HUM-01"), key=lambda a: a["date"])
    assert hum["material"] and hum["residual"] < hum["inherent"]          # lowered on the passed test
    assert state["register"]["HUM-01"]["owner"].startswith("Aoife Byrne")
    assert state["register"]["HUM-01"]["next_review"] == "2027-03-15"     # dated by the sign-off
