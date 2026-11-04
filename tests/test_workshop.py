"""Round 7: the workshop's method (PLAN.md round 7; B.4, B.5; chapter 6).

swift.json matches the book's B.4 table; the candidates for multivoting; the
ranking rule of chapter 6 (a risk every participant votes for once outranks
one a single participant votes for heavily); no average anywhere; the seats
whose votes differ from the business owner's; the checks on answers, lists
and votes.
"""

import re
from pathlib import Path

from riskid import importers
from riskid.workshop import (SEATS, STAGES, candidates, check_answer, check_votes, pre_list_items,
                             ranking, seat_differences)

BOOK_TABLES = Path(__file__).parent.parent / "docs" / "BOOK_TABLES.md"


def test_swift_json_is_the_book_table():
    text = BOOK_TABLES.read_text(encoding="utf-8")
    table = text[text.index("## B.4 SWIFT"):text.index("## B.5")]
    rows = [m.groups() for m in re.finditer(r"^\| (\d+) \| (.+?) \| (.+?) \|$", table, re.M)]
    prompts = importers.load_swift()
    assert len(prompts) == 23 == len(rows)
    for prompt, (n, words, lines) in zip(prompts, rows):
        assert (prompt["id"], prompt["prompt"]) == (int(n), words)
        assert prompt["lines"] == [x.strip() for x in lines.split(",")]
    library = {line.id for line in importers.load_library()}
    assert all(line in library for p in prompts for line in p["lines"])


def test_stages_and_seats_follow_b5():
    assert [s["name"] for s in STAGES] == ["Opening", "Independent assessment review", "SWIFT rounds",
                                           "Emerging risk session", "Multivoting", "Gap review"]
    assert [s["role"] for s in SEATS][:6] == ["Business owner", "Data science lead or model owner",
                                              "Security", "Data protection officer", "Overseer",
                                              "Sceptic"]


def test_ranking_counts_voters_before_votes_and_never_averages():
    votes = {"Ann": {"MOD-05": 1, "HUM-01": 5}, "Bob": {"MOD-05": 1}, "Cy": {"MOD-05": 1}}
    ranked = ranking(votes)
    assert [r["id"] for r in ranked] == ["MOD-05", "HUM-01"]
    assert ranked[0] == {"id": "MOD-05", "voters": 3, "votes": 3,
                         "by_participant": {"Ann": 1, "Bob": 1, "Cy": 1}}
    assert all("average" not in r and "mean" not in r for r in ranked)


def test_candidates_come_from_lists_unknown_prompts_and_emerging_risks():
    workshop = {"pre_lists": {"Ann": ["MOD-05 silent vendor update", "our own worry"],
                              "Bob": ["vendor update MOD-05", "HUM-01"]},
                "swift_answers": {"6": {"status": "not known"}, "1": {"status": "covered"}},
                "emerging_risks": [{"title": "Agents booking travel", "note": ""}]}
    swift = importers.load_swift()
    known = {line.id for line in importers.load_library()}
    found = candidates(workshop, swift, known)
    ids = [c["id"] for c in found]
    assert ids == ["MOD-05", "HUM-01", "E1"]
    assert found[0]["from"] == ["2 pre-workshop lists"]
    assert "SWIFT prompt 6" in found[1]["from"] and "1 pre-workshop list" in found[1]["from"]
    assert found[2]["kind"] == "emerging"


def test_seat_differences_against_the_business_owner():
    seats = [{"role": "Business owner", "person": "Ann"}, {"role": "Overseer", "person": "Ola"},
             {"role": "Security", "person": "Sam"}, {"role": "Sceptic", "person": "Sid"}]
    votes = {"Ann": {"MOD-05": 3}, "Ola": {"HUM-01": 2}, "Sam": {"MOD-05": 1}, "Sid": {"HUM-01": 4}}
    diffs = seat_differences(votes, seats)
    assert {"candidate": "HUM-01", "seat": "Overseer", "person": "Ola", "votes": 2,
            "owner_votes": 0} in diffs
    assert {"candidate": "MOD-05", "seat": "Overseer", "person": "Ola", "votes": 0,
            "owner_votes": 3} in diffs
    assert not any(d["seat"] == "Sceptic" for d in diffs)      # the owner is compared with three seats
    assert not any(d["seat"] == "Security" and d["candidate"] == "MOD-05" for d in diffs)


def test_answer_votes_and_list_checks():
    assert check_answer("covered", "version pinning", "release checklist RC-12") == []
    assert check_answer("covered", "", "") == [
        "Covered needs the control and its evidence (B.4)."]
    assert check_answer("not known", "", "") == []
    assert check_answer("maybe", "", "") == ["Record the answer as covered or not known (B.4)."]
    assert check_votes({"MOD-05": 3, "HUM-01": 2}, 5, {"MOD-05", "HUM-01"}) == []
    assert check_votes({"MOD-05": 6}, 5, {"MOD-05"}) == ["6 votes placed; the allowance is 5."]
    assert check_votes({"XYZ-01": 1}, 5, {"MOD-05"}) == ["XYZ-01 is not a candidate."]
    assert pre_list_items("a\n\n b \n") == (["a", "b"], [])
    assert pre_list_items("\n".join(str(i) for i in range(11)))[1] == [
        "A pre-workshop list holds ten risks at most."]
