"""Round 14 the assistant (PLAN.md round 14; SPEC.md 5.9 and 8; chapter 14).

The plan's checks: the assistant is off until an endpoint is set; with a stub
endpoint a drafted field carries ai_draft and counts as Very Low until
accepted; acceptance records the person. Also: only the screen's fields are
sent, each request is logged, an answer that does not fit the schema is
refused, a cut generation is asked again without thinking, and a draft can be
discarded.
"""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from fastapi.testclient import TestClient

from riskid import rules
from riskid.ai import prompts
from riskid.app import create_app
from riskid.store import Store

BASE = "http://127.0.0.1:8765"
DRAFT = {"risk_id": "", "taxonomy": "2.3", "definition": "The supplier changes the model behind the API",
         "drivers_direct": "The contract allows changes without notice", "drivers_indirect": "One supplier",
         "metrics": "not stated", "qualitative": "not stated", "indicators": "a deprecation notice",
         "controls": [{"name": "Version pinning", "type": "preventive", "evidence": "not stated"}],
         "data_quality_basis": "the supplier's documentation only"}


class Stub:
    """An OpenAI-compatible endpoint that records each request and answers from a queue."""

    def __init__(self):
        self.requests, self.headers, self.answers = [], [], []
        stub = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                stub.headers.append(dict(self.headers))
                stub.requests.append(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
                body = json.dumps(stub.answers.pop(0)).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.endpoint = f"http://127.0.0.1:{self.server.server_port}/v1"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    @staticmethod
    def answer(content, finish="stop"):
        return {"model": "stub-27b", "choices": [{"message": {"content": content}, "finish_reason": finish}],
                "usage": {"prompt_tokens": 900, "completion_tokens": 300}}


@pytest.fixture
def stub():
    s = Stub()
    yield s
    s.server.shutdown()


@pytest.fixture
def org(fixture_org):
    return TestClient(create_app(fixture_org.path, actor="tester"), base_url=BASE), fixture_org.path


def _switch_on(client, endpoint, local="on"):
    client.post("/settings/assistant", data={"enabled": "on", "endpoint": endpoint, "model": "stub-27b",
                                             "version": "2026-10", "local": local})


def _state(path):
    with Store(path) as store:
        return store.state()


def test_the_assistant_is_off_until_an_endpoint_is_set(org, stub):
    client, path = org
    assert "Draft with the assistant" not in client.get("/usecases/new?system=SYS-002").text
    assert client.post("/usecases/draft", data={"system_id": "SYS-002"}).status_code == 409
    assert stub.requests == [] and "usecase" not in _state(path)


def test_a_draft_carries_ai_draft_and_counts_as_very_low_until_a_person_accepts_it(org, stub):
    client, path = org
    _switch_on(client, stub.endpoint)
    assert "Draft with the assistant" in client.get("/usecases/new?system=SYS-002").text
    stub.answers.append(Stub.answer(json.dumps(DRAFT)))
    resp = client.post("/usecases/draft", data={"system_id": "SYS-002"}, follow_redirects=False)
    assert resp.status_code == 303 and resp.headers["location"] == "/usecases/UC-001"
    usecase = _state(path)["usecase"]["UC-001"]
    assert usecase["status"] == "draft" and usecase["submitted_by"] is None
    assert usecase["ai_draft"]["model"] == "stub-27b" and usecase["ai_draft"]["version"] == "2026-10"
    assert "definition" in usecase["ai_draft"]["fields"] and usecase["fields_"]["owner"] == ""
    assert rules.ai_draft_quality({"ai_draft": usecase["ai_draft"], "data_quality": "Medium"}) == "Very Low"
    page = client.get("/usecases/UC-001").text
    assert "Drafted by the assistant" in page and "Very Low" in page
    # A person checks it, names the owner, rates it and submits: that is the acceptance.
    with Store(path) as store:
        drafted_event = store.events()[-1]
    assert json.loads(drafted_event["ai_draft"]) == {"model": "stub-27b", "version": "2026-10"}
    assert drafted_event["actor"] == "tester"
    form = {"system_id": "SYS-002", "header_role": "deployer", "taxonomy": "2.3",
            "definition": DRAFT["definition"], "drivers_direct": DRAFT["drivers_direct"],
            "owner": "Head of Customer Service", "data_quality": "Low",
            "data_quality_basis": DRAFT["data_quality_basis"]}
    client.post("/usecases/UC-001", data=form)
    usecase = _state(path)["usecase"]["UC-001"]
    assert usecase["ai_draft"]["accepted_by"] == "tester" and usecase["submitted_by"] == "tester"
    assert usecase["status"] == "accepted" and usecase["line_id"] == "ORG-001"
    assert rules.ai_draft_quality({"ai_draft": usecase["ai_draft"], "data_quality": "Low",
                                   "accepted": usecase["ai_draft"]["accepted_by"]}) == "Low"


def test_only_the_screens_fields_are_sent_and_the_request_is_logged(org, stub):
    client, path = org
    _switch_on(client, stub.endpoint)
    stub.answers.append(Stub.answer(json.dumps(DRAFT)))
    client.post("/usecases/draft", data={"system_id": "SYS-002"})
    sent = json.dumps(stub.requests[0])
    assert "Customer-service chatbot" in sent                       # SYS-002's header line
    assert "CV-screening" not in sent and "Meridian" not in sent     # nothing from the other systems
    assert stub.requests[0]["chat_template_kwargs"]["reasoning_effort"] == "medium"
    assert stub.requests[0]["response_format"]["json_schema"]["schema"] == prompts.KINDS["use_case"]["schema"]
    log = _state(path)["ai_request"]["AIR-001"]
    assert log["tokens"] == {"prompt": 900, "completion": 300} and log["outcome"] == "draft UC-001"


def test_an_answer_that_does_not_fit_the_schema_is_refused(org, stub):
    client, path = org
    _switch_on(client, stub.endpoint)
    stub.answers.append(Stub.answer(json.dumps({"definition": 3})))
    assert client.post("/usecases/draft", data={"system_id": "SYS-002"}).status_code == 502
    assert "usecase" not in _state(path) and "did not fit" in _state(path)["ai_request"]["AIR-001"]["outcome"]


def test_a_taxonomy_answered_with_its_name_is_read_as_its_code(org, stub):
    client, path = org
    _switch_on(client, stub.endpoint)
    stub.answers.append(Stub.answer(json.dumps(dict(DRAFT, taxonomy="2.3 - Drift and degradation",
                                                    controls=[{"name": "not stated", "type": "preventive",
                                                               "evidence": "not stated"}]))))
    client.post("/usecases/draft", data={"system_id": "SYS-002"})
    fields = _state(path)["usecase"]["UC-001"]["fields_"]
    assert fields["taxonomy"] == "2.3" and fields["controls"] == []     # an unnamed control is dropped


def test_a_cut_generation_is_asked_again_without_thinking(org, stub):
    client, path = org
    _switch_on(client, stub.endpoint)
    stub.answers += [Stub.answer("", finish="length"), Stub.answer("```json\n" + json.dumps(DRAFT) + "\n```")]
    client.post("/usecases/draft", data={"system_id": "SYS-002"})
    assert [r["chat_template_kwargs"]["enable_thinking"] for r in stub.requests] == [True, False]
    assert _state(path)["ai_request"]["AIR-001"]["tokens"] == {"prompt": 1800, "completion": 600}


def test_a_hosted_endpoint_gets_no_local_server_settings(org, stub):
    client, _ = org
    _switch_on(client, stub.endpoint, local="")
    stub.answers.append(Stub.answer(json.dumps(DRAFT)))
    client.post("/usecases/draft", data={"system_id": "SYS-002"})
    assert "chat_template_kwargs" not in stub.requests[0]


def test_the_key_is_read_only_from_a_riskid_variable(org, stub, monkeypatch):
    client, path = org
    _switch_on(client, stub.endpoint)
    monkeypatch.setenv("RISKID_AI_KEY", "test-key")
    stub.answers.append(Stub.answer(json.dumps(DRAFT)))
    client.post("/usecases/draft", data={"system_id": "SYS-002"})
    assert stub.headers[0].get("Authorization") == "Bearer test-key"
    # A file whose setting names another variable (written around the form) sends nothing.
    with Store(path) as store:
        from riskid.model import Event
        assistant = dict(store.state()["settings"]["assistant"], key_env="HOME")
        store.append(Event(entity="settings", entity_id="assistant", new=assistant, actor="someone else"))
    assert client.post("/usecases/draft", data={"system_id": "SYS-002"}).status_code == 502
    assert len(stub.requests) == 1


def test_a_draft_can_be_discarded(org, stub):
    client, path = org
    _switch_on(client, stub.endpoint)
    stub.answers.append(Stub.answer(json.dumps(DRAFT)))
    client.post("/usecases/draft", data={"system_id": "SYS-002"})
    client.post("/usecases/UC-001/discard")
    assert _state(path)["usecase"]["UC-001"]["status"] == "discarded"
    assert client.post("/usecases/UC-001/discard").status_code == 409
    assert client.post("/usecases/UC-001", data={"system_id": "SYS-002"}).status_code == 409
    assert "draft discarded" in client.get("/usecases").text


def test_every_schema_checks_its_kind():
    good = {"use_case": DRAFT, "swift_answers": {"status": "covered", "control": "pinning", "evidence": "x"},
            "library_lines": {"lines": [{"line_id": "MOD-05", "why": "a vendor model"}]},
            "trigger_summary": {"summary": "s", "lines": []},
            "report_narrative": {"sections": [{"item": 2, "narrative": "n"}]}}
    for kind, value in good.items():
        assert prompts.check(kind, value) == [], kind
    assert prompts.check("swift_answers", {"status": "maybe", "control": "", "evidence": ""})
    assert prompts.check("report_narrative", {"sections": [{"item": 13, "narrative": "n"}]})
    assert prompts.check("report_narrative", {"sections": [{"item": True, "narrative": "n"}]})
    assert prompts.check("library_lines", [])
    assert set(prompts.KINDS) == {"use_case", "swift_answers", "library_lines", "trigger_summary",
                                  "report_narrative"}
    for kind in prompts.KINDS:                          # the assistant may set no score, rating or owner
        assert not {"owner", "data_quality", "score", "likelihood"} & set(prompts.KINDS[kind]["schema"]["properties"])
