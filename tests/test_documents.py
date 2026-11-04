"""Round 12 Documents (PLAN.md round 12; SPEC.md section 7; chapter 12; B.7).

The plan's checks: XLSX columns equal the reference list in
tests/reference/columns.txt; the FRIA for the credit-scoring system contains
all six elements and names HUM-01's override rate under 27(1)(e); the SoA
lists exactly the Annex A references on live lines; every document records
the data-pack versions and the state hash. Also the CSV and PDF forms, the
board report's twelve items, the download routes and the Document record.
"""

import csv
import io
from pathlib import Path

import openpyxl
import pytest
from docx import Document as Docx
from fastapi.testclient import TestClient

from riskid.app import create_app
from riskid.documents.provenance import pack_versions, state_hash
from riskid.store import Store

BASE = "http://127.0.0.1:8765"
COLUMNS = (Path(__file__).parent / "reference" / "columns.txt").read_text(encoding="utf-8").splitlines()
FORM = {"harm_scored": "wrongful refusals", "unit_of_exposure": "applications a year",
        "impact_FIN": "2", "impact_REG": "3", "impact_REP": "2", "impact_IND": "4", "impact_OPS": "1",
        "likelihood": "4", "vulnerability": "3", "speed": "2", "data_quality": "Medium",
        "data_quality_basis": "partial tests on our own applications"}


@pytest.fixture
def org(fixture_org):
    client = TestClient(create_app(fixture_org.path, actor="tester"), base_url=BASE)
    for line in ("HUM-01", "FAI-04", "TRA-02", "MOD-05"):
        client.post("/library/adopt", data={"line_id": line, "system_id": "SYS-001"})
    client.post("/assess/HUM-01/controls", data={"name": "Override-rate monitoring", "type": "detective",
                                                 "annex_a_ref": "A.9.3"})
    client.post("/assess/HUM-01/controls/CT-001/test",
                data={"test_date": "2026-10-01", "outcome": "passed", "test_result": "override rate 4.1%"})
    client.post("/assess/HUM-01", data=dict(FORM, impact_IND="5"))      # material: impact 5
    client.post("/assess/FAI-04", data=dict(FORM, likelihood="3"))   # 12: not material
    return client, fixture_org.path


def _provenance(path):
    with Store(path) as store:
        state = store.state()
    return state_hash(state), pack_versions(state)


def test_xlsx_columns_equal_the_reference_list(org):
    client, _ = org
    resp = client.get("/documents/register.xlsx")
    assert resp.status_code == 200
    book = openpyxl.load_workbook(io.BytesIO(resp.content))
    sheet = book["Register"]
    assert [c.value for c in sheet[1]] == COLUMNS
    ids = [row[0].value for row in sheet.iter_rows(min_row=2)]
    assert ids == ["FAI-04", "HUM-01", "MOD-05", "TRA-02"]
    hum01 = next(row for row in sheet.iter_rows(min_row=2) if row[0].value == "HUM-01")
    values = dict(zip(COLUMNS, (c.value for c in hum01)))
    assert (values["Likelihood"], values["Impact"], values["Inherent score"], values["Material"]) == (4, 5, 20, "Yes")


def test_the_fria_has_six_elements_and_hum01s_override_rate_under_27_1_e(org):
    client, _ = org
    resp = client.get("/documents/fria/SYS-001.docx")
    assert resp.status_code == 200
    text = "\n".join(p.text for p in Docx(io.BytesIO(resp.content)).paragraphs)
    headings = ["27(1)(a)", "27(1)(b)", "27(1)(c)", "27(1)(d)", "27(1)(e)", "27(1)(f)"]
    positions = [text.find(h) for h in headings]
    assert -1 not in positions and positions == sorted(positions)
    oversight = text[positions[4]:positions[5]]
    assert "HUM-01" in oversight and "override rate 4.1%" in oversight
    html = client.get("/documents/fria/SYS-001.html").text
    assert "Source:" in html and "inventory field 6" in html             # each element cites its fields
    pdf = client.get("/documents/fria/SYS-001.pdf")
    assert pdf.status_code == 200 and pdf.content[:5] == b"%PDF-"
    assert client.get("/documents/fria/SYS-404.docx").status_code == 404


