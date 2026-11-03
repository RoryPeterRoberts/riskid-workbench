# RiskID Workbench — design specification

<p class="sub">An open-source, downloadable workbench for practitioners using <em>AI Risk Identification: The Complete Methodology</em>. Specification v1, 3 November 2026. Author: Sapien for EON Risk Services.</p>

## 1. Purpose, reader and scope

**Purpose.** The book gives a practitioner a method in six phases and nine templates for producing an AI risk register that stands up to ISO/IEC 42001 clause 6.1.2 and Article 9 of the EU AI Act. Readers then do the work in spreadsheets, and the spreadsheets drift: fields are skipped, scores are typed without their basis, residual scores are lowered without a test, lines are deleted rather than retired, and the record cannot be reconstructed when an auditor or a supervisor asks for it (chapter 11, the Post Office case). The Workbench is the method as software: every form is one of the book's templates, every rule in chapter 9 and chapter 11 is enforced by the program, and one record produces every document the method calls for.

**Reader.** The practitioner who has to produce the evidence: the risk or compliance lead, the DPO, the AI officer, the consultant. One person, or a small team sharing a file. Not the board (they receive the report), not the data scientist (they fill in the use-case template when asked).

**In scope.** Phases 1 to 6 of the method, the integration outputs of chapter 12, the cycle of chapter 13, the contract checklist of Appendix B.9, and the regulatory hooks of chapter 15 as data. **Out of scope** for version 1: multi-user concurrency, cloud hosting, the continuous watch of the Harness service (chapter 14; it feeds this tool, it is not this tool), model monitoring or evaluation harnesses, and any automated scoring.

**Non-negotiable principles**, from chapter 14 and the November 2026 measurements of the local model:
1. The software is never the owner or the scorer of record. Every score, rating and acceptance carries a named person and a date.
2. Nothing is deleted. Lines are retired with a reason; every change is an event in an audit trail that can replay the register as it stood on any date.
3. A residual score equals the inherent score until a tested control supports a lower one (chapter 11, field 8).
4. Any text an AI assistant drafts is marked as a draft, with the model and version logged, until a person accepts it (chapter 14; template B.6 field 6).
5. The practitioner's data never leaves the machine unless they export it.

## 2. How the book maps onto the tool

| Phase | Book | Module | Templates it embodies |
|---|---|---|---|
| 1 Context | Ch 5 | **Inventory** | B.1 (18 fields), Article 5 screen, Article 6 classification, risk criteria, interested parties |
| 2 Identification, top-down | Ch 6 | **Workshop** | B.4 (23 SWIFT prompts), B.5 (agenda and seats), multivoting, emerging-risk session, Delphi rounds |
| 2 Identification, bottom-up | Ch 7 | **Use cases** | B.2 (5 headers, 11 fields), the three failing-field checks, the ten specialist sub-processes as a checklist |
| 3 Reconciliation | Ch 8 | **Reconcile** | the five steps, the disagreement log, the portfolio view |
| 4 Assessment | Ch 9 | **Assess** | the five impact scales, likelihood, vulnerability, speed, data quality, B.6 (seven-field record), heat map |
| 5 Interaction | Ch 10 | **Interact** | interaction matrix, bow-tie, concentration, cascades |
| 6 Documentation | Ch 11 | **Register** | B.3 (14 fields + 5 AI columns), risk profiles, audit trail, governance |
| Integration | Ch 12 | **Documents** | B.7 (FRIA mapping), Statement of Applicability, DPIA cross-reference, serious-incident clock, Principal AI Risk Report |
| The cycle | Ch 13 | **Cycle** | monthly indicators (the chapter 13 table as presets), trigger log, B.8 (18-step quarterly checklist), annual re-baseline, audit and management review |
| Contracts | B.9 | **Contracts** | 17 clauses per vendor system, gaps shown against register lines |
| Rules | Ch 15 | **Hooks** | regulatory hooks per line; the role-and-date calendar as an updatable data pack |
| Lessons | Ch 16 | **Teach** | every screen cites its chapter and shows its opening case; the case library is browsable by taxonomy line |
| Library | App A, Ch 4 | **Library** | the 91-line register and the 43-line taxonomy, preloaded and versioned |

