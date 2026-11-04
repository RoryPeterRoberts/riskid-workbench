"""Round 14 Settings (PLAN.md round 14; SPEC.md 6.13, 8, 10).

The organisation, the people and who is recording, the assistant (off until an
endpoint is set), the data packs, the encryption warning, and the backup.
"""

import sqlite3

import pytest
from fastapi.testclient import TestClient

from riskid.app import create_app
from riskid.store import Store

BASE = "http://127.0.0.1:8765"
ASSISTANT = {"enabled": "on", "endpoint": "http://127.0.0.1:8085/v1", "model": "qwen3.8-27b",
             "version": "2026-10", "local": "on"}


@pytest.fixture
def org(fixture_org):
    return TestClient(create_app(fixture_org.path, actor="tester"), base_url=BASE), fixture_org.path


def _state(path):
    with Store(path) as store:
        return store.state()


def test_settings_renders_with_the_packs_and_the_encryption_warning(org):
    client, _ = org
    page = client.get("/settings").text
    assert "library 1.0" in page.replace("</td><td>", " ") and "not encrypted" in page


def test_the_organisation_is_recorded(org):
    client, path = org
    assert client.post("/settings/organisation", data={"name": ""}).status_code == 422
    client.post("/settings/organisation", data={"name": "Fixture Bank", "sector": "banking",
                                                "jurisdictions": "IE, EU", "accountable_executive": "CFO",
                                                "ai_officer": "Ola Byrne", "facilitator": "Sam"})
    organisation = _state(path)["organisation"]["organisation"]
    assert organisation["name"] == "Fixture Bank" and organisation["jurisdictions"] == ["IE", "EU"]


def test_a_person_recording_is_the_actor_on_later_changes(org):
    client, path = org
    assert client.post("/settings/people", data={"name": "", "role": "AI officer"}).status_code == 422
    client.post("/settings/people", data={"name": "Ola Byrne", "role": "AI officer"})
    assert _state(path)["person"]["P-001"] == {"name": "Ola Byrne", "role": "AI officer"}
    assert client.post("/settings/actor", data={"name": "Someone Else"}).status_code == 422
    client.post("/settings/actor", data={"name": "Ola Byrne"})
    client.post("/library/adopt", data={"line_id": "HUM-01", "system_id": "SYS-001"})
    with Store(path) as store:
        assert store.events()[-1]["actor"] == "Ola Byrne"
    assert "Recording as Ola Byrne" in client.get("/settings").text


def test_the_assistant_is_off_until_an_endpoint_is_set(org):
    client, path = org
    assert "settings" not in _state(path)
    assert "The assistant is off" in client.get("/settings").text
    assert client.post("/settings/assistant", data={"enabled": "on"}).status_code == 422
    for bad in ("file:///etc/passwd", "javascript:alert(1)", "127.0.0.1:8085"):
        assert client.post("/settings/assistant", data=dict(ASSISTANT, endpoint=bad)).status_code == 422
    # A shared file must not be able to have another secret sent as the key.
    other_secret = dict(ASSISTANT, key_env="AWS_SECRET_ACCESS_KEY")
    assert client.post("/settings/assistant", data=other_secret).status_code == 422
    client.post("/settings/assistant", data=ASSISTANT)
    assistant = _state(path)["settings"]["assistant"]
    assert assistant["enabled"] and assistant["endpoint"] == "http://127.0.0.1:8085/v1"
    client.post("/settings/assistant", data=dict(ASSISTANT, enabled=""))
    assert not _state(path)["settings"]["assistant"]["enabled"]


def test_the_backup_is_a_copy_of_the_file_and_is_recorded(org, tmp_path):
    client, path = org
    resp = client.get("/settings/backup.riskid")
    assert resp.status_code == 200 and resp.content.startswith(b"SQLite format 3\x00")
    copy = tmp_path / "copy.riskid"
    copy.write_bytes(resp.content)
    with Store(copy) as store:
        assert sorted(store.state()["system"]) == ["SYS-001", "SYS-002", "SYS-003"]
    assert [d["kind"] for d in _state(path)["document"].values()] == ["backup"]
    with sqlite3.connect(copy) as conn:
        assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


def test_a_backup_that_cannot_write_its_copy_still_closes_the_file(org, monkeypatch):
    client, _ = org
    from riskid.web import routes_settings
    opened, real_connect = [], sqlite3.connect

    def connect(target, *args, **kwargs):
        if str(target).endswith("backup.riskid"):
            raise sqlite3.OperationalError("disk full")
        if not kwargs.get("uri"):
            return real_connect(target, *args, **kwargs)
        # The backup's read-only source, usable from this thread so the test can see whether it closed.
        opened.append(real_connect(target, *args, check_same_thread=False, **kwargs))
        return opened[-1]

    monkeypatch.setattr(routes_settings.sqlite3, "connect", connect)
    with pytest.raises(sqlite3.OperationalError):
        client.get("/settings/backup.riskid")
    with pytest.raises(sqlite3.ProgrammingError, match="closed"):  # closed, not left open
        opened[0].execute("SELECT 1")


def test_settings_renders_for_an_empty_organisation(tmp_path):
    from riskid.store import init
    init(tmp_path / "e.riskid").close()
    client = TestClient(create_app(tmp_path / "e.riskid", actor="t"), base_url=BASE)
    assert client.get("/settings").status_code == 200
