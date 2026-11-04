"""The optional AI assistant (SPEC.md section 8): one OpenAI-compatible chat request per draft.

Off until the practitioner sets an endpoint and a model in Settings and switches
it on. A draft sends only the fields of the screen it is drafted for, asks for
JSON against the draft kind's schema (``riskid.ai.prompts``), and is checked
against that schema before anything is shown. It returns the draft with the
model, the version and the token counts, which the caller records as an
``ai_request`` event in the name of the person who asked: the assistant never
writes to the audit trail as an actor.

The endpoint is the server's base address, such as ``http://127.0.0.1:8085/v1``.
For a local server (vLLM or Ollama with a 27B model) the request carries the
November 2026 settings: reasoning effort medium, and when the reasoning uses up
the token budget before any answer, one more request with thinking off, so a
cut generation still returns its draft. The API key, if one is needed, is read
from the environment variable Settings names, which must start ``RISKID_`` so a
file shared by someone else cannot have any other secret sent; the key is
never stored in the file.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from riskid.ai import prompts

DEFAULT_KEY_ENV = "RISKID_AI_KEY"
KEY_ENV_PREFIX = "RISKID_"
MAX_TOKENS = 8000
TIMEOUT = 600


class AssistantError(Exception):
    """The assistant is off, its endpoint failed, or its answer did not fit the schema."""


def assistant_settings(state: dict) -> dict:
    return state.get("settings", {}).get("assistant") or {}


def is_on(settings: dict) -> bool:
    return bool(settings.get("enabled") and settings.get("endpoint") and settings.get("model"))


def _ask(settings: dict, kind: str, fields: dict, thinking: bool) -> dict:
    body = {"model": settings["model"], "max_tokens": MAX_TOKENS, "temperature": 0.2,
            "messages": [{"role": "system", "content": prompts.SYSTEM},
                         {"role": "user", "content": prompts.message(kind, fields)}],
            "response_format": {"type": "json_schema",
                                "json_schema": {"name": kind, "schema": prompts.KINDS[kind]["schema"]}}}
    if settings.get("local"):
        body["chat_template_kwargs"] = {"enable_thinking": thinking, "reasoning_effort": "medium"}
    headers = {"Content-Type": "application/json"}
    key_env = settings.get("key_env") or DEFAULT_KEY_ENV
    if not key_env.startswith(KEY_ENV_PREFIX):
        raise AssistantError(f"The API key's variable must start {KEY_ENV_PREFIX}; {key_env} is not read.")
    key = os.environ.get(key_env)
    if key:
        headers["Authorization"] = f"Bearer {key}"
    request = urllib.request.Request(settings["endpoint"].rstrip("/") + "/chat/completions",
                                     data=json.dumps(body).encode(), headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            return json.loads(response.read().decode())
    except (OSError, ValueError) as exc:          # URLError and timeouts are OSErrors; bad JSON a ValueError
        raise AssistantError(f"The assistant at {settings['endpoint']} did not answer: {exc}") from exc


def _content(answer: dict) -> tuple:
    choice = (answer.get("choices") or [{}])[0]
    text = ((choice.get("message") or {}).get("content") or "").strip()
    if text.startswith("```"):                     # a fenced answer: keep what is inside the fence
        text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    return text, choice.get("finish_reason")


def draft(settings: dict, kind: str, fields: dict) -> dict:
    """``{"draft", "model", "version", "tokens"}`` for one draft of ``kind`` made from ``fields``."""
    if not is_on(settings):
        raise AssistantError("The assistant is off; Settings switches it on.")
    answers = [_ask(settings, kind, fields, thinking=True)]
    text, finish = _content(answers[0])
    if not text and finish == "length" and settings.get("local"):
        answers.append(_ask(settings, kind, fields, thinking=False))
        text, finish = _content(answers[-1])
    try:
        drafted = json.loads(text)
    except ValueError as exc:
        raise AssistantError(f"The assistant's answer was not JSON (finish: {finish}).") from exc
    problems = prompts.check(kind, drafted)
    if problems:
        raise AssistantError("The draft did not fit its schema: " + "; ".join(problems[:5]))
    usage = [a.get("usage") or {} for a in answers]
    return {"draft": drafted, "model": answers[-1].get("model") or settings["model"],
            "version": settings.get("version") or answers[-1].get("system_fingerprint") or "not reported",
            "tokens": {"prompt": sum(u.get("prompt_tokens") or 0 for u in usage),
                       "completion": sum(u.get("completion_tokens") or 0 for u in usage)}}
