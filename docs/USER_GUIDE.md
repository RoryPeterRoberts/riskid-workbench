# RiskID Workbench user guide

The workbench runs the method of *AI Risk Identification* on one organisation
file. Each screen implements one chapter, names it in its header, and quotes the
chapter's rule beside its opening case. This guide gives one page per screen, in
the order of the method.

## Starting

```
pipx install git+https://github.com/RoryPeterRoberts/riskid-workbench   # or `pipx install .` in a copy
riskid init my-organisation.riskid     # creates the file and loads the data packs
riskid serve my-organisation.riskid    # opens the workbench in the browser
```

Without Python, use the single-file build (`packaging/riskid.spec`), which takes
the same commands.

The workbench listens on this machine only (`127.0.0.1:8765`). Every change is
an event in the file's audit trail, recorded in the name of the person
recording (Settings). Nothing is deleted: a line is retired with a reason, and
the register can be replayed as it stood on any date. The file is the whole
record; copy it to move it, and back it up from Settings.

## Inventory (chapter 5, template B.1)

List every AI system before identifying its risks: "you cannot identify the
risks of a system you have not listed." The form follows B.1 row by row, with
the register lines each row informs. It records the Article 6 classification
as one of six outcomes, and the lifecycle stage, the version running and the
version last assessed, and the pilot end date. Record each quarter's discovery
ratio (tools found against tools inventoried) under the list. A system is
refused without a name, an owner, a role under the Act and a classification
outcome.

## Library (chapter 4, Appendix A)

The 91 lines of the book's register and the 42-node taxonomy, read-only. For a
system, *Propose* sorts the lines into those proposed and those removed, with
the reason for each: role, lifecycle stage, the articles the system's
classification engages, and the persons affected. *Adopt* puts a line into
the register for that system, keeping its ID (MOD-05 stays MOD-05).

## Workshop (chapter 6, templates B.4 and B.5)

A top-down SWIFT workshop in B.5's six stages: opening, independent
assessment review, SWIFT rounds, emerging risks, multivoting and gap review.
Each participant's pre-list stays hidden until stage 2. The 23 SWIFT prompts
of B.4 are answered covered or not known, with the control and the evidence.
Votes are kept per participant, and the record shows where they disagree; it
gives no average. Closing the workshop adds the voted lines to the register as
top-down candidates for the system they were proposed for; emerging risks go
to the gap list.

## Use cases (chapter 7, template B.2)

Bottom-up submissions, one per risk, by the people who operate the system. A
submission is returned with its reasons when the direct drivers are empty or a
stock phrase, a human-oversight control has no override figure, a Medium
rating has no basis, or the template is incomplete. An accepted one becomes a
candidate line: the library ID given in field 1, or a new ORG line. The
coverage table shows which of the ten specialist sub-processes have
contributed for each system.

With the assistant on (Settings), *Draft with the assistant* drafts a use case
from the system's header lines. The draft is shown in a blue draft colour and
counts as Very Low data quality until a person accepts it. Check each field
against its source, name the owner, rate the data quality, then submit to
accept it, or discard it. The person who submits is recorded as accepting it.

## Reconcile (chapter 8)

Top-down and bottom-up meet here, matched on taxonomy node and system. Each
gap, in either direction, and each library line that neither route found, takes
one of five dispositions: add, merge, escalate, accept as local, or close as
not applicable. Each needs a reason, and is applied in one change. The
disagreement log keeps minority views with their evidence. Sign the record at
the end of the session.

## Assess (chapter 9, template B.6)

The seven-field assessment record. Impact is scored on five dimensions and
the dominant one named; harm to individuals at 4 or 5 that is not dominant
needs the reasoning. Materiality follows the rule: inherent 15 or more, impact
5, or a line flagged material on impact alone. The residual stays at the
inherent score until a control on the line has passed a dated test, and the
data quality basis must then cite that test. The heat maps show inherent and
residual placement.

## Interact (chapter 10)

The interaction matrix of material lines and the lines linked to them: a link
is triggers, amplifies or shared driver, read from row to column, and needs its
mechanism. Propagation and vulnerable nodes are listed, with candidate links by
shared controls. Bow-ties set the causes and preventive controls against the
consequences and recovery controls of one event, with one owner. The
concentration view shows systems sharing a model, a provider or a supplier.

## Register (chapter 11, template B.3)

The living register: every live line with its latest assessment, trend and
interactions. Each line has a profile with its assessments, controls,
disagreements and audit trail. Owner, COSO category and definition change with
a reason; a line is retired with a reason and stays in every replay. *As of*
replays the register as it stood on a date. The signs of a living inventory are
shown under the grid.

## Documents (chapter 12, template B.7)

The register as XLSX (the book's thirty columns), CSV and PDF; the fundamental
rights impact assessment per system, each Article 27(1) element assembled from
the fields B.7 maps to it; the Statement of Applicability from the Annex A
references on live lines; and the Principal AI Risk Report, chapter 12's twelve
items. Every document records the data-pack versions and the register state it
was built from, and each download is recorded in the audit trail.

## Cycle (chapter 13, template B.8)

The indicator sheet shows each indicator green, amber or red against its
thresholds; a reading that turns red logs a trigger. The trigger log lists the
lines each trigger touches and why, brings their reviews forward, and records
the significance decision with its reason. The regulatory calendar shows
chapter 15's dates by role. A quarterly or annual run works through B.8's 18
steps with evidence and an owner per step, showing what the register already
answers for ten of them. Sign-off needs evidence on every step; it fixes the
next run and dates each line's next review. The quarterly pack holds the
register as signed, the change list, the disagreement log and the checklist;
the evidence pack holds everything, with the audit trail.

## Contracts (chapter 12, template B.9)

The 17 clauses of B.9 for each system bought from a supplier or built on a
model provider's model, each recorded present, partial or absent. A clause is
a gap when it is not present and one of its register lines is live on the
system. The list shows the share of contracts that meet the clause standard.

## Settings (chapter 14)

The organisation and its named roles; the people, and who is recording; the
assistant; the data packs and their versions; and the file. The assistant is
off until an endpoint and a model are set and it is switched on. It sends only
the fields on the screen it drafts for, never sets a score, a rating, an
acceptance or an owner, and its API key is read from a `RISKID_` environment
variable, never stored. The file is not encrypted at rest, so keep it on an
encrypted disk. *Download a backup* gives a plain copy of the file.