def test_the_soa_lists_exactly_the_annex_a_references_on_live_lines(org):
    client, path = org
    client.post("/library/adopt", data={"line_id": "MOD-13", "system_id": "SYS-001"})
    client.post("/register/MOD-13/retire", data={"reason": "we do not build systems"})
    with Store(path) as store:
        state = store.state()
    live = {i for i, line in state["register"].items() if line["status"] != "retired"}
    expected = {ref for i in live for ref in state["register"][i]["annex_a_controls"]}
    expected |= {c["annex_a_ref"] for c in state["control"].values() if c["line_id"] in live and c.get("annex_a_ref")}
    sheet = openpyxl.load_workbook(io.BytesIO(client.get("/documents/soa.xlsx").content))["Statement of Applicability"]
    listed = {row[0].value for row in sheet.iter_rows(min_row=2)}
    assert listed == expected
    a93 = next(row for row in sheet.iter_rows(min_row=2) if row[0].value == "A.9.3")
    assert "HUM-01" in a93[1].value and a93[2].value == "included: cited by a material line"
    retired_only = set(state["register"]["MOD-13"]["annex_a_controls"]) - expected
    assert not (retired_only & listed)


def test_every_document_records_the_pack_versions_and_the_state_hash(org):
    client, path = org
    digest, versions = _provenance(path)
    assert versions == "library 1.0, scales 1.0, indicators 1.0"
    about = openpyxl.load_workbook(io.BytesIO(client.get("/documents/register.xlsx").content))["About"]
    about_text = " ".join(str(c.value) for row in about.iter_rows() for c in row if c.value)
    assert digest in about_text and versions in about_text
    first = client.get("/documents/register.csv").text.splitlines()[0]
    assert first.startswith("#") and digest in first and versions in first
    fria = "\n".join(p.text for p in Docx(io.BytesIO(client.get("/documents/fria/SYS-001.docx").content)).paragraphs)
    assert digest in fria and versions in fria
    soa_about = openpyxl.load_workbook(io.BytesIO(client.get("/documents/soa.xlsx").content))["About"]
    assert digest in " ".join(str(c.value) for row in soa_about.iter_rows() for c in row if c.value)
    for page in ("/documents/register.html", "/documents/soa.html", "/documents/report.html",
                 "/documents/fria/SYS-001.html"):
        text = client.get(page).text
        assert digest in text and versions in text, page


def test_the_csv_has_the_same_columns(org):
    client, _ = org
    rows = list(csv.reader(io.StringIO("\n".join(client.get("/documents/register.csv").text.splitlines()[1:]))))
    assert rows[0] == COLUMNS and len(rows) == 5


def test_pdfs_render(org):
    client, _ = org
    for url in ("/documents/register.pdf", "/documents/soa.pdf", "/documents/report.pdf"):
        resp = client.get(url)
        assert resp.status_code == 200 and resp.content[:5] == b"%PDF-", url
        assert resp.headers["content-type"] == "application/pdf"


def test_the_board_report_has_the_twelve_items(org):
    client, _ = org
    text = client.get("/documents/report.html").text
    for n, item in enumerate(("Scope", "Material risks", "Persons affected", "Acceptance",
                              "Incidents and monitoring", "Concentration", "Change", "Evidence quality",
                              "Calendar", "Movement", "Process", "Decisions"), start=1):
        assert f"{n}. {item}" in text, item
    material = text.split("2. Material risks")[1].split("3. Persons affected")[0]
    assert "HUM-01" in material and "FAI-04" not in material   # FAI-04 is not material


def test_the_state_hash_ignores_document_records_and_follows_the_register(org):
    client, path = org
    before, _ = _provenance(path)
    client.get("/documents/register.xlsx")
    assert _provenance(path)[0] == before          # generating a document does not change the register
    client.post("/register/HUM-01", data={"owner": "Aoife Byrne", "change_reason": "named"})
    assert _provenance(path)[0] != before


def test_each_download_is_recorded(org):
    client, path = org
    client.get("/documents/register.xlsx")
    client.get("/documents/fria/SYS-001.docx")
    with Store(path) as store:
        docs = sorted(store.state()["document"].items())
    assert [d["kind"] for _, d in docs] == ["register", "FRIA"]
    assert all(d["inputs_hash"] and d["file_path"] and d["generated_at"] for _, d in docs)
    assert "DOC-001" in client.get("/documents").text


def test_documents_page_renders_for_an_empty_organisation(tmp_path):
    from riskid.store import init
    init(tmp_path / "e.riskid").close()
    client = TestClient(create_app(tmp_path / "e.riskid", actor="t"), base_url=BASE)
    assert client.get("/documents").status_code == 200
    assert client.get("/documents/register.xlsx").status_code == 200
    assert client.get("/documents/report.pdf").status_code == 200
