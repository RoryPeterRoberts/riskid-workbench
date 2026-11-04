"""Round 5: proposing library lines for a system (PLAN.md round 5; chapter 5, the straw man).

The plan's check: proposals for the fixture credit-scoring system include
FAI-04, HUM-01, TRA-02 and LEG-07 with reasons. Also chapter 5's own worked
example (a deployer that buys a chatbot drops SEC-03, keeps SEC-02 and brings
DAT-04), the reasons for every removed line, the regulatory-hook parser over
all 91 lines, and adoption into a candidate register line.
"""

from riskid import importers
from riskid.model import System
from riskid.propose import (annex_a_refs, engaged_hooks, line_hooks, propose_lines,
                            register_line_from_library, screen_lines)

LIBRARY = {line.id: line for line in importers.load_library()}

CREDIT = System(id="SYS-001", name="Credit-scoring model", vendor_or_built="bought and configured",
                role_under_act="deployer", article_6_outcome="high-risk: Annex III",
                lifecycle_stage="operation and monitoring")
CHATBOT = System(id="SYS-002", name="Customer-service chatbot", vendor_or_built="bought",
                 role_under_act="deployer", article_6_outcome="no further class",
                 article_50_duty="yes", lifecycle_stage="operation and monitoring")


def _ids(pairs):
    return [line.id for line, _ in pairs]


def _reasons(pairs, line_id):
    return dict((line.id, reasons) for line, reasons in pairs)[line_id]


def test_credit_scoring_proposals_include_the_plans_four_lines_with_reasons():
    proposed = propose_lines(CREDIT)
    for line_id in ("FAI-04", "HUM-01", "TRA-02", "LEG-07"):
        assert line_id in _ids(proposed), line_id
        assert _reasons(proposed, line_id), line_id
    # LEG-07 covers inception and deployment only: it comes in on the articles
    # the system's classification and configuration engage.
    leg07 = " ".join(_reasons(proposed, "LEG-07"))
    assert "AI Act Art 6" in leg07 and "AI Act Art 25" in leg07
    assert "stage" not in leg07


def test_chapter_5_worked_example_for_a_bought_chatbot():
    proposed, removed = screen_lines(CHATBOT)
    assert "SEC-02" in _ids(proposed)
    assert "SEC-03" in _ids(removed)
    assert "a provider's concern" in " ".join(_reasons(removed, "SEC-03"))
    assert "DAT-04" in _ids(proposed)            # "A bought model brings DAT-04"
    assert "bought" in " ".join(_reasons(proposed, "DAT-04"))


def test_every_line_is_either_proposed_or_removed_with_a_reason():
    proposed, removed = screen_lines(CREDIT)
    assert len(proposed) + len(removed) == 91
    assert set(_ids(proposed)).isdisjoint(_ids(removed))
    assert all(reasons for _, reasons in proposed + removed)


def test_a_provider_drops_deployer_lines():
    provider = System(role_under_act="provider", article_6_outcome="high-risk: Annex III",
                      lifecycle_stage="operation and monitoring")
    proposed, removed = screen_lines(provider)
    assert "HUM-01" in _ids(removed)                       # a deployer's line
    assert "a deployer's concern" in " ".join(_reasons(removed, "HUM-01"))
    assert "SEC-03" in _ids(proposed)                      # a provider's line


def test_unrecorded_stage_and_role_remove_nothing_on_those_grounds():
    proposed, removed = screen_lines(System(article_6_outcome="no further class"))
    assert removed == []
    assert len(proposed) == 91


def test_stage_mismatch_without_an_engaged_article_is_removed_with_its_reason():
    retiring = System(role_under_act="deployer", article_6_outcome="no further class",
                      vendor_or_built="built", lifecycle_stage="retirement")
    proposed, removed = screen_lines(retiring)
    assert "HUM-01" in _ids(removed)
    reason = " ".join(_reasons(removed, "HUM-01"))
    assert "operation and monitoring" in reason and "retirement" in reason


def test_personal_data_engages_gdpr_lines():
    with_data = System(role_under_act="deployer", article_6_outcome="no further class",
                       lifecycle_stage="retirement", data={"personal": True})
    without = System(role_under_act="deployer", article_6_outcome="no further class",
                     lifecycle_stage="retirement")
    assert "LEG-05" in _ids(propose_lines(with_data))     # cites GDPR Art 32
    assert "LEG-05" not in _ids(propose_lines(without))
    assert "personal data" in " ".join(_reasons(propose_lines(with_data), "LEG-05"))


def test_engaged_hooks_follow_classification_and_role():
    hooks = engaged_hooks(CREDIT)
    assert ("AI Act", 26) in hooks and ("AI Act", 86) in hooks     # deployer, high-risk
    assert ("AI Act", 9) not in hooks                               # a provider's duty
    assert ("AI Act", 50) in engaged_hooks(CHATBOT)
    assert ("AI Act", 26) not in engaged_hooks(CHATBOT)            # not high-risk
    assert engaged_hooks(System(article_6_outcome="out of scope")) == {}


def test_line_hooks_parse_every_reg_column():
    cites_ai_act = [line for line in LIBRARY.values() if "AI Act" in line.reg]
    assert len(cites_ai_act) == 68                     # SPEC.md section 3
    assert all(any(i == "AI Act" for i, _ in line_hooks(line)) for line in cites_ai_act)
    assert line_hooks(LIBRARY["LEG-07"]) == {("AI Act", 6), ("AI Act", 25), ("AI Act", 49),
                                            ("AI Act", 99)}
    assert line_hooks(LIBRARY["DAT-04"]) == {("AI Act", 13), ("AI Act", 25), ("AI Act", 53)}
    assert line_hooks(LIBRARY["OPS-07"]) == {("AI Act", 4), ("AI Act", 26), ("GDPR", 30)}


def test_register_line_from_library_keeps_the_id_and_is_a_candidate():
    line = LIBRARY["HUM-01"]
    reg = register_line_from_library(line, "SYS-001")
    assert (reg.id, reg.system_id, reg.source, reg.status) == ("HUM-01", "SYS-001", "library",
                                                               "candidate")
    assert (reg.l1, reg.l2, reg.role) == (line.l1, line.l2, line.role)
    assert reg.definition == line.description
    assert reg.lifecycle_stages == ["operation and monitoring"]
    assert reg.annex_a_controls == ["A.9.3"]
    assert reg.owner is None                 # a named person, chosen later; never a role


def test_annex_a_refs():
    assert annex_a_refs("Classification record per system (Art 6(4)); legal review at "
                        "inception (A.6.2.2); change triggers (6.3)") == ["A.6.2.2"]
    assert annex_a_refs("") == []
