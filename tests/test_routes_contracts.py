"""Round 14 Contracts (PLAN.md round 14; SPEC.md 6.12; B.9; chapter 12).

The plan's check: the contract checklist shows gaps against lines. Also the
clauses against the book table, the "Any line" clause, the share of contracts
that meet the clause standard, and the refusals.
"""

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from riskid import importers
from riskid.app import create_app
from riskid.store import Store

BASE = "http://127.0.0.1:8765"
TABLES = (Path(__file__).parent.parent / "docs" / "BOOK_TABLES.md").read_text(encoding="utf-8")


@pytest.fixture
def org(fixture_org):
    client = TestClient(create_app(fixture_org.path, actor="tester"), base_url=BASE)
    for line, system in (("MOD-05", "SYS-002"), ("OPS-05", "SYS-002"), ("TRA-04", "SYS-002"),
                         ("HUM-01", "SYS-001")):
        client.post("/library/adopt", data={"line_id": line, "system_id": system})
    return client, fixture_org.path


def _state(path):
    with Store(path) as store:
        return store.state()


def _gaps(client, system):
    return client.get(f"/contracts/{system}").text.split('id="gaps"')[1].split("</section>")[0]


def test_the_clauses_are_the_book_table():
    clauses = importers.load_contract_clauses()
    rows = re.findall(r"^\| (\d+) \| (.+?) \| (.+?) \| (.+?) \| (.+?) \|$",
                      TABLES[TABLES.index("## B.9"):TABLES.index("## Chapter 15")], re.M)
    assert [(c["n"], c["clause"], c["covers"]) for c in clauses] == [(int(n), c, w) for n, c, w, _, _ in rows]
    assert clauses[0]["lines"] == ["MOD-05", "OPS-05"] and clauses[4]["any_line"] and not clauses[4]["lines"]


def test_the_checklist_shows_gaps_against_lines(org):
    client, path = org
    gaps = _gaps(client, "SYS-002")
    # Nothing reviewed yet: each clause whose lines are live on the system is a gap.
    assert "1. Notice of changes" in gaps and "MOD-05" in gaps and "OPS-05" in gaps
    assert "5. Incident notification" in gaps                  # "Any line", and SYS-002 has live lines
    assert "15. Fairness evidence" not in gaps                 # FAI-04 is not live on SYS-002
    statuses = {f"clause_{n}": "present" for n in range(1, 18)}
    statuses.update({"clause_1": "partial", "clause_4": "absent"})
    resp = client.post("/contracts/SYS-002", data={**statuses, "reference": "Helix MSA 2025-03",
                                                   "gap_note": "renewal in 2027"}, follow_redirects=False)
    assert resp.status_code == 303
    gaps = _gaps(client, "SYS-002")
    assert "1. Notice of changes" in gaps and "partial" in gaps
    assert "4. Audit and testing" in gaps and "absent" in gaps and "TRA-04" in gaps
    assert "2. Documentation" not in gaps and "5. Incident notification" not in gaps
    contract = _state(path)["contract"]["SYS-002"]
    assert contract["clauses"]["1"] == "partial" and contract["reference"] == "Helix MSA 2025-03"


def test_a_clause_with_no_live_line_on_the_system_is_not_a_gap(org):
    client, _ = org
    assert "No gap" in _gaps(client, "SYS-003")                # no live lines on SYS-003


def test_the_list_shows_the_share_that_meets_the_clause_standard(org):
    client, _ = org
    client.post("/contracts/SYS-002", data={f"clause_{n}": "present" for n in range(1, 18)})
    # SYS-003 has no live line, so a contract with every clause absent has nothing to be judged by.
    client.post("/contracts/SYS-003", data={f"clause_{n}": "absent" for n in range(1, 18)})
    listing = client.get("/contracts").text
    assert "1 of 3" in listing                                  # three bought systems, one meets it
    assert "no live lines yet" in listing


def test_refusals(org):
    client, path = org
    assert client.post("/contracts/SYS-002", data={"clause_1": "maybe"}).status_code == 422
    assert "contract" not in _state(path)
    assert client.get("/contracts/SYS-404").status_code == 404


def test_contracts_render_for_an_empty_organisation(tmp_path):
    from riskid.store import init
    init(tmp_path / "e.riskid").close()
    client = TestClient(create_app(tmp_path / "e.riskid", actor="t"), base_url=BASE)
    assert client.get("/contracts").status_code == 200
