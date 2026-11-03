# RiskID Workbench — build plan for Qwen3.8-27B in the DeepSeek Harness

This file is written for the model that will build the tool. Read it whole once; then work one round at a time. The specification is `SPEC.md` in this folder; its section numbers are cited below. Do not change the specification. If something in it cannot be built as written, record the problem in `docs/DECISIONS.md` and ask.

## 0. Objective (immutable; carry it into every round)

Build `riskid-workbench`, a Python 3.11 local web application that implements the method of *AI Risk Identification: The Complete Methodology* as specified in `SPEC.md`: the data model of §4, the rules of §5, the screens of §6, the documents of §7, under the principles of §1. Version 1 is done when the acceptance test in §11 passes: a practitioner reaches a signed quarterly pack for the fixture organisation without leaving the tool.

## 1. How to work (the execution specification)

These rules come from measurements of this model in November 2026. Follow them exactly.

1. **One round per session.** Each round below names its files, its tests and its done-when. Do the round, run its tests, stop. Write the handoff (§3). Do not start the next round in the same session.
2. **Tests first.** Write the round's tests before its code. The round is done when `pytest tests/ -q` is green and `python -m riskid check tests/fixtures/org.riskid` prints no violations. Nothing else counts as done. Do not decide for yourself that the work is good enough; the tests decide.
3. **Run code, do not trace it in your head.** Whenever you are unsure what a function returns, run it. Use the bash tool early: the first run should happen within the first few hundred tokens of a round, not after a long think.
4. **Reasoning effort medium.** Do not escalate. If a step needs more thought, split it into two smaller steps and run each.
5. **Small files.** No file over 400 lines. If a module grows past that, split it along the entity or document it serves.
6. **The rules are the method.** `riskid/rules.py` implements §5 and nothing else. Every rule has one function and at least one positive and one negative test. Never special-case a test to make it pass.
7. **Never delete data paths.** The store has no delete; retirement is an event. If a test or a route needs deletion, it is wrong; see §5.6 of the spec.
8. **Commit after every green round** with the message `round N: <one line>`. Do not commit red.
9. **Stuck rule.** If a test has failed three times on the same cause, stop, write `BLOCKED.md` with the test name, the error, what you tried, and the smallest question that would unblock you. Do not loop.
10. **No new dependencies** beyond the list in §2 without a line in `docs/DECISIONS.md`.
11. **Scope.** Build what the round says. Features that come to mind go in `docs/LATER.md`, one line each.

## 2. Environment (round 0 sets this up)

```
python3.11 -m venv .venv && . .venv/bin/activate
pip install fastapi uvicorn jinja2 python-multipart openpyxl matplotlib weasyprint python-docx pytest httpx
```

