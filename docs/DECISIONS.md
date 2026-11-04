# DECISIONS

Decision log for the RiskID Workbench build. One line per decision. Any
dependency added outside `PLAN.md` section 2 needs a line here (rule 10 of
`PLAN.md` section 1); any deviation from `SPEC.md` needs a line and a question.

- round 0: use the `PLAN.md` section 2 dependency set exactly (fastapi,
  uvicorn, jinja2, python-multipart, openpyxl, matplotlib, weasyprint,
  python-docx, pytest, httpx). All are named in `PLAN.md` section 2, so this
  adds no new dependency.
- round 0: the root route returns JSON `{"title": "RiskID Workbench"}`; the
  title is `RiskID Workbench`, matching the `FastAPI` app title.
- round 1: added `[tool.setuptools.package-data] riskid = ["data/*"]` to
  `pyproject.toml` so the data packs introduced this round ship with a
  non-editable (pipx) install. No new runtime dependency; the build backend
  (setuptools) was already in use.
- round 1: the book's incident indicator names `Any line` (not a specific
  register line). It is encoded as `any_line: true` with an empty `lines`
  list in `riskid/data/indicators.json`; `load_indicators()` and the
  test treat it as applying to every line, so the "every indicator names a
  register line" check is a data-integrity check on the 8 line-specific
  presets, not a special case that forces a pass.
- round 2: the golden file `tests/reference/golden_register.json` is
  generated from the book's reference scoring script
  `~/RiskID_Har…/build_register.py` (imported in a throwaway Python 3.12
  environment and called, never run as a script; PyYAML is needed at import
  time there and is not added to the project). Only the golden file is
  committed, not the reference script or its private paths. 2026-11-03.
- round 2: `pilot_overdue` flags a system when it has a `pilot_end_date` that
  today is after and its `lifecycle_stage` is still before deployment — one
  of inception, design and development, verification and validation. The
  seven lifecycle stage names live in one constant, `LIFECYCLE_STAGES`.
  Moving a system to deployment or later is the gate decision, so a pilot
  that was risk-assessed but is still before deployment is still flagged.
  2026-11-03.
- round 3: the fixture organisation is not committed. `tests/fixtures/`
  ignores `*.riskid` (see `.gitignore`), so the tests build the fixture in a
  temporary directory through a shared `fixture_org` fixture in
  `tests/conftest.py`; `tests/fixtures/make_org.py` exposes
  `build_org(path)` and, run as a script, writes `tests/fixtures/org.riskid`
  for manual use only. Later rounds reuse the same `fixture_org` fixture
  instead of re-deriving the organisation. 2026-11-03.
- round 3: the CV-screening tool in the fixture is deliberately overdue under
  the round 2 `pilot_overdue` rule: it carries a fixed `pilot_end_date`
  (2026-06-30) that has passed and a `lifecycle_stage` of
  `verification and validation`, still before deployment. The credit-scoring
  model and the chatbot sit at `operation and monitoring` with no
  `pilot_end_date`, so neither is flagged. 2026-11-03.
- round 4: `riskid/web/static/htmx.min.js` is htmx.org 2.0.11 `dist/htmx.min.js`
  (52,182 bytes, sha256 `d6fdc75f204e6bdefa99b69bf1e6d4ac69b8a364f77929f45c13476b4000f717`),
  taken from the npm registry tarball after checking its sha512 against the
  registry's published integrity. Licence 0BSD. A test pins the hash. HTMX is
  named in `PLAN.md` round 4, so this adds no dependency. 2026-11-03.
- round 4: the Inventory form also refuses a save without a name, besides the
  owner, role and Article 6 outcome that SPEC.md section 3 requires: a system
  with no name cannot be listed once. 2026-11-03.
- round 4: the Article 6 outcome is one of six values, one per end of chapter
  5's classification steps: out of scope, prohibited, high-risk: Annex I,
  high-risk: Annex III, not high-risk: Article 6(3), no further class. The
  fixture's three systems now carry one each (credit scoring and CV screening
  high-risk: Annex III; the chatbot no further class, with its Article 50
  duty). 2026-11-03.
- round 4: SPEC.md 6.2 asks for the discovery ratio per quarter but section 4
  has no entity for it. The store gains a `discovery` entity (quarter, tools
  found, tools inventoried, methods), recorded as events like everything
  else. 2026-11-03.
- round 4: until Settings brings the list of people (round 14), the person
  recorded on each change is `RISKID_ACTOR` if set, else the operating-system
  account (`riskid/config.py`). 2026-11-03.
