"""The top-down workshop's method (chapter 6; templates B.4 and B.5).

The six stages and eight seats of B.5, the candidates the room votes on, the
ranking rule of chapter 6, and the differences between the business owner's
votes and those of the overseer, the data protection officer and security
(which go to the disagreement log). Nothing here averages: "A risk that every
participant votes for once outranks one that a single participant votes for
heavily, so the most senior view does not decide the order" (chapter 6).
"""

from __future__ import annotations

import re

STAGES = (
    {"n": 1, "name": "Opening", "duration": "15 minutes",
     "purpose": "State the objectives, the ground rules and the system and version in scope; "
                "the straw man is there to be challenged",
     "for_ai": "Name the version running today"},
    {"n": 2, "name": "Independent assessment review", "duration": "30 minutes",
     "purpose": "Show the anonymised results of the written pre-workshop lists and where they disagree",
     "for_ai": "Each participant wrote a top-ten list before seeing the straw man, the sceptic included"},
    {"n": 3, "name": "SWIFT rounds", "duration": "90 to 120 minutes",
     "purpose": "Systematic what-if questioning of each element", "for_ai": "Use the prompt set in B.4"},
    {"n": 4, "name": "Emerging risk session", "duration": "30 minutes",
     "purpose": "Risks not yet in the taxonomy",
     "for_ai": "Agents, new supplier features, new capability; items for the Delphi rounds"},
    {"n": 5, "name": "Multivoting", "duration": "20 minutes",
     "purpose": "Each participant allocates votes to the risks they rate highest",
     "for_ai": "Record the votes; do not average away a dissent"},
    {"n": 6, "name": "Gap review", "duration": "15 minutes",
     "purpose": "Check the output against the taxonomy and the register",
     "for_ai": "Add to the taxonomy gap list"},
)

SEATS = (
    {"role": "Business owner", "why": "Answers for the outcomes of the system"},
    {"role": "Data science lead or model owner", "why": "Knows how the system works and how it fails"},
    {"role": "Security", "why": "Brings the attacker's view"},
    {"role": "Data protection officer", "why": "Brings the view of the people whose data is processed"},
    {"role": "Overseer", "why": "Reviews outputs or overrides the system day to day"},
    {"role": "Sceptic", "why": "Has a written remit to argue that the system should not be used or "
                               "that the list is incomplete"},
    {"role": "Procurement or legal", "why": "Added where the portfolio depends on bought systems"},
    {"role": "Facilitator (the AI officer)", "why": "Runs the session and records it; does not report "
                                                    "to the owner of any system under discussion"},
)

# The seats whose votes chapter 6 compares with the business owner's.
COMPARED_SEATS = ("Overseer", "Data protection officer", "Security")
ANSWERS = ("covered", "not known")
MAX_LIST = 10

LINE_ID = re.compile(r"\b[A-Z]{3}-[0-9]{2}\b")


def pre_list_items(text: str) -> tuple[list, list]:
    """A participant's top-ten list, one risk per line; ``(items, reasons)``."""
    items = [line.strip() for line in (text or "").splitlines() if line.strip()]
    reasons = [] if len(items) <= MAX_LIST else ["A pre-workshop list holds ten risks at most."]
    return items, reasons


def check_answer(status: str, control: str, evidence: str) -> list:
    """B.4: an answer is covered, with the control and its evidence, or not known."""
    if status not in ANSWERS:
        return ["Record the answer as covered or not known (B.4)."]
    if status == "covered" and not (control and evidence):
        return ["Covered needs the control and its evidence (B.4)."]
    return []


def check_votes(allocation: dict, allowance: int, candidate_ids) -> list:
    """A participant's votes: on candidates only, and no more than the allowance."""
    reasons = [f"{c} is not a candidate." for c in allocation if c not in candidate_ids]
    total = sum(allocation.values())
    if total > allowance:
        reasons.append(f"{total} votes placed; the allowance is {allowance}.")
    return reasons


def candidates(workshop: dict, swift: list, known_ids) -> list:
    """What the room votes on: register lines named in the pre-workshop lists, the lines
    of SWIFT prompts answered "not known", and the emerging risks (E1, E2, ...).

    Each candidate says where it came from. Lines keep the order they first appear in.
    """
    found: dict = {}

    def note(line_id, source):
        found.setdefault(line_id, {"id": line_id, "kind": "line", "from": []})["from"].append(source)

    mentions: dict = {}
    for items in (workshop.get("pre_lists") or {}).values():
        for line_id in dict.fromkeys(m for item in items for m in LINE_ID.findall(item)):
            if line_id in known_ids:
                mentions[line_id] = mentions.get(line_id, 0) + 1
    for line_id, count in mentions.items():
        note(line_id, f"{count} pre-workshop list" + ("s" if count > 1 else ""))
    answers = workshop.get("swift_answers") or {}
    for prompt in swift:
        if (answers.get(str(prompt["id"])) or {}).get("status") == "not known":
            for line_id in prompt["lines"]:
                note(line_id, f"SWIFT prompt {prompt['id']}")
    ordered = list(found.values())
    for i, risk in enumerate(workshop.get("emerging_risks") or [], start=1):
        ordered.append({"id": f"E{i}", "kind": "emerging", "title": risk["title"],
                        "from": ["emerging risk session"]})
    return ordered


def ranking(votes: dict) -> list:
    """Candidates by how many participants voted for them, then by votes placed.

    Each entry keeps every participant's own votes (``by_participant``); there
    is no average, so a dissent stays visible.
    """
    table: dict = {}
    for participant, allocation in (votes or {}).items():
        for candidate, n in allocation.items():
            if n > 0:
                entry = table.setdefault(candidate, {"id": candidate, "voters": 0, "votes": 0,
                                                     "by_participant": {}})
                entry["voters"] += 1
                entry["votes"] += n
                entry["by_participant"][participant] = n
    return sorted(table.values(), key=lambda e: (-e["voters"], -e["votes"], e["id"]))


def seat_differences(votes: dict, seats: list) -> list:
    """Where the overseer, the DPO or security voted differently from the business owner.

    "Differently" means one of them put votes on a candidate and the other put
    none. These go to the disagreement log (chapter 6).
    """
    person = {s["role"]: s.get("person") for s in seats if s.get("person")}
    owner = person.get("Business owner")
    if not owner:
        return []
    owner_votes = (votes or {}).get(owner, {})
    diffs = []
    for role in COMPARED_SEATS:
        other = person.get(role)
        if not other:
            continue
        theirs = (votes or {}).get(other, {})
        for candidate in sorted(set(owner_votes) | set(theirs)):
            mine, yours = owner_votes.get(candidate, 0), theirs.get(candidate, 0)
            if (mine == 0) != (yours == 0):
                diffs.append({"candidate": candidate, "seat": role, "person": other,
                              "votes": yours, "owner_votes": mine})
    return diffs
