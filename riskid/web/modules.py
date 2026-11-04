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
}

# The modules in the navigation bar, in the method's order.
NAV = tuple(MODULES.values())