- round 4: two guards keep the workbench local (SPEC.md section 10): the Host
  header must be loopback (or the host given to `riskid serve --host`), which
  stops DNS rebinding, and a change whose Origin header names another site is
  refused with 403. 2026-11-03.
- round 4: the web routes are `async`, as is the store dependency, so each
  request opens, uses and closes its SQLite connection on one thread.
  2026-11-03.
- round 4: the root route still returns the title as JSON (the round 0 test).
  The Dashboard of SPEC.md 6.1 has no round in `PLAN.md`; until it has one,
  the header's product name links to the Inventory. 2026-11-03.
- round 4: the timestamp helpers moved from `riskid/store.py` to
  `riskid/timestamps.py`, unchanged, because the round 3 fix took store.py to
  408 lines, over rule 5's limit of 400. 2026-11-03.
- round 5: `riskid/propose.py` sorts the library for a system into proposed and
  removed lines, each with its reasons (chapter 5: filter by role, lifecycle
  stage, persons affected and classification; record the reason for every
  line removed). A provider's line is removed for a pure deployer and a
  deployer's for a pure provider. A line is proposed when its stages include
  the system's stage, or when it cites an article the system engages: the
  Act's Articles 4 and 6 for any classified system; Article 5 if prohibited;
  Articles 9 to 17, 43, 47 to 49, 72 and 73 for a provider of a high-risk
  system and 13, 14, 26, 27, 73 and 86 for its deployer; 6 and 49 for the
  Article 6(3) exception; 25 when the system is bought and configured or the
  role is both; 13, 25 and 53 when it is bought; 50 when an Article 50 duty
  is recorded; the GDPR when personal data is recorded. An unrecorded role,
  stage or list of persons removes nothing: unknown is not none. 2026-11-04.
- round 5: a register ID is used once in an organisation, so adopting a
  library line already in the register is refused, whichever system it was
  adopted for (SPEC.md section 4: one `system_id` per register line).
  2026-11-04.
- round 5: an adopted line is a candidate with `source` library and `trend`
  new; its owner stays empty because B.3 asks for a named person and the
  library holds a role; its Annex A references are read from the line's
  controls text (81 of the 91 lines cite one). 2026-11-04.
- round 5: a line the filter removed can still be adopted ("Adopt anyway");
  the event's reason then records the filter's reason it overrode.
  2026-11-04.
- round 6: `Store.transaction()` keeps several events together: all are
  committed or none. The pack load uses it, so `riskid init` is atomic (and a
  failed init removes the empty file it created), as do an inventory edit's
  field events and a use case's acceptance with its register line.
  2026-11-04.
- round 6: `UseCase` gains `source` (the general template or one of the ten
  specialist sub-processes; chapter 7: every risk carries its source) and
  `line_id` (the register line it created or supports). 2026-11-04.
- round 6: a use case is returned for the three checks of SPEC.md 5.5
  (`rules.check_use_case`) and for an incomplete template: no Level 2
  taxonomy code, no definition, no named owner, no data quality rating, a
  control row with no name, an unknown type or an unreadable test date, an
  unknown risk ID, or a taxonomy code that differs from the line named in
  field 1. Chapter 7: a submission that classifies in its own categories is
  sent back. 2026-11-04.
- round 6: every submission is recorded. A returned one keeps its reasons
  (one per line) and is corrected and resubmitted on the same UC-nnn record;
  an accepted one is not resubmitted (409). 2026-11-04.
- round 6: an accepted use case becomes a candidate line with source
  bottom-up: a new ORG-nnn, or the library ID named in field 1. A risk already
  in the register is supported by the use case (`line_id`) and not entered
  twice. 2026-11-04.
- round 7: `riskid/data/swift.json` is generated from the B.4 table in
  `docs/BOOK_TABLES.md`, not retyped; a test compares the two prompt by prompt
  and checks every named line is in the library. 2026-11-04.
- round 7: `Workshop` gains `stage` (1 to 6, B.5), `status` (open | closed)
  and `vote_allowance` (chapter 6: five to ten votes each; 1 to 20 accepted).
  2026-11-04.
- round 7: a workshop moves forward through the six stages and each stage
  opens its input: pre-workshop lists at stage 1 only, SWIFT answers from
  stage 3, emerging risks from stage 4, votes at stage 5 only, the gap review
  at stage 6. A closed workshop takes no further change. 2026-11-04.
- round 7: the pre-workshop lists are hidden everywhere until stage 2 (the
  facilitator view, the record, the participant view), then shown as List A,
  List B and so on, in an order set by their content rather than by who sent
  them first. 2026-11-04.
