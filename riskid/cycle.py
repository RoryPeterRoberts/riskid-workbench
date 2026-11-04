"""The ongoing cycle (chapter 13; B.8; SPEC.md 5.7, 5.8, 5.10).

Indicator status against its thresholds; the lines a trigger touches; what
each B.8 step can be shown from the register; and which steps still lack
evidence before sign-off.

A trigger touches a line in three ways, each given as the reason: the text
names the line; the text cites an article the line's regulatory hooks cite
(the Harness's article lookup); or the text shares words with one of the
line's indicators. The last is a suggestion for the person deciding its
significance, who records the decision.
"""

from __future__ import annotations

import re
from datetime import date, timedelta

from riskid import importers, rules
from riskid.assess import latest_assessments
from riskid.propose import line_hooks

DIRECTIONS = ("higher is worse", "lower is worse")
_ARTICLE = re.compile(r"\b(GDPR|AI Act)?\s*Art(?:icle)?s?\.?\s*([0-9]+)", re.I)
_LINE_ID = re.compile(r"\b[A-Z]{3}-[0-9]{2}\b")
_WORD = re.compile(r"[a-z][a-z-]+")
_STOP = {"with", "from", "that", "this", "against", "where", "when", "which", "their", "about",
         "would", "there", "these", "those", "other", "after", "before", "notice", "share", "rate"}


def status(indicator: dict) -> str:
    """green, amber or red for the current value against the thresholds; '' when not set."""
    value, t = indicator.get("current_value"), indicator.get("thresholds") or {}
    if value is None or t.get("amber") is None or t.get("red") is None:
        return ""
    worse = (lambda v, limit: v >= limit) if t.get("direction") != "lower is worse" else (lambda v, limit: v <= limit)
    return "red" if worse(value, t["red"]) else "amber" if worse(value, t["amber"]) else "green"


def check_thresholds(amber: float, red: float, direction: str) -> list:
    if direction not in DIRECTIONS:
        return ["Indicator: say whether higher or lower is worse."]
    if (direction == "higher is worse" and red <= amber) or (direction == "lower is worse" and red >= amber):
        return ["Indicator: the red threshold lies beyond the amber one, in the direction that is worse."]
    return []


def _words(text: str) -> set:
    return {w for w in _WORD.findall((text or "").lower()) if len(w) >= 4 and w not in _STOP}


def touched_lines(text: str, state: dict, presets: list) -> list:
    """``[{"line_id", "why"}]``: the live lines a trigger's text touches, and why."""
    live = {i: l for i, l in state.get("register", {}).items() if l.get("status") != "retired"}
    found: dict = {}
    for line_id in _LINE_ID.findall(text or ""):
        if line_id in live:
            found.setdefault(line_id, []).append("named in the trigger")
    cited = {((inst or "AI Act").upper().replace("AI ACT", "AI Act"), int(n)) for inst, n in _ARTICLE.findall(text or "")}
    words = _words(text)
    names = {}
    for preset in presets:
        for line_id in preset["lines"]:
            names.setdefault(line_id, []).append(preset["name"])
    for kri in state.get("indicator", {}).values():
        names.setdefault(kri.get("line_id"), []).append(kri.get("name") or "")
    for line_id, line in sorted(live.items()):
        hooks = line_hooks({"reg": "; ".join(line.get("regulatory_hooks") or [])})
        for inst, article in sorted(cited & hooks):
            found.setdefault(line_id, []).append(f"its regulatory hooks cite {inst} Art {article}")
        for name in names.get(line_id, []):
            shared = sorted(words & _words(name))
            if len(shared) >= 2 or any(len(w) >= 7 for w in shared):
                found.setdefault(line_id, []).append(f"its indicator '{name}' shares: {', '.join(shared)}")
    return [{"line_id": i, "why": "; ".join(dict.fromkeys(why))} for i, why in sorted(found.items())]


def material_systems(state: dict) -> set:
    latest = latest_assessments(state)
    return {l.get("system_id") for i, l in state.get("register", {}).items()
            if l.get("status") != "retired" and latest.get(i, (None, {}))[1].get("material")}


