# Book tables for the builder (copied verbatim from the book, 3 November 2026)

## Chapter 9 scales
## The Five Consequence Dimensions
### Financial Impact
| Score and rating | Description |
|---|---|
| 1 Incidental | Less than 0.1% of annual revenue or budget |
| 2 Minor | 0.1–1% |
| 3 Moderate | 1–5% |
| 4 Major | 5–15% |
| 5 Extreme | More than 15%, or threatens the viability of the organisation |
### Regulatory and Legal Impact
| Score and rating | Description |
|---|---|
| 1 Incidental | No regulatory or legal impact |
| 2 Minor | Informal regulator feedback, minor findings, individual complaints resolved |
| 3 Moderate | Formal investigation or enforcement warning, claims by individuals |
| 4 Major | Formal enforcement action, significant fines, restrictions on activities, an order to stop or withdraw a system, a claim by a group of affected persons |
| 5 Extreme | Withdrawal of authorisation, criminal prosecution, penalties in the highest tier of Article 99, or the same breach established against every person the system has decided about |
### Reputational Impact
| Score and rating | Description |
|---|---|
| 1 Incidental | No external coverage |
| 2 Minor | Limited trade or local press, quickly contained |
| 3 Moderate | National press coverage, sustained for days |
| 4 Major | International press, sustained coverage, loss of key customer or partner relationships |
| 5 Extreme | Total loss of public confidence, departure of the board or chief executive, sustained international coverage |
### Harm to Individuals
| Score and rating | Description |
|---|---|
| 1 Incidental | None |
| 2 Minor | Inconvenience |
| 3 Moderate | Material and reversible detriment to some individuals |
| 4 Major | Serious or irreversible harm to some individuals, or material harm to many |
| 5 Extreme | Death, mass harm, or loss of fundamental rights at scale |
### Customer and Operational Impact
| Score and rating | Description |
|---|---|
| 1 Incidental | Negligible disruption, no customer impact |
| 2 Minor | Limited disruption, minimal customer impact |
| 3 Moderate | Significant disruption, noticeable degradation of service |
| 4 Major | Major service disruption, large-scale customer impact, material complaints |
| 5 Extreme | Total service failure, mass customer harm, systemic operational breakdown |
## Likelihood
| Score and rating | Description |
|---|---|
| 1 Rare | Less than 1% |
| 2 Unlikely | 1–10% |
| 3 Possible | 10–50% |
| 4 Likely | 50–90% |
| 5 Frequent | More than 90%, or already occurring |
## Vulnerability
| Score and rating | Description |
|---|---|
| 1 Very Low | Robust controls, tested under stress |
| 2 Low | Adequate controls, minor gaps |
| 3 Medium | Controls exist, with known weaknesses or untested elements |
| 4 High | Material control gaps, limited resilience |
| 5 Very High | No effective controls, fully exposed |
## Speed of Onset
| Score and rating | Description |
|---|---|
| 1 Very Slow | Years |
| 2 Slow | Quarters |
| 3 Moderate | Months |
| 4 Fast | Weeks |
| 5 Immediate | Days or less |
## Data Quality
| Rating | Basis |
|---|---|
| High | Measurements on the organisation's own system and data, or an extensive public record |
| Medium | Limited measurement plus structured expert judgement, such as partial test results or checked vendor documentation |
| Low | Mainly expert judgement or the supplier's own claims, such as workshops or vendor benchmarks not reproduced on your data |
| Very Low | Speculative, with no relevant data or precedent, as with agentic and novel uses |
## Inherent and Residual

