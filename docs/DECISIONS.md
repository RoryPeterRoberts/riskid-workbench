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