Inputs that already exist and must be copied, not rewritten:
- `~/RiskID_Harness/04_ai_book/register/risks.tsv` → `riskid/data/register.tsv` (91 lines, 23 columns; §4 LibraryLine)
- `~/RiskID_Harness/04_ai_book/taxonomy/taxonomy.tsv` → `riskid/data/taxonomy.tsv` (42 lines, 5 columns)
- `~/RiskID_Harness/04_ai_book/register/build_register.py` → `tests/reference/build_register.py` (the reference scoring; read it, do not import it into the app)
- Chapter 13's indicator table and chapter 9's scales → `riskid/data/indicators.json`, `riskid/data/scales.json` (typed in round 1 from `SPEC.md` §5 and the tables in `docs/BOOK_TABLES.md`, which the plan's author provides)

## 3. The handoff (write it at the end of every round, under 200 words)

```
ROUND N DONE
Files: <list>
Tests: <count passing> / <count>, command used
Rules touched: <none | list>
Open: <anything the next round must know>
Next: round N+1
```

## 4. Rounds

### Round 0 — scaffold
Files: `pyproject.toml`, `riskid/__init__.py`, `riskid/cli.py` (init, serve, check as stubs that print their name), `riskid/app.py` (FastAPI app with `/` returning "RiskID Workbench"), `tests/test_smoke.py`, `docs/DECISIONS.md`, `docs/LATER.md`, `.gitignore`, `README.md` (two paragraphs from SPEC §1).
Tests: `test_smoke.py`: importing `riskid` works; `GET /` returns 200 with the title; `riskid --help` lists the three commands.
Done when: tests green; `git init` done; first commit.

### Round 1 — data packs and model
Files: `riskid/data/register.tsv`, `taxonomy.tsv`, `scales.json`, `indicators.json`, `VERSION`; `riskid/model.py` (dataclasses for every entity in SPEC §4, with `to_dict`/`from_dict`); `riskid/importers.py` (`load_library()`, `load_taxonomy()`, `load_scales()`, `load_indicators()`).
Tests: `test_importers.py`: 91 library lines with the 23 columns; 42 taxonomy lines; every library line's l1/l2 exists in the taxonomy; scales have five levels on five dimensions plus likelihood, vulnerability, speed, data quality; every indicator names at least one register line that exists.
Done when: green.

### Round 2 — the rules
Files: `riskid/rules.py`: `score(L, I)`, `band(score)`, `dominant(impacts) -> (dim, value)`, `needs_reasoning(impacts)`, `material(inherent, I, flags)`, `residual_allowed(line_controls)`, `check_use_case(fields) -> list[reason]`, `next_review(cycle_date, trigger_date)`, `version_mismatch(system)`, `pilot_overdue(system, today)`, `ai_draft_quality(field)`.
Tests: `test_rules_golden.py`: load the 91 library lines, recompute inherent, residual, both bands and materiality, and compare with `tests/reference/build_register.py` run on the same TSV (write the golden file once, commit it). `test_rules.py`: one positive and one negative test per function; the three failing-field checks each with a returned and an accepted example from SPEC §5.5.
Done when: golden matches 91/91; green.

### Round 3 — the store and the audit trail
Files: `riskid/store.py`: `Store(path)` over SQLite; `append(event)`; projections for each entity; `replay(date)`; `retire(line_id, reason, actor)`; no delete; `riskid init` creates the file and loads the packs; `riskid rebuild`.
Also: `tests/fixtures/make_org.py` builds the fixture organisation (three systems: a credit-scoring model bought and configured, deployer, Article 6 high-risk; a customer-service chatbot, deployer, Article 50 duty; a CV-screening tool in pilot past its end date) and saves `tests/fixtures/org.riskid`.
Tests: `test_store.py`: events append and project; a change then `replay(before)` shows the old value; `retire` keeps the line in replay and removes it from the live view; any call that would delete raises; `riskid init` on a temp path yields 91 library lines and 42 taxonomy lines; the fixture builds.
Done when: green.

### Round 4 — the web shell and Inventory (SPEC §6.2, B.1)
Files: `riskid/web/__init__.py`, `routes_inventory.py`, `templates/base.html` (header with the module's chapter and template, the "why" panel), `templates/inventory_list.html`, `inventory_form.html`, `static/style.css` (EON palette: navy #1B2A4A, gold #C5A55A), HTMX from `static/htmx.min.js` (vendored).
Tests: `test_routes_inventory.py` with `httpx`: list renders empty and with the fixture; the form refuses a save without owner, role and Article 6 outcome and shows the reason; a saved system appears in the list with its ID `SYS-001`.
Done when: green; `riskid serve` opens the inventory in a browser.

### Round 5 — Library and adoption (§6.3)
Files: `routes_library.py`, templates; `riskid/propose.py` (`propose_lines(system) -> list[(line, reasons)]` by lifecycle stage, role, data flags and regulatory hooks).
Tests: proposals for the fixture credit-scoring system include FAI-04, HUM-01, TRA-02 and LEG-07 with reasons; adopting a line creates a RegisterLine with the same ID and `source=library`; adopting twice is refused.
Done when: green.

### Round 6 — Use cases (§6.5, B.2)
Files: `routes_usecases.py`, templates with the MOD-05 example as placeholders.
Tests: a submission with driver "model error" is returned with the reason; "human in the loop" with no override figure is returned; Medium data quality without a basis is returned; a complete submission is accepted and creates a candidate line with `source=bottom-up`.
Done when: green.

### Round 7 — Workshop (§6.4, B.4, B.5)
Files: `routes_workshop.py`, templates for the facilitator's six stages and the participant entry; `riskid/data/swift.json` (the 23 prompts with their register lines, typed from `docs/BOOK_TABLES.md`).
Tests: pre-lists are hidden until stage 2; all 23 prompts render with their lines; each answer stores covered/not known with control and evidence; votes are stored per participant and never summed into an average in the record; the workshop record renders as HTML with every stage.
Done when: green.

### Round 8 — Reconcile (§6.6)
Files: `routes_reconcile.py`, templates (five tabs); the disagreement log entity and view.
Tests: a candidate with no matching line shows as a gap; a line with no submission shows as a gap; resolving requires a reason and records who; the disagreement log lists the minority score and the dimension.
Done when: green.

### Round 9 — Assess and the heat map (§6.7, ch 9, B.6)
Files: `routes_assess.py`, templates with the five scales as pickers showing their descriptions; `riskid/documents/heatmap.py` (same drawing as the reference script); the controls table.
Tests: inherent, band and materiality shown match `rules`; residual pickers are locked until a control has a test result; the record view has the seven fields of B.6; the heat map PNG renders for the fixture and places each line in the right cell.
Done when: green.

### Round 10 — Interact (§6.8)
Files: `routes_interact.py`, templates: matrix grid, bow-tie editor (two columns around the event), concentration by vendor and model.
Tests: an interaction is stored with its kind; a bow-tie saves causes, controls and consequences; the concentration view counts systems per vendor and per model.
Done when: green.

### Round 11 — Register, profiles, replay (§6.9, B.3)
Files: `routes_register.py`, templates: the grid with the 14 + 5 columns, the line profile, a date picker that calls `replay`.
Tests: the grid shows the fixture's live lines and not retired ones; a profile shows every assessment and control with dates and actors; replay to a date before a change shows the earlier score.
Done when: green.

### Round 12 — Documents (§7, ch 12, B.7)
Files: `riskid/documents/register.py` (XLSX with the book's column order, CSV, PDF), `fria.py` (per system, six Article 27(1) elements, each with its source fields per B.7), `soa.py` (Annex A references across live lines), `report.py` (Principal AI Risk Report), `routes_documents.py`.
Tests: XLSX columns equal the reference list in `tests/reference/columns.txt`; the FRIA for the credit-scoring system contains all six elements and names HUM-01's override rate under 27(1)(e); the SoA lists exactly the Annex A references on live lines; every document records the data-pack versions and the state hash.
Done when: green.

### Round 13 — Cycle (§6.11, ch 13, B.8)
Files: `routes_cycle.py`, templates: indicator sheet with green/amber/red; trigger log; the 18-step checklist runner with evidence and owner per step; sign-off; `riskid/documents/packs.py` (quarterly pack ZIP, evidence pack ZIP); `riskid/data/calendar.json` (the role-and-date calendar, typed from `docs/BOOK_TABLES.md`).
Tests: an indicator above its red threshold shows red; a trigger lists the lines whose hooks or indicators it touches and opens an event update; step 4 flags a version mismatch in the fixture; sign-off refuses while a step lacks evidence; the quarterly pack ZIP contains the register, the change list and the disagreement log.
Done when: green.

### Round 14 — Contracts, Settings, the assistant, packaging (§6.12–13, §8, §9)
Files: `routes_contracts.py` (B.9), `routes_settings.py`, `riskid/ai/adapter.py` (OpenAI-compatible; off by default; sends only the current screen's fields; logs model, version, tokens), `riskid/ai/prompts.py` (JSON schemas for the five draft kinds in SPEC §8), `pyproject` packaging for `pipx`, a PyInstaller spec, `docs/USER_GUIDE.md` (one page per module, each citing its chapter).
Tests: the assistant is off until an endpoint is set; with a stub endpoint a drafted field carries `ai_draft` and counts as Very Low until accepted; acceptance records the person; the contract checklist shows gaps against lines; `pipx install .` and `riskid serve` work in a clean virtualenv (a shell test).
Done when: green; the acceptance test of SPEC §11 passes end to end on the fixture; tag `v1.0.0`.

## 5. Order and dependencies

Rounds 0 → 1 → 2 → 3 are strictly sequential. Rounds 4 to 11 depend on 3 and may be done in any order after it, but keep the numbering unless told otherwise. Round 12 needs 9 and 11. Round 13 needs 12. Round 14 is last.

## 6. What the plan's author owes the builder before round 1

`docs/BOOK_TABLES.md`: the chapter 9 scales, the chapter 13 cycle and indicator tables, the B.4 prompt set, the B.8 checklist and the B.9 clauses, copied from the book verbatim so the builder types nothing from memory. (Provided alongside this plan.)