## Chapter 13 cycle and indicator tables
| Speed | What runs | Output | ISO/IEC 42001 | EU AI Act |
|---|---|---|---|---|
| Monthly | Indicator review for each material line | Indicator sheet, trends, escalations | 9.1, A.6.2.6 | Art 26(5), 72 |
| On an event | Targeted update after a trigger | Updated lines, significance decision | 8.2, 8.4 | Art 9(2)(c), 25(1), 73 |
| Quarterly | Active re-identification | Signed register, change list, disagreement log | 8.2, 8.3 | Art 9(2) |
| Annually | Full re-identification from the start | New baseline, comparison with last year | 6.1.1, 6.1.2, 8.4 | Art 6(4), 9(2), 27(2) |
| At planned intervals | Internal audit of the process | Findings, nonconformities | 9.2, 10.2 | None specific |
| At planned intervals | Management review | Decisions on changes and on residual risk | 6.1.3, 9.3 | Art 9(5) |
| Indicator | Register lines | What a movement can mean | Read by |
|---|---|---|---|
| Share of production inputs outside the training distribution; feature-distribution alerts | DAT-05, DAT-01 | The population or data feed has moved, so validation figures no longer apply | System owner |
| Accuracy on recent labelled cases, where outcomes arrive | MOD-06, MOD-02 | Concept drift: what the model learned no longer holds | Model owner |
| Override rate; agreement with the model on a blind sample | HUM-01, HUM-07 | A rise: the model is worse or trust is falling. A fall towards zero: review may be rubber-stamping | Business owner |
| Complaints and explanation requests per thousand decisions; appeals overturned | TRA-02, FAI-01 | Harm reaching people outside the organisation, often before any internal measure moves | Service owner |
| Incidents and near-misses, with time from awareness to report | Any line | Control failure; a serious-incident clock may be running | AI officer |
| Vendor version changes; regression pass rate per version | MOD-05 | A changed model behind a stable interface | System owner |
| Changes without a linked re-assessment | OPS-05 | Change control bypassed | System owner |
| Cost per transaction against plan | OPS-04 | Abuse, retries, longer outputs or a price change | Operations and finance |
| Tools found against tools inventoried; pilots past end date | OPS-07, OPS-08 | Shadow AI growing; pilots going live | AI officer |

## Appendix B templates (B.1–B.9)
# Appendix B: Templates

These are the templates the chapters refer to, set out as tables you can copy. They follow the artifact list of the bank book and are adapted for AI. There are nine. Adapt them to your organisation the first time you use them, and keep a note of what you change and why.

## B.1 AI System Inventory Fields

One line per AI system (Chapter 5, Setting the Context: Inventory, Roles, Classification and the Starting Universe). Fields 1 to 11 are the inventory fields of Chapter 5. Fields 12 to 18 are additions that later chapters rely on.

| # | Field | What to record | Why it is there |
|---|---|---|---|
| 1 | System | Name, business function and components; a unique, persistent system ID | Lists each system once; the ID links to the register, the impact assessments and the logs |
| 2 | Vendor or built | Built, bought, or bought and configured; supplier and contract; any model provider behind the product | Who holds the documentation (Articles 13, 25(4)); DAT-04, TRA-04 |
| 3 | Model and version | Model name, version identifier, date of the last change notice, whether the version can be pinned | MOD-05, OPS-05 |
| 4 | Purpose | The intended purpose as the provider states it, and the purpose in use | HUM-03; A.9.4 |
| 5 | Users | Who operates the system or acts on its output, by role and number | Articles 4, 26(2); HUM-05 |
| 6 | Persons affected | People whose money, access, rights or health the output affects, including those unaware of the system; children and vulnerable groups flagged | Article 27(1)(c); ISO/IEC 42005, section 6.7 |
| 7 | Data | Training sources if built; production inputs; personal and special-category data; where data is sent and kept | A.4, A.7; Articles 10, 26(4) |
| 8 | Role under the Act | Provider, deployer or both; the ISO/IEC 42001 role; the Article 25 check | Articles 3, 25; LEG-07 |
| 9 | Classification | The Article 6 outcome and a reference to the record, with the Article 5 screen and any Article 50 duty | Articles 5, 6, 49; LEG-07, LEG-08 |
| 10 | Owner | One named person accountable, with the model owner and data owner | A.3.2; TRA-05 |
| 11 | Stage | One of the seven lifecycle stages | OPS-08 |
| 12 | Jurisdictions | Where it is used and where the affected persons are | Regulatory hooks (Chapter 15) |
| 13 | Period and frequency of use | How long and how often it is used | Article 27(1)(b) |
| 14 | Impact assessments | DPIA, fundamental rights impact assessment and ISO/IEC 42005-style assessment: reference, date, next due | A.5; Articles 26(9), 27 |
| 15 | Last risk assessment | The date, and the version assessed | The quarterly version check (Chapter 13) |
| 16 | Discovery source | Declared, procurement, scan, audit or incident | Measures shadow AI (OPS-07) |
| 17 | Pilot end date | The date by which the pilot closes or goes through the deployment gate | OPS-08; A.6.2.5 |
| 18 | Logs | Where they are kept and for how long | Articles 12, 26(6); A.6.2.8; TRA-07 |

