"""Round 5 Library screens (PLAN.md round 5; SPEC.md 6.3).

The plan's checks: adopting a line creates a RegisterLine with the same ID and
source=library; adopting twice is refused. Also: the library and taxonomy
render for an empty and for the fixture organisation, search and the L1
filter, a line's page, the proposal page with its reasons and the removed
lines, and the error cases.
"""

import pytest
from fastapi.testclient import TestClient

from riskid.app import create_app
from riskid.store import Store, init

BASE = "http://127.0.0.1:8765"


@pytest.fixture
def empty_org(tmp_path):
    path = tmp_path / "empty.riskid"
    init(path).close()
    return path


def _client(path):
    return TestClient(create_app(path, actor="tester"), base_url=BASE)


def _register_events(path):
    with Store(path) as store:
        return store._conn.execute(
            "SELECT entity_id, field, new, actor, reason FROM events "
            "WHERE entity = 'register' ORDER BY seq").fetchall()


def test_library_lists_91_lines_and_42_taxonomy_lines(empty_org):
    resp = _client(empty_org).get("/library")
    assert resp.status_code == 200
    assert resp.text.count('class="line-id"') == 91
    assert resp.text.count('class="tax-code"') == 42
    assert "Chapter 4" in resp.text and "Appendix A" in resp.text


def test_library_renders_for_the_fixture(fixture_org):
    resp = _client(fixture_org.path).get("/library")
    assert resp.status_code == 200
    assert "SYS-001" in resp.text                   # offered in the propose picker


def test_search_and_l1_filter(empty_org):
    client = _client(empty_org)
    found = client.get("/library", params={"q": "prompt injection"}).text
    assert "SEC-02" in found and "FAI-04" not in found
    fairness = client.get("/library", params={"l1": "FAI"}).text
    assert "FAI-04" in fairness and "SEC-02" not in fairness
    assert 'class="line-id"' not in client.get("/library", params={"q": "zzzz-nothing"}).text


def test_line_page_shows_every_column(empty_org):
    text = _client(empty_org).get("/library/HUM-01").text
    for value in ("Automation bias", "Override rate", "AI Act Art 14(4)(b), 26(2)", "A.9.3"):
        assert value in text
    assert _client(empty_org).get("/library/NOPE-99").status_code == 404


def test_proposals_for_the_credit_scoring_system(fixture_org):
    resp = _client(fixture_org.path).get("/library/propose", params={"system": "SYS-001"})
    assert resp.status_code == 200
    for line_id in ("FAI-04", "HUM-01", "TRA-02", "LEG-07"):
        assert f'value="{line_id}"' in resp.text          # an Adopt button for each
    assert "AI Act Art 25: configuring or repurposing a system" in resp.text
    assert "removed: a provider" in resp.text              # the removed lines, with reasons
    assert "straw man" in resp.text


def test_propose_without_a_system_offers_the_inventory(empty_org):
    resp = _client(empty_org).get("/library/propose")
    assert resp.status_code == 200
    assert "/inventory/new" in resp.text
    assert _client(empty_org).get("/library/propose", params={"system": "SYS-404"}).status_code == 404


def test_adopting_creates_a_candidate_register_line_with_the_same_id(fixture_org):
    client = _client(fixture_org.path)
    resp = client.post("/library/adopt", data={"line_id": "HUM-01", "system_id": "SYS-001"},
                       follow_redirects=False)
    assert resp.status_code == 303
    (entity_id, field, new, actor, reason), = _register_events(fixture_org.path)
    assert (entity_id, field, actor) == ("HUM-01", None, "tester")
    with Store(fixture_org.path) as store:
        line = store.state()["register"]["HUM-01"]
    assert (line["id"], line["source"], line["status"], line["system_id"]) == (
        "HUM-01", "library", "candidate", "SYS-001")
    assert line["annex_a_controls"] == ["A.9.3"]
    page = client.get("/library/propose", params={"system": "SYS-001"}).text
    assert "In the register" in page and 'value="HUM-01"' not in page


def test_adopting_twice_is_refused(fixture_org):
    client = _client(fixture_org.path)
    client.post("/library/adopt", data={"line_id": "HUM-01", "system_id": "SYS-001"})
    for system_id in ("SYS-001", "SYS-003"):
        resp = client.post("/library/adopt", data={"line_id": "HUM-01", "system_id": system_id})
        assert resp.status_code == 409
        assert "HUM-01 is already in the register" in resp.text
    assert len(_register_events(fixture_org.path)) == 1


def test_adopt_refuses_unknown_line_or_system(fixture_org):
    client = _client(fixture_org.path)
    assert client.post("/library/adopt", data={"line_id": "NOPE-99",
                                               "system_id": "SYS-001"}).status_code == 404
    assert client.post("/library/adopt", data={"line_id": "HUM-01",
                                               "system_id": "SYS-404"}).status_code == 404
    assert _register_events(fixture_org.path) == []


def test_adopt_from_another_site_is_refused(fixture_org):
    resp = _client(fixture_org.path).post(
        "/library/adopt", data={"line_id": "HUM-01", "system_id": "SYS-001"},
        headers={"Origin": "http://evil.example"})
    assert resp.status_code == 403
    assert _register_events(fixture_org.path) == []


def test_library_is_in_the_navigation(empty_org):
    text = _client(empty_org).get("/inventory").text
    assert 'href="/library"' in text


def test_adopting_a_removed_line_records_why_it_was_removed(fixture_org):
    # SYS-002 is a deployer; SEC-03 is a provider's line, so the filter removes it.
    _client(fixture_org.path).post("/library/adopt", data={"line_id": "SEC-03",
                                                           "system_id": "SYS-002"})
    (_, _, _, _, reason), = _register_events(fixture_org.path)
    assert "although the filter removed it" in reason and "a provider's concern" in reason
