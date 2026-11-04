# LATER

Ideas that came to mind during a round but are out of scope for that round.
One line each (`PLAN.md` rule 11).

- round 0: none yet.
- round 4: B.1 field 8 asks for the ISO/IEC 42001 role as well as the role
  under the Act; SPEC.md section 4 has no field for it.
- round 4: the Dashboard (SPEC.md 6.1) needs a round; `/` then becomes the
  dashboard and the round 0 smoke test changes with it.
- round 4: errors such as an unknown system ID answer with FastAPI's JSON
  body; a page in the shell would read better.
- round 4: `load_packs` commits once per event (136 commits on `riskid
  init`); one transaction would make init and the tests faster.
- round 5: chapter 5 says one risk can sit across many systems, but a
  register line has one `system_id` (SPEC.md section 4), so a second system
  cannot adopt a line already in the register.
- round 5: chapter 5 asks for a recorded reason for every library line not
  kept; the proposal page shows the filter's reasons but has no "declined
  with reason" record for the person's own decisions.
- round 5: three lines cite an Annex III point (FAI-01, FAI-02, FAI-03); the
  inventory records the Article 6 outcome but not the Annex III point, so
  those citations are not matched.
- round 6: the controls listed in an accepted use case (B.2 field 8) could
  seed the controls table of the Assess round.
- round 6: the use-case form has four control rows; an HTMX "add a row"
  would allow more.
- round 7: chapter 6's assumption register (one of its five outputs) has no
  entity or screen yet.
- round 7: the Delphi rounds for emerging and frontier risks (SPEC.md
  section 2) are not built; the emerging risks are listed for them.
- round 7: B.5's quarterly session keeps stages 1, 2, 3 (change prompts
  only), 5 and 6; the workshop does not yet distinguish a quarterly session.
- round 7: a workshop on several systems puts each top-down line on one
  system (the first it was proposed for), because a register line has one
  `system_id`.
- round 7: emerging risks stay in each workshop's taxonomy gap list; the
  organisation-wide gap list for chapter 4's taxonomy maintenance has no
  entity yet.
- round 8: chapter 8's enterprise AI risk map (systems against shared
  vendors, models, data and overseers) is not built.
- round 8: chapter 8's ownership rules (natural owner, largest exposure, the
  designated senior manager) are not applied when a gap is resolved; the
  owner is set elsewhere.
- round 8: an escalated line has no "principal" flag on the register line;
  the resolution records the escalation.
- round 9: chapter 9's rule that lines sharing a cause are tested together
  (their sum can be material when no part is) is not applied.
- round 9: the controls listed in an accepted use case could be offered as the
  line's controls on the Assess screen.
- round 10: chapter 10's concentration by reviewer pool and by data source
  needs those recorded per system; the inventory has users and data but not
  as comparable keys.
- round 10: B.3 field 11 (risk interaction summary) could be filled from the
  matrix and the bow-tie reference on each line.
- round 11: chapter 11's risk profile has fourteen elements (drivers, exposure,
  cost-benefit, incident history among them); the profile page shows the
  line's fields, assessments, controls, disagreements and trail, and the PDF
  profile of SPEC.md section 7 comes with the Documents round.
- round 11: chapter 11's governance rule that a change is reviewed by someone
  outside the system's team before it takes effect is not enforced.
- round 11: `riskid/store.py` is at the 400-line limit; the next store change
  should first move `init` and `rebuild` to their own module.