## B.2 The AI Use-Case Template

The template has a five-line system header above eleven fields (Chapter 7, Bottom-Up Identification: The AI Use-Case Template and the Specialist Sub-Processes). Complete one for every risk, with the person who operates the system.

| Header line | Record | Note |
|---|---|---|
| Header 1: System and version | The system, the model version, the application version and the date of the last change | The assessment applies to this version only |
| Header 2: Role | Provider, deployer or both, for this use case | Decides which obligations of the Act apply |
| Header 3: Lifecycle stage | One of the seven stages: inception; design and development; verification and validation; deployment; operation and monitoring; re-evaluation; retirement | Controls and evidence differ by stage |
| Header 4: Intended purpose and users | The purpose as the provider states it, the purpose in use, who operates the system and who relies on its output | Compare the two purposes (HUM-03) |
| Header 5: Persons affected | Who the output affects, and whether they know | Feeds harm to individuals and Article 27(1)(c) |

| # | Field | What to write | Example (MOD-05) |
|---|---|---|---|
| 1 | Risk ID | A unique ID from the central function; keep the register ID where you adopt a line | MOD-05 |
| 2 | Taxonomy classification | Level 1 and Level 2 code | MOD, 2.3 |
| 3 | Risk definition | What could happen, in plain words, not the category | The supplier replaces the model behind the interface without notice and our thresholds stop holding |
| 4 | Underlying drivers, direct | What directly causes or triggers the risk | The contract allows changes without notice; the version is not pinned |
| 5 | Underlying drivers, indirect | What amplifies or enables it | One supplier; no regression suite; nobody reads supplier notices |
| 6 | Quantitative metrics | Measured values and limits, with the date and the sample | Version changes per quarter; regression pass rate per version |
| 7 | Qualitative information | Narrative where numbers do not exist, with the source of each statement | Overseers report that the style of answers has changed |
| 8 | Current controls (type and effectiveness) | Each control, its type (preventive, detective or corrective), its last test date and its evidence | Version pinning (preventive), tested at the last release; weekly regression run (detective) |
| 9 | Risk owner | One named person | Name and role, not a team |
| 10 | Emerging risk indicators | Early signals that the risk is rising | A supplier deprecation notice; a change in the refusal rate |
| 11 | Data quality rating | High, Medium, Low or Very Low, with the basis stated | Medium: our own regression results exist, the supplier's change history does not |

Three fields fail more often than the others: the drivers, the controls and the data quality rating. In AI they fail in recognisable ways. The driver is written as "model error" and nothing more. The control is "human in the loop", with no override data to show that the human changes anything. The data quality rating is Medium on every line. Return any submission with those entries.

## B.3 The Fourteen-Field Inventory and the Five AI Context Columns

The living inventory of Chapter 11 (Documentation: The Living AI Risk Inventory). Fields 1 to 14 are the fields of the bank book. Fields 15 to 19 are the AI context columns. Phases are those of this book.

