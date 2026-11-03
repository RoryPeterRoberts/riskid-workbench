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
