# AGENTS.md — how to work in this repository

Read `docs/PLAN.md` first; its section 1 is the execution specification and binds every agent here. The objective is in its section 0 and the specification is `docs/SPEC.md`. Do not change the specification.

Summary of the rules that matter most:
- One round per ticket. A ticket names its round; do that round only. Write the handoff in the form of PLAN.md §3 in your final report.
- Tests first. A round is done when `pytest tests/ -q` is green and `python -m riskid check tests/fixtures/org.riskid` prints no violations (once those exist). Run code; do not reason about what it would print.
- Reasoning effort stays at the profile's default. Split a hard step in two rather than thinking longer.
- No file over 400 lines. No new dependencies beyond PLAN.md §2 without a line in `docs/DECISIONS.md`.
- `riskid/rules.py` is the method: one function per rule, a positive and a negative test each, never special-cased.
- Nothing deletes data; retirement is an event.
- Commit only green, with the message `round N: <one line>`, as the author the delivery requirements name. Open a pull request for the round; a person reviews and merges.
- Stuck rule: after three failures on one cause, write `BLOCKED.md` (test, error, what was tried, the smallest unblocking question) and stop.

Environment: Python 3.11, `python3.11 -m venv .venv && . .venv/bin/activate`, then the pip line in PLAN.md §2. The book's data files to copy are listed there; they live outside this repository on the operator's machine and the ticket's instructions will say where.