| # | Field | What it holds | Source |
|---|---|---|---|
| 1 | Risk ID | A unique identifier that persists across cycles; keep the register's IDs | Phase 2 |
| 2 | Taxonomy classification | Level 1, Level 2 and the line, using the codes of Chapter 4 | Phase 2 |
| 3 | Risk definition | The event in plain words, naming the mechanism and who is affected | Phase 2 |
| 4 | COSO objective category | Strategic, operations, reporting or compliance | Phase 1 |
| 5 | Risk owner | A named person, never a committee or a vendor | Phase 2 |
| 6 | Inherent risk score | The harm scored and its unit of exposure; impact with the dominant dimension named; likelihood; vulnerability; speed of onset | Phase 4 |
| 7 | Control summary | Key controls by type and effectiveness, with the date and result of the last test | Phases 2 and 4 |
| 8 | Residual risk score | Impact and likelihood after tested controls | Phase 4 |
| 9 | Material (Y/N) | Whether the line meets the materiality rule | Phase 4 |
| 10 | Data quality rating | High, Medium, Low or Very Low, with the evidence | Phase 4 |
| 11 | Risk interaction summary | Links to other lines (triggers, amplifies, shared driver) and the bow-tie reference | Phase 5 |
| 12 | Key risk indicators | Indicators with current values and green, amber and red thresholds | Phases 2 and 4 |
| 13 | Trend indicator | Increasing, stable or decreasing since the last assessment, or new | Phase 4 and the cycle |
| 14 | Date of last review and next review | The next review is the earlier of the calendar date and the next trigger event | The cycle |
| 15 | Lifecycle stage | One or more of the seven stages | Taxonomy tags |
| 16 | Role | Provider, deployer or both | ISO/IEC 42001, clause 4.1; the Act, Article 3 |
| 17 | Persons affected | The people and groups the system acts on, including those who do not know it is used | Article 27(1)(c) |
| 18 | Regulatory hooks | The articles, clauses and sector rules the line engages | Chapter 15 matrix |
| 19 | ISO/IEC 42001 Annex A control references | The Annex A controls the line relies on | Statement of Applicability |

## B.4 SWIFT Prompt Set for AI

Use with the workshop of B.5 (Chapter 6, Top-Down Identification: Workshops, SWIFT, Scenarios, Delphi and Red Teams). Apply each prompt to each system on the inventory, or to each class of system where the estate is large. Record the answer as covered, with the control and its evidence, or as not known. Prompts 1 to 14 are the set in Chapter 6. Prompts 15 to 23 are additions.

| # | Prompt | Register lines |
|---|---|---|
| 1 | What if the vendor changes the model behind the service and does not tell us? | MOD-05 |
| 2 | What has changed in our customers, products or data since the model was built? | DAT-05, MOD-06 |
| 3 | What if a user pastes personal or confidential data into the system, or into a public tool in its place? | LEG-05, LEG-03 |
| 4 | What if the model is wrong and sounds certain? | MOD-01 |
| 5 | What if a document, email or web page the model reads contains instructions? | SEC-02 |
| 6 | What if the overseer stops overriding the model? | HUM-01 |
| 7 | Could the overseer override the model at all, and has anyone the time to? | HUM-07 |
| 8 | What if the system is used for a purpose it was not built for? | HUM-03 |
| 9 | What if a regulator, a court or a complainant asks for the log of one decision? | TRA-07 |
| 10 | What if the supplier withdraws the product, is bought, or changes its terms? | OPS-02 |
| 11 | What if the system works on average and badly for one group of people? | FAI-04 |
| 12 | What if the people affected are not told, or cannot challenge the outcome? | TRA-02 |
| 13 | Could the system do more than its task needs if it acts on a wrong or planted instruction? | SEC-08, MOD-10 |
| 14 | What are we assuming about the vendor's testing that we have not checked on our own data? | MOD-08 |
| 15 | What if the cost per transaction doubles? | OPS-04 |
| 16 | What if the system learns from its users in production? | OPS-06, FAI-06 |
| 17 | Could someone trick, jailbreak or instruct the system into acting against policy? | SEC-01, HUM-04 |
| 18 | Could someone use the technology to impersonate our staff or our customers? | SOC-02 |
| 19 | Could something in the supply chain, such as a model, library or plugin, be compromised? | SEC-09 |
| 20 | What has changed since last year that could alter the classification, the law that applies or the persons affected? | LEG-07, LEG-09 |
| 21 | Where are the gaps between data science, security, legal and the business? Who owns the risk that sits between them? | TRA-05, SOC-02 |
| 22 | Where are the gaps between the pilot and production? | OPS-08, MOD-09 |
| 23 | What if the service is down for a day, or staff can no longer do the task by hand? | OPS-03, HUM-06 |