- round 7: the candidates for multivoting are the register lines named in
  the lists, the lines of the prompts answered "not known", and the emerging
  risks. They are ranked by how many participants voted for them, then by
  votes placed (chapter 6); each participant's votes are kept and nothing is
  averaged. Where the overseer, the DPO or security put votes on a candidate
  and the business owner did not, or the reverse, the record lists it for the
  disagreement log. 2026-11-04.
- round 7: closing the workshop makes each voted library line not yet in the
  register a candidate line with source top-down, for the first system in
  scope that the line was proposed for (else the first system); a line
  already in the register is left as it is; emerging risks stay in the
  workshop's taxonomy gap list. Attendance is set when the workshop opens and
  taken at stage 1; absent seats do not write lists or vote. 2026-11-04.
- round 8: three new entities: `disagreement` (DL-nnn, the disagreement log
  the plan asks for; SPEC.md section 4 carries a disagreement only inside an
  assessment), `resolution` (one per gap or disagreement, keyed by its
  subject) and `reconciliation` (RC-nnn, a signed pass). 2026-11-04.
- round 8: top-down entries are the lines a closed workshop voted for and any
  top-down register line; bottom-up entries are the accepted use cases. They
  match on the Level 2 node and the system (chapter 8, step 1). A gap is what
  is unmatched in either direction, or a line adopted from the library that
  neither track raised. A blind spot is a line proposed for a system that is
  not in the register; each needs a recorded reason (chapter 8). 2026-11-04.
- round 8: every gap and disagreement gets one of chapter 8's five
  dispositions, with a reason (required), the person and the date. On the
  register: add makes the line active (adopting a blind spot first, for the
  first system it was proposed for), merge retires it into the line named,
  escalate and local make it active, not applicable retires it. For a blind
  spot the other dispositions record the decision only. A candidate becomes
  active here. A retired line or a resolved disagreement is not resolved
  again. 2026-11-04.
- round 8: a disagreement records who holds the minority view, the minority
  score (1 to 5), the majority score if known, the dimension (an impact
  dimension, likelihood or control effectiveness) and the evidence. The
  workshops' seat differences are shown as the challenge agenda. 2026-11-04.
- round 9: rule change, with tests: a control test whose result is recorded
  as failed does not unlock the residual. SPEC.md 5.4 says "a test date and a
  result"; chapter 9 says "until it passes a test the residual stays at the
  inherent score", and the method is the book. The test form asks for passed
  or failed. The golden file is unchanged (91/91). 2026-11-04.
- round 9: SPEC.md 5.4's second half is now a rule:
  `rules.residual_basis_cites_test` (a lower residual's data-quality basis
  names a passed control test or gives its date). 2026-11-04.
- round 9: `riskid/data/flags.json` holds the library's rule flags
  (`material_on_impact_alone`: LEG-08, from SPEC.md 5.3), because the register
  file has no column for them; a system classified as a prohibited practice
  makes its lines material. 2026-11-04.
- round 9: each save is a new assessment (AS-nnn) for the line; the latest is
  the current one, and the line's history keeps them all. The data-quality
  basis is required for every rating (B.6 field 4: "with the evidence"). A
  residual above the inherent is refused. A minority view in the record also
  goes to the disagreement log. 2026-11-04.
- round 9: a vulnerability or speed of onset of 5 is shown as "in front of
  the owner this week" (chapter 9), whatever the score. 2026-11-04.
- round 9: the heat maps are drawn by `riskid/documents/heatmap.py` with the
  reference script's drawing (band colours, IDs three to a row, the score in
  the corner), and are also given as a text table for screen readers.
  2026-11-04.
- round 10: `Interaction` gains `mechanism` (required: "a cell with no
  mechanism stays blank", chapter 10) and `delay`, and a fourth kind, none,
  so a judgement of no effect is recorded rather than deleted. A link is one
  entity per ordered pair (`FROM>TO`), re-recorded when the judgement changes;
  the matrix is not symmetric. 2026-11-04.
- round 10: the matrix's axes are the material lines (latest assessment) and
  every line in a live link. Propagation and vulnerable nodes are lines with
  two or more outgoing or incoming links. Candidate links are pairs of live
  lines that cite the same Annex A control and have not been judged.
  2026-11-04.
- round 10: `BowTie` gains `owner` (chapter 10: one owner, the head of the
  process) and `escalation_factors`; causes and preventive controls, and
  consequences and recovery controls, are kept as row-aligned lists.
  2026-11-04.
- round 10: concentration counts systems per model (provider and name), per
  model provider and per supplier, flags one model under several suppliers as
  hidden concentration, and lists the Annex A controls several live lines
  rely on (chapter 10's five forms; the reviewer pool and data-source forms
  wait for those fields). 2026-11-04.
