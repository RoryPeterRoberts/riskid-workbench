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