## B.5 Top-Down Workshop Agenda

The stages follow the bank method. The full session takes about four hours. The quarterly session takes two to three hours and keeps stages 1, 2, 3 (with the change prompts only), 5 and 6.

| Stage | Duration | Purpose | For AI |
|---|---|---|---|
| 1 Opening | 15 minutes | State the objectives, the ground rules and the system and version in scope; the straw man is there to be challenged | Name the version running today |
| 2 Independent assessment review | 30 minutes | Show the anonymised results of the written pre-workshop lists and where they disagree | Each participant wrote a top-ten list before seeing the straw man, the sceptic included |
| 3 SWIFT rounds | 90 to 120 minutes | Systematic what-if questioning of each element | Use the prompt set in B.4 |
| 4 Emerging risk session | 30 minutes | Risks not yet in the taxonomy | Agents, new supplier features, new capability; items for the Delphi rounds |
| 5 Multivoting | 20 minutes | Each participant allocates votes to the risks they rate highest | Record the votes; do not average away a dissent |
| 6 Gap review | 15 minutes | Check the output against the taxonomy and the register | Add to the taxonomy gap list |

| Seat | Why |
|---|---|
| Business owner | Answers for the outcomes of the system |
| Data science lead or model owner | Knows how the system works and how it fails |
| Security | Brings the attacker's view |
| Data protection officer | Brings the view of the people whose data is processed |
| Overseer | Reviews outputs or overrides the system day to day |
| Sceptic | Has a written remit to argue that the system should not be used or that the list is incomplete |
| Procurement or legal | Added where the portfolio depends on bought systems |
| Facilitator (the AI officer) | Runs the session and records it; does not report to the owner of any system under discussion |

Internal audit does not take part. Rotate one or two seats each cycle.

## B.6 The Seven-Field Assessment Record

One record for every line when Phase 4 is complete (Chapter 9, Assessment: Four-Dimensional Scoring, Harm to Individuals and Data Quality). It mirrors the bank record and adds the points that matter for AI.

| # | Field | Content | AI note |
|---|---|---|---|
| 1 | Inherent risk score | The harm scored and its unit of exposure; impact with dominant dimension, likelihood, product and band, vulnerability, speed of onset | Score harm to individuals as its own dimension; give the reasoning for the dominant one |
| 2 | Control effectiveness | Each control by type, the test that showed it works, the date and the result | The test is on the current version; "human in the loop" needs override data |
| 3 | Residual risk score | Impact and likelihood after tested controls, product and band | State whether the residual risk is judged acceptable under the risk criteria, and by whom (Article 9(5); clause 6.1.3) |
| 4 | Data quality rating | High, Medium, Low or Very Low, with the evidence | A supplier's evaluation of an earlier version is not High |
| 5 | Materiality | Material or not, and the basis | Apply the rule in Chapter 9 |
| 6 | Model and vendor dependency | Where a model or vendor evaluation informs the score: its assumptions, its limits, and who outside the building team challenged it | Include any AI-drafted text or comparison scoring the assessment relies on |
| 7 | Disagreement record | The minority score, the dimension in dispute, the evidence on each side | Goes to the disagreement log (Chapter 8) |

## B.7 Fundamental Rights Impact Assessment Mapping

Article 27(1) lists six elements. The table maps each to the columns of the register and the fields of the inventory and the template, so that one record serves the assessment (Chapter 12, Integration: Impact Assessments, the Statement of Applicability, Monitoring and the Board).