## 3. User journeys

**Day one.** Install; create an organisation file; the Library is already there. Add the first system with the 18 fields (the form will not save without an owner, a role and a classification outcome). Choose "start from the library": the tool proposes the register lines that match the system's lifecycle stage, role and data (the same lookup the Harness uses: 68 of the 91 lines cite an AI Act article). Adopt lines; each keeps its register ID. End of day one: an inventory, a candidate list, nothing scored.

**A workshop.** Open Workshop for a system. Participants' pre-workshop top-ten lists are entered blind (the tool hides them until stage 2). Stage 3 walks the 23 SWIFT prompts; each answer is recorded as covered (with the control and its evidence) or not known. Stage 5 records multivotes per person; dissent is kept, not averaged. The output is the workshop record and a set of candidate lines marked "top-down".

**A use-case submission.** The system operator completes B.2 for a risk. The three failing fields are checked on save: a driver that reads only "model error" is returned; a control called "human in the loop" with no override figure is returned; a data quality rating of Medium needs its basis stated. Submissions are marked "bottom-up".

**Reconciliation.** The five steps on one screen: match top-down and bottom-up candidates to lines; show gaps (a line with no submission, a submission with no line); challenge (the sceptic's remit); resolve with a reason; record. The disagreement log is written here.

**Assessment.** For each line: the harm scored and its unit of exposure; impact chosen on each of the five dimensions with the chapter 9 descriptions beside the picker; the tool names the dominant dimension and asks for the reasoning when harm to individuals is not dominant but scored 4 or 5; likelihood on the twelve-month horizon; vulnerability; speed of onset; data quality with its basis. Inherent = L × I, banded; material if inherent ≥ 15 or impact = 5, and the rules above the score (LEG-08 material on impact alone) apply. Controls are listed by type with their last test date and result; the residual picker stays locked at the inherent values until at least one control has a test result. The heat map updates as you go.

**Quarter-end.** Open the Cycle. The 18-step checklist runs with an evidence field per step and an owner; the version check compares each material system's assessed version against its running version; the indicator sheet shows green, amber and red against thresholds; the trigger log shows every event since last quarter and whether it was processed; the focused workshop uses the change prompts only. Sign-off by the accountable executive dates the register and fixes the next run. Export the quarterly pack.

**The auditor's question.** "Show me the register as it stood on 30 June, and why MOD-05 was re-scored in August." The audit trail replays the register to the date; the line profile shows the change, the person, the reason and the evidence.

**A vendor change notice.** Log a trigger (source, date, text). The tool lists the lines whose indicators or hooks it touches (MOD-05, OPS-05) and opens an event-driven update for each, with the significance decision recorded. The Harness service, where subscribed, posts these triggers into the log automatically; without it, the practitioner types them.

## 4. Data model

One SQLite file per organisation (`<org>.riskid`), with an event table that is the source of truth and tables that are projections of it.

**Entities and their fields.**

- **Organisation**: name, sector, jurisdictions, risk criteria (the acceptable-risk statement of chapter 5), accountable executive, AI officer, facilitator.
- **System** (B.1, 18 fields): id (persistent), name, function, components, vendor_or_built, supplier, contract_ref, model_provider, model_name, model_version, version_pinned, last_change_notice, purpose_stated, purpose_in_use, users (role, number), persons_affected (groups, vulnerable flag), data (training sources, production inputs, personal, special category, locations), role_under_act (provider | deployer | both), article_25_check, article_5_screen, article_6_outcome (+ record ref, Article 50 duty), owner, model_owner, data_owner, lifecycle_stage (one of seven), jurisdictions, period_and_frequency, impact_assessments (DPIA, FRIA, 42005: ref, date, next due), last_risk_assessment (date, version), discovery_source (declared | procurement | scan | audit | incident), pilot_end_date, logs (location, retention).
- **TaxonomyLine**: l1_code, l1, l2_code, l2, owner_function (43 rows, versioned with the library).
- **LibraryLine** (Appendix A, 91 rows): the register columns of `risks.tsv`: id, l1, l2, title, description, lifecycle, role, harmed, exposure, event, L, I, dim, V, S, dq, controls, rL, rI, owner (role), kri, reg, sources. Read-only; adopted into RegisterLines.
- **RegisterLine** (B.3, 14 + 5): id (register ID kept on adoption, or ORG-nnn for new lines), system_id, taxonomy (l1, l2), definition, coso_category, owner (person), status (candidate | active | retired), retired_reason, source (top-down | bottom-up | library | event), trend, last_review, next_review, lifecycle_stages, role, persons_affected, regulatory_hooks, annex_a_controls, interaction_summary.
- **Assessment** (B.6): line_id, date, assessor, harm_scored, unit_of_exposure, impact per dimension {FIN, REG, REP, IND, OPS}: 1–5, dominant_dimension (+ reasoning), likelihood 1–5, vulnerability 1–5, speed 1–5, inherent (computed), inherent_band (computed), material (computed + rule), data_quality (High | Medium | Low | Very Low) + basis, residual_L, residual_I (locked until a tested control exists), residual (computed), acceptable (yes | no, by whom), model_vendor_dependency (text; AI-drafted text noted), disagreement (minority score, dimension, evidence).
- **Control**: line_id, name, type (preventive | detective | corrective), owner, last_test_date, last_test_result, evidence_ref, annex_a_ref.
- **Indicator** (KRI): line_id, name, unit, current_value, green/amber/red thresholds, read_by, history (dated values).
- **UseCase** (B.2): system_id, headers 1–5, fields 1–11, submitted_by, date, status (returned | accepted), return_reason.
- **Workshop** (B.5): system_ids, date, facilitator, seats (role, person, present), pre_lists (per participant, hidden until stage 2), swift_answers (prompt_id → covered | not known, control, evidence), emerging_risks, votes (per participant, per candidate), gap_review notes, record (generated).
- **Interaction**: from_line, to_line, kind (triggers | amplifies | shared driver), note; **BowTie**: line_id, causes, preventive controls, event, recovery controls, consequences.
- **Trigger**: date, source, text, lines_touched, significance (significant | not), decision, decided_by, resulting_changes.
- **CycleRun**: kind (monthly | quarterly | annual | event | audit | management review), date, steps (B.8 step → done, evidence, owner, date), signed_by, signed_date, next_due.
- **Contract** (B.9): system_id, clause 1–17 → present | absent | partial, reference, gap note.
- **Document**: kind (register | heat map | FRIA | SoA | board report | workshop record | quarterly pack | evidence pack), generated_at, inputs_hash, file_path.
- **Event** (audit trail): timestamp, actor, entity, entity_id, field, old, new, reason, evidence_ref, ai_draft (model, version) if any.
- **DataPack**: name (library | regulatory calendar | indicator presets), version, date, source, signature.

**Identifiers.** Register IDs from the library persist (MOD-05 stays MOD-05 in every organisation, which makes registers comparable). New lines are ORG-nnn with the taxonomy code shown beside them. Systems get SYS-nnn. IDs are never reused.

## 5. The rules engine

All rules live in one module, `riskid/rules.py`, with a test per rule, because they are the method.

1. **Scoring.** Inherent = L × I. Band: ≤ 4 Low, ≤ 9 Moderate, ≤ 14 High, else Critical. Residual = rL × rI, same bands. (`build_register.py` is the reference implementation; the tests recompute the 91 library lines and must match it exactly.)
2. **Dominant dimension.** Impact is the maximum over the five dimensions; the dominant dimension is named; if harm to individuals scores 4 or 5 and is not dominant, the assessor must give the reasoning.
3. **Materiality.** Material if inherent ≥ 15 or impact = 5. Rules above the score: a line flagged `material_on_impact_alone` in the library (LEG-08) is material whatever the likelihood; a prohibited practice (Article 5) is material.
4. **Residual lock.** rL and rI default to L and I and cannot be lowered until at least one control on the line has a test date and a result; the data quality basis must then cite that test.
5. **The three failing fields** (B.2): a submission is returned if drivers_direct is empty or equals a stock phrase ("model error", "AI risk", "the model is wrong") ; if any control named "human in the loop" or "human oversight" has no override figure in its evidence; if data_quality is Medium without a basis.
6. **Never delete.** Retire with a reason; retired lines keep their ID and history and are excluded from the live register but included in the audit replay.
7. **Review dates.** next_review = min(calendar date by cycle, next trigger date); material lines carry a monthly indicator review.
8. **Version check.** A material system whose running version differs from its assessed version is flagged on the dashboard and in B.8 step 4.
9. **AI drafts.** Any field written by the assistant carries `ai_draft = (model, version, date)` until a person accepts it; an unaccepted draft counts as Very Low data quality (chapter 14).
10. **Pilots.** A system past its pilot end date without a deployment-gate record is flagged (OPS-08).

## 6. Screens

Server-rendered pages, one per module, each with a header line that names the chapter and template it implements and a "why" panel quoting the chapter's rule in one sentence (the Teach module).

1. **Dashboard**: systems by stage; lines by band (inherent and residual); material lines and their owners; indicators in amber or red; triggers unprocessed; next cycle due; version mismatches; pilots overdue; the heat map.
2. **Inventory** (B.1): list and form; discovery ratio (tools found against tools inventoried) entered per quarter.
3. **Library**: the 91 lines and 43 taxonomy lines; search; "propose lines for this system"; adopt.
4. **Workshop** (B.4, B.5): a facilitator view that walks the six stages; a participant entry view for pre-lists and votes (same machine, or a printed form keyed in).
5. **Use cases** (B.2): the template as a form with the examples from MOD-05 as placeholders; the return reasons shown in red.
6. **Reconcile**: the five steps as tabs; the disagreement log.
7. **Assess** (ch 9, B.6): the scales as pickers with their descriptions; the controls table; the locked residual; the record view.
8. **Interact** (ch 10): matrix grid; bow-tie editor (two columns of causes and consequences around the event); concentration view by vendor and model.
9. **Register** (B.3): the living inventory as a grid; line profile pages for material lines; audit replay by date.
10. **Documents** (ch 12): generate and download; FRIA per system assembled per B.7 with each Article 27(1) element and its source fields; SoA from Annex A references; board report (Principal AI Risk Report: top risks, movements, breaches, triggers, decisions).
11. **Cycle** (ch 13, B.8): the checklist runner; the indicator sheet; the trigger log; the regulatory calendar; sign-off.
12. **Contracts** (B.9): per vendor system, 17 clauses, gaps against lines.
13. **Settings**: organisation; people; AI assistant endpoint (off by default); data packs (import a signed pack); backup; export.

## 7. Documents generated

| Document | Source | Format |
|---|---|---|
| Register | RegisterLines + latest Assessment per line | XLSX (same columns as the book's register), CSV, PDF |
| Heat maps | Assessments | PNG (inherent, residual), same drawing as `build_register.py` |
| Line profile | one material line, all its records | PDF |
| Workshop record | Workshop | PDF |
| FRIA (per system) | B.7 mapping over inventory, template and register fields | PDF, DOCX |
| Statement of Applicability | Annex A references across live lines | XLSX, PDF |
| Principal AI Risk Report | dashboard state, movements since last report, triggers, decisions | PDF |
| Quarterly pack | CycleRun + register + change list + disagreement log | ZIP |
| Evidence pack | everything above plus the audit trail export | ZIP |

Every document records the data-pack versions and the register state hash it was built from.

## 8. The AI assistant (optional)

Off until the practitioner sets an endpoint. Any OpenAI-compatible chat endpoint: a local vLLM or Ollama, or a hosted model. What it may do: draft a use-case template from a system's inventory fields; draft SWIFT answers for a prompt from the inventory; propose library lines for a system with reasons; summarise a trigger text and name the lines it touches; draft the narrative sections of the board report from the numbers. What it may not do: set any score, rating, acceptance or owner; delete or retire; write to the audit trail as an actor. Every draft is shown in a draft colour with "Accept", "Edit", "Discard"; acceptance records the person. The adapter sends only the fields on the current screen, never the whole file, and logs each request (model, version, tokens) for the assessment record's field 6.

Execution settings for a local 27B, from the November 2026 measurements: reasoning effort medium; a thinking budget of about 3,000 tokens via the server's native budget where available; a reserved answer budget so a cut generation still returns its draft; drafts requested as JSON with a schema so they can be checked before display.

## 9. Architecture

- **Language and runtime**: Python 3.11+. No JavaScript framework; server-rendered HTML (Jinja2) with HTMX for in-page updates and a small amount of plain JavaScript for the heat map and the bow-tie editor.
- **Web**: FastAPI on localhost (default port 8765), started by `riskid serve`; opens the browser. No network listener beyond loopback unless configured.
- **Storage**: SQLite via the standard library plus a thin repository layer; the event table is append-only; projections are rebuilt from it on demand (`riskid rebuild`).
- **Documents**: openpyxl for XLSX, matplotlib for heat maps, WeasyPrint for PDF (HTML templates shared with the screens), python-docx for the FRIA.
- **Data packs**: the library, taxonomy, indicator presets and regulatory calendar ship as TSV/JSON in `riskid/data/`, each with a version file; a signed pack can be imported to update them (the Harness service's delivery route).
- **CLI**: `riskid init <org>`, `riskid serve`, `riskid import-library`, `riskid export <kind>`, `riskid replay <date>`, `riskid check` (runs the rules over the file and prints the violations), `riskid backup`.
- **Packaging**: `pipx install riskid-workbench`; a single-file build per platform with PyInstaller for people who cannot install Python; a `.riskid` file is portable between them.
- **Repository layout**:

```
riskid-workbench/
  pyproject.toml            name riskid-workbench, Apache-2.0
  riskid/
    __init__.py  cli.py  app.py  config.py
    rules.py                the method's rules, one function each
    model.py                dataclasses for every entity in §4
    store.py                SQLite, events, projections, replay
    importers.py            library, taxonomy, packs
    documents/              register.py heatmap.py fria.py soa.py report.py packs.py
    ai/                     adapter.py prompts.py (schemas for drafts)
    web/                    routes_*.py per module; templates/; static/
    data/                   register.tsv taxonomy.tsv indicators.json calendar.json VERSION
  tests/                    one file per rule, per document, per route; golden files
  docs/                     this specification, the plan, the brochure, user guide
```

## 10. Security and privacy

Local only; no telemetry; no outbound calls except the configured AI endpoint, and then only the current screen's fields. The `.riskid` file may be encrypted at rest with a passphrase (SQLCipher if available, otherwise a warning in Settings). Backups are plain copies with a timestamp. Personal data in the inventory (owners' names, persons affected as categories) is the practitioner's responsibility; the tool stores categories, not individuals, in persons_affected.

## 11. Quality and acceptance

**Tests that define done.**
- Rules: recomputing the 91 library lines reproduces `build_register.py`'s inherent, residual, bands and materiality exactly (golden file); each rule in §5 has a positive and a negative test; the residual lock cannot be bypassed through any route.
- Documents: the FRIA assembled for a fixture system contains each Article 27(1) element with its source fields; the SoA lists exactly the Annex A references on live lines; the register XLSX has the book's column order.
- Audit: a sequence of changes replayed to a date gives the register as it stood; a deletion attempt is refused through the API and the UI.
- Routes: every screen renders for an empty organisation and for the fixture organisation; a submission with a stock driver is returned with the reason.
- Packaging: `pipx install` from the repository and `riskid serve` on a clean machine; the PyInstaller binary starts and opens the dashboard.

**Acceptance for version 1**: a practitioner following chapter 5 to chapter 13 with the fixture organisation (three systems) reaches a signed quarterly pack without leaving the tool, and the pack opens in Excel, a PDF reader and a browser.

## 12. What is left to the builder

The visual design within the EON palette; the exact HTMX interactions; the bow-tie editor's layout; the PDF page designs; error messages. The builder may not change the rules in §5, the field lists in §4, or the principles in §1 without a note in `docs/DECISIONS.md` and a test.

## 13. Later versions

Multi-user with roles (owner, assessor, overseer, auditor) over a shared file or a small server; the Tauri chassis as a desktop wrapper; the Harness feed as a live socket rather than imported packs; a Delphi round runner with external participants; import of existing spreadsheets by column mapping; a Welsh, Irish, French and German interface, since the Act's persons affected are not all English speakers.
