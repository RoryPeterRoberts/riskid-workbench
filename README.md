# RiskID Workbench

The *RiskID Workbench* is the AI risk identification method as software. The book
gives a practitioner a method in six phases and nine templates for producing an AI
risk register that stands up to ISO/IEC 42001 clause 6.1.2 and Article 9 of the EU
AI Act; in practice the work is done in spreadsheets that drift, and the record
cannot be reconstructed when an auditor or supervisor asks for it. The Workbench
is the method as software: every form is one of the book's templates, every rule
is enforced by the program, and one record produces every document the method
calls for, with the data staying on your machine.

It is built for the practitioner who has to produce the evidence — the risk or
compliance lead, the DPO, the AI officer, or a consultant: one person, or a small
team sharing a file. Version 1 covers phases 1 to 6 of the method, the
integration outputs, the cycle and the contract checklist, and deliberately leaves
out multi-user concurrency, cloud hosting, and any automated scoring.

Status: **in build.** Rounds 0 to 4 of `docs/PLAN.md` are done: the data packs,
the rules, the store and its audit trail, and the Inventory screen. To try it:
`pip install -e .`, then `riskid init my.riskid` and `riskid serve my.riskid`.
Read `docs/SPEC.md` (what it is), `docs/PLAN.md` (how it is built, round by
round) and `docs/RiskID_Workbench_Brochure.pdf` (for the Risk Manager).

Apache-2.0.
