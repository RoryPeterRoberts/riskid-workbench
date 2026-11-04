"""The B.9 contract clause checklist read against the register (SPEC.md 6.12; chapter 12).

Each of the 17 clauses names the register lines it answers. A clause is a gap
for a system when it is not recorded as present and one of its lines is live on
that system; for "Any line" (clause 5), when the system has any live line.
Chapter 12: "the register gives procurement a measure to report: the share of AI
contracts that meet the clause standard"; here, a recorded contract with no gap.
"""

from __future__ import annotations

STATUSES = ("present", "partial", "absent")


def needs_contract(system: dict) -> bool:
    """A system bought from a supplier, or built on a model provider's model."""
    return system.get("vendor_or_built") in ("bought", "bought and configured") or bool(system.get("model_provider"))


def live_lines(state: dict, system_id: str) -> list:
    return sorted(i for i, line in state.get("register", {}).items()
                  if line.get("system_id") == system_id and line.get("status") != "retired")


def gaps(contract: dict | None, live: list, clauses: list) -> list:
    """``[(clause, status, lines)]``: the clauses not present whose lines are live on the system."""
    recorded = (contract or {}).get("clauses") or {}
    out = []
    for clause in clauses:
        lines = list(live) if clause["any_line"] else [i for i in clause["lines"] if i in live]
        status = recorded.get(str(clause["n"])) or "not reviewed"
        if lines and status != "present":
            out.append((clause, status, lines))
    return out


def meets_standard(contract: dict | None, live: list, clauses: list) -> bool:
    return contract is not None and not gaps(contract, live, clauses)