def pending_trigger_dates(state: dict) -> dict:
    """``{line_id: date}``: the earliest trigger touching each line that still awaits its decision."""
    out: dict = {}
    for t in state.get("trigger", {}).values():
        if not t.get("significance"):
            for touched in t.get("lines_touched") or []:
                out[touched["line_id"]] = min(t["date"], out.get(touched["line_id"], t["date"]))
    return out


def step_findings(state: dict, today: str, since: str | None, events: list) -> dict:
    """What the register shows for the B.8 steps it can answer: ``{step: [finding]}``.

    ``today`` is the run's date; ``since`` is when the previous run was signed
    (``None`` for the first run), and ``events`` the part of the audit trail
    the run covers.
    """
    systems = state.get("system", {})
    material = material_systems(state)
    latest = latest_assessments(state)
    live = {i: l for i, l in state.get("register", {}).items() if l.get("status") != "retired"}
    material_lines = sorted(i for i in live if latest.get(i, (None, {}))[1].get("material"))
    out: dict = {}
    discovery = sorted(state.get("discovery", {}).values(), key=lambda d: d["quarter"])
    out[1] = ([f"{d['quarter']}: {d['found']} tools found against {d['inventoried']} inventoried."
               for d in discovery[-1:]] or ["No discovery ratio recorded on the Inventory."])
    out[2] = [f"{i} {s.get('name')}: pilot ended {s.get('pilot_end_date')}, still at {s.get('lifecycle_stage')}."
              for i, s in sorted(systems.items()) if rules.pilot_overdue(s, today)] or ["No pilot is past its end date."]
    out[3] = [f"{i} {systems[i].get('name')} is material and has no named owner."
              for i in sorted(material) if i in systems and not systems[i].get("owner")] or [
                 "Every material system has a named owner." if material else "No system is material yet."]
    out[4] = [f"{i} {s.get('name')}: running {s.get('model_version')}, assessed "
              f"{(s.get('last_risk_assessment') or {}).get('version')}"
              f"{' (material: flag it)' if i in material else ' (not yet material)'}."
              for i, s in sorted(systems.items()) if rules.version_mismatch(s)] or [
                 "Every system's assessed version is the version running."]
    horizon = (date.fromisoformat(today) + timedelta(days=365)).isoformat()
    out[6] = [f"{e['as_written']}, {e['role']}: {e['applies']} (Art {e['articles']})."
              for e in importers.load_calendar() if e["applies_from"] and today <= e["applies_from"] <= horizon] or [
                 "No new dates in the next twelve months on the calendar."]
    triggers = state.get("trigger", {})
    logged = [k for k, t in triggers.items() if since is None or t.get("date", "") > since[:10]]
    out[8] = [f"{len(logged)} triggers dated since the last signed run." if since
              else f"{len(logged)} triggers in the log."] + [
        f"{k} has no significance decision." for k, t in sorted(triggers.items()) if not t.get("significance")]
    watched = {kri.get("line_id") for kri in state.get("indicator", {}).values()}
    out[9] = [f"{k} on {kri['line_id']} is {status(kri)}: {kri.get('name')} = {kri.get('current_value')}"
              for k, kri in sorted(state.get("indicator", {}).items()) if status(kri) in ("amber", "red")] + [
        f"{i} is material and has no indicator." for i in material_lines if i not in watched]
    out[9] = out[9] or ["No indicator is amber or red, and every material line has one."]
    stale = [i for i in material_lines if since and latest[i][1].get("date", "") <= since[:10]]
    out[12] = [f"{i} was last assessed on {latest[i][1].get('date')}, before the last signed run."
               for i in stale] or (["Every material line has been assessed since the last signed run."]
                                   if since else ["No earlier signed run to compare with."])
    changes = [e for e in events if e["entity"] == "register"]
    out[16] = [f"{len(changes)} changes to the register {'since the last signed run' if since else 'so far'} "
               "(the change list in the quarterly pack)."]
    open_dl = [k for k, d in sorted(state.get("disagreement", {}).items()) if d.get("status") == "open"]
    out[15] = [f"{len(open_dl)} open disagreements: {', '.join(open_dl)}."] if open_dl else ["No open disagreements."]
    return out


def missing_evidence(run: dict, steps: list) -> list:
    """The step numbers that have no evidence recorded."""
    recorded = run.get("steps") or {}
    return [s["n"] for s in steps if not (recorded.get(str(s["n"])) or {}).get("evidence")]