| Element | What the Act asks for | Register columns | Inventory and template fields |
|---|---|---|---|
| 27(1)(a) | A description of the deployer's processes in which the system will be used in line with its intended purpose | Title and description of the lines that apply; lifecycle | Header 1 and Header 4; inventory fields 1, 4 and 5 |
| 27(1)(b) | The period within which, and the frequency with which, each system is intended to be used | Lifecycle | Template field 6 (volume and frequency); inventory field 13; Header 3 |
| 27(1)(c) | The categories of natural persons and groups likely to be affected in the specific context | Harmed | Header 5; inventory field 6; context column 17, persons affected |
| 27(1)(d) | The specific risks of harm likely to affect those categories, taking account of the provider's Article 13 information | Lines in categories 3.x, 5.5 and 7.1 (the FAI lines, HUM-08, LEG-01, LEG-02): title, description, L, I with dimension IND, V, S, data quality | Template fields 3 to 7 and 11; assessment record fields 1 and 4; the provider's information cited in field 7 |
| 27(1)(e) | A description of the implementation of human oversight measures, according to the instructions for use | Controls (A.9.3) and owner of HUM-01, HUM-05 and HUM-07; indicator (override rate) | Inventory field 5; template field 8; the named overseer |
| 27(1)(f) | The measures to be taken if those risks materialise, including internal governance and complaint mechanisms | Recovery controls, owner and indicators, residual L and I; TRA-02 | Template fields 8 to 10; the complaints and concerns channels (A.8.3, A.3.3); inventory field 10 |

The assessment is carried out before the first use of a system, and its information is updated when an element changes or is no longer up to date (Article 27(2)). Its results go to the market surveillance authority on the questionnaire template that the AI Office is to develop (Article 27(3), (5)); I had not found a published template by 1 November 2026. Where a DPIA already covers an element, the assessment complements it, and since the Digital Omnibus the deployer may cross-refer to the DPIA (Article 27(4)). From 2 December 2027 the duty applies to high-risk systems listed in Annex III other than critical infrastructure (point 2). It falls on deployers that are public bodies or private entities providing public services, and on deployers of the systems in Annex III, points 5(b) and (c): creditworthiness and credit scoring of natural persons, fraud detection excepted, and risk assessment and pricing in life and health insurance.

## B.8 Quarterly Re-Identification Checklist

The checklist for the cycle of Chapter 13 (The Ongoing Cycle: Re-Identification, Triggers, Indicators and Audit).

| # | Group | Step | Evidence | Owner |
|---|---|---|---|---|
| 1 | Inventory | Run discovery and compare tools found with tools inventoried | Discovery report and ratio | AI officer |
| 2 | Inventory | List pilots past their end date | Pilot register | AI officer |
| 3 | Inventory | Confirm every material system has a named owner in post | Inventory | AI officer |
| 4 | Inventory | Check that the version assessed is the version running, for every material system | Version record against logs | System owners |
| 5 | Context | Update the external context: guidance, enforcement decisions, supplier notices, incidents elsewhere | Context note mapped to the taxonomy | Compliance |
| 6 | Context | Review the regulatory calendar for the next twelve months | Calendar | Compliance |
| 7 | Context | Classify again any system whose use changed; confirm the Article 6(4) records | Classification records | Compliance |
| 8 | Triggers and indicators | Confirm that every trigger since last quarter was processed and logged | Trigger log | AI officer |
| 9 | Triggers and indicators | Review the indicators for each material line: breaches, trends, whether thresholds still fit | Indicator sheet | System owners |
| 10 | Workshop | Collect each participant's written list of changes before the session | Pre-workshop submissions | Facilitator |
| 11 | Workshop | Run the focused SWIFT session with the change prompts | Workshop record | Facilitator |
| 12 | Assessment | Re-assess the material lines on fresh evidence and record the reason for any change | Assessment records | Assessors |
| 13 | Assessment | Review data quality ratings; lower any that rest on evidence about an earlier version | Rating changes | Assessors |
| 14 | Assessment | Test the assumption register against current evidence | Assumption register | System owners |
| 15 | Close | Reconcile with the bottom-up submissions and update the disagreement log | Disagreement log | Risk function |
| 16 | Close | Update the register: new lines, escalations, retired lines (retire with a reason, never delete) | Register with audit trail | AI officer |
| 17 | Close | Update the inputs to the board report and the Statement of Applicability if controls changed | Report inputs; statement | AI officer |
| 18 | Close | Obtain sign-off from the accountable executive and fix the date of the next run | Signed record | Accountable executive |

## B.9 AI Contract Clause Checklist

For contracts with suppliers of AI models, systems or services (Chapters 5 and 7). The clauses answer LEG-12, "Contracts that leave the organisation holding the vendor's risk", and the controls of A.10.2 and A.10.3.

