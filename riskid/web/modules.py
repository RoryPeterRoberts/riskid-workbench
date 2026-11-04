"""The header and "why" panel of each module screen (SPEC.md section 6, the Teach module).

Every screen names the chapter and template it implements and quotes the
chapter's rule in one sentence, with the chapter's opening case beside it.
Later rounds add their module here as they add its screens.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Module:
    key: str
    title: str
    path: str
    chapter: int
    chapter_title: str
    template: str
    why: str            # the chapter's rule, one sentence, in the book's words
    case: str           # the chapter's opening case, one line


MODULES = {
    "inventory": Module(
        key="inventory",
        title="Inventory",
        path="/inventory",
        chapter=5,
        chapter_title="Setting the Context: Inventory, Roles, Classification and the Starting Universe",
        template="B.1 AI System Inventory Fields",
        why="You cannot identify the risks of a system you have not listed.",
        case=("The Tool Nobody Had Listed: in April 2023 engineers at Samsung pasted "
              "confidential source code into ChatGPT, a tool nobody had assessed "
              "(LEG-05, OPS-07)."),
    ),
    "library": Module(
        key="library",
        title="Library",
        path="/library",
        chapter=4,
        chapter_title="The AI Risk Taxonomy",
        template="Appendix A register (91 lines) and the 42-line taxonomy",
        why=("It is the starting universe for Phase 1 (Chapter 5): the straw man you cut "
             "down for one system and add to."),
        case=("SyRI and the Risk That Had No Name: in February 2020 the District Court of "
              "The Hague held that the law behind a Dutch welfare-fraud system breached "
              "Article 8 ECHR; its risks had not been set out in any form the court could "
              "test (FAI-03)."),
    ),
    "usecases": Module(
        key="usecases",
        title="Use cases",
        path="/usecases",
        chapter=7,
        chapter_title="Bottom-Up Identification: The AI Use-Case Template and the Specialist Sub-Processes",
        template="B.2 The AI Use-Case Template",
        why=("Three fields decide whether a submission contains identification or only "
             "classification: the drivers, the controls and the data quality rating."),
        case=("The Model That Passed Its Own Test: in 2021 Michigan Medicine ran a widely "
              "deployed sepsis model on its own patients and found it missed about two-thirds "
              "of cases while alerting on about 18% of patients (MOD-02, MOD-08)."),
    ),
    "workshop": Module(
        key="workshop",
        title="Workshop",
        path="/workshops",
        chapter=6,
        chapter_title="Top-Down Identification: Workshops, SWIFT, Scenarios, Delphi and Red Teams",
        template="B.4 SWIFT prompt set and B.5 workshop agenda",
        why=("A room of senior people asked for the key risks tends to produce the risks "
             "already on the register."),
        case=("The Model That Priced the Market: in November 2021 Zillow shut down Zillow "
              "Offers, whose algorithm set the prices it paid for homes; the model had not "
              "kept pace with the market (MOD-06, SOC-06)."),
    ),
    "reconcile": Module(
        key="reconcile",
        title="Reconcile",
        path="/reconcile",
        chapter=8,
        chapter_title="Reconciliation and the Enterprise AI Portfolio View",
        template="The five steps of reconciliation and the disagreement log",
        why=("If a regulator or auditor asks how the register came to hold what it holds, "
             "the record is the answer."),
        case=("The Fraud That Nobody Owned: in early 2024 an Arup employee in Hong Kong "
              "transferred about US$25 million after a video call with deepfakes of colleagues; "
              "each function's answer on who owned the risk stopped at its own edge (SOC-02)."),
    ),
    "assess": Module(
        key="assess",
        title="Assess",
        path="/assess",
        chapter=9,
        chapter_title="Assessment: Four-Dimensional Scoring, Harm to Individuals and Data Quality",
        template="B.6 The Seven-Field Assessment Record",
        why=("A control that has not been tested reduces nothing, and until it passes a test "
             "the residual stays at the inherent score."),
        case=("The Algorithm Behind the A-Level Grades: in August 2020 Ofqual's standardisation "
              "model lowered about 39% of teacher-assessed grades in England; it was measured on "
              "the cohort, and the harm fell on individual students."),
    ),
    "interact": Module(
        key="interact",
        title="Interact",
        path="/interact",
        chapter=10,
        chapter_title="Risk Interaction: Bow-Ties, Cascades and Concentration",
        template="The interaction matrix, the bow-tie and concentration analysis",
        why=("The impact of a propagation node should reflect what it sets off as well as what "
             "it does alone, and the likelihood of a vulnerable node should reflect every route "
             "into it."),
        case=("Knight Capital and Cruise: in August 2012 a trading release lost Knight Capital "
              "about $440 million in 45 minutes; one Cruise robotaxi accident in October 2023 "
              "ended in the wind-down of the business in December 2024."),
    ),
}

# The modules in the navigation bar, in the method's order.
NAV = tuple(MODULES[k] for k in ("inventory", "library", "workshop", "usecases", "reconcile", "assess", "interact"))