| # | Clause | What it should cover | Register lines | Hooks |
|---|---|---|---|---|
| 1 | Notice of changes | Advance notice of model or version changes; the right to pin a version; a deprecation timetable | MOD-05, OPS-05 | A.10.3; Article 25(4) |
| 2 | Documentation | Model card, evaluation results, known limits, instructions for use, and for general-purpose models the training-content summary | TRA-04, DAT-04 | Articles 13, 53(1)(d) |
| 3 | Use of your data | No training on your prompts, outputs or data without agreement; retention limits; deletion on exit | DAT-07, LEG-05 | GDPR Article 5 |
| 4 | Audit and testing | The right to run your own tests and to receive the supplier's test results and incident history | TRA-04, MOD-08 | A.10.3 |
| 5 | Incident notification | A notice period for incidents and malfunctions that is shorter than your own reporting deadlines; cooperation in investigations | Any line | Articles 26(5), 73 |
| 6 | Logs | Access to logs in a usable form, and the retention period | TRA-07 | Articles 12, 26(6); A.6.2.8 |
| 7 | Sub-suppliers | Disclosure of sub-processors and upstream model providers, and notice of changes | OPS-01, SEC-09 | A.10.3; DORA Articles 28 to 30 |
| 8 | Liability and indemnity | Allocation of liability; intellectual property indemnity; limits on caps for data and regulatory loss | LEG-06, LEG-11, LEG-12 | A.10.2 |
| 9 | Service levels | Availability, latency, rate limits, support and fallback | OPS-03 | A.6.2.6 |
| 10 | Price protection | Notice of price changes; spend caps; consumption alerts | OPS-04 | A.4 |
| 11 | Security | Security standards, vulnerability disclosure, data location and transfer terms | SEC-09, SEC-10 | NIS2 Article 21 |
| 12 | Exit and portability | Return of data, migration help, a transition period, and a right to terminate on regulatory change or material change to the model | OPS-02 | A.10.3; DORA Article 28 |
| 13 | Compliance warranties | The supplier's classification of the system, no prohibited practices, conformity and registration where required | LEG-07, LEG-08 | Articles 5, 6, 49 |
| 14 | Oversight support | Instructions, oversight tooling and an explanation capability | HUM-07, TRA-02 | Articles 13, 14, 86 |
| 15 | Fairness evidence | Performance results by group, and the supplier's bias testing method | FAI-04 | A.10.3 |
| 16 | Use restrictions | Intended-use limits, prohibited uses, and the supplier's monitoring of misuse | HUM-03, HUM-04 | A.9.4 |
| 17 | Change of control | Notice and termination rights if the supplier is acquired or changes its terms | OPS-02 | A.10.3 |

## Chapter 15: the Act by role and date (the role-and-date calendar)

The Act applies by role and by date. The table sets out what applies to whom as at 14 October 2026.

| Role | What applies | Articles | Applies from |
|---|---|---|---|
| Any provider or deployer | Prohibited practices; AI literacy | 5; 4 | 2 February 2025 |
| Providers of general-purpose AI models | Documentation, copyright policy, training-content summary; more for systemic-risk models | 53, 55 | 2 August 2025 |
| Providers and deployers of chatbots, synthetic content and deepfakes | Transparency | 50 | 2 August 2026 |
| Providers of high-risk systems in the Annex III areas | Risk management, data governance, documentation, logging, oversight, accuracy; conformity assessment, registration, post-market monitoring, incident reporting | 9 to 15, 17, 43, 49, 72, 73 | 2 December 2027 |
| Deployers of those systems | Use as instructed, oversight, monitoring, logs, notices to workers and affected persons, DPIA; impact assessment for public bodies, public-service providers and credit and life and health insurance pricing | 26, 27, 86 | 2 December 2027 |
| Providers of AI that is, or is a safety component of, an Annex I product | High-risk obligations alongside product law | 6(1) | 2 August 2028 |
| Systems on the market before those dates | Caught only if significantly changed in design; public-authority systems by 2 August 2030 | 111(2) | Not applicable |
