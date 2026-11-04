"""The Principal AI Risk Report: chapter 12's twelve items on one page, read off the register.

"It is a presentation layer over the register and not a separate analysis"
(chapter 12). Items whose source is the Cycle's indicator sheet, incident log
or calendar say so until those are recorded.
"""

from __future__ import annotations

from collections import Counter

from riskid.assess import latest_assessments
from riskid.interact import concentration
from riskid.register import assessments_of, trend

LATER = "recorded with the Cycle's indicator sheet, trigger log and calendar"


def build(state: dict, library: dict, events: list, last_report_at: str | None) -> list:
    """``[(n, item, [statements], source)]`` for the twelve items."""
    register = state.get("register", {})
    live = {i: l for i, l in register.items() if l.get("status") != "retired"}
    systems = state.get("system", {})
    latest = latest_assessments(state)
    material = sorted(i for i in live if latest.get(i, (None, {}))[1].get("material"))

    def title(i):
        return library[i].title if i in library else (register[i].get("definition") or "")

    classes = Counter(s.get("article_6_outcome") or "not classified" for s in systems.values())
    discovery = sorted(state.get("discovery", {}).values(), key=lambda d: d["quarter"])
    scope = [f"{n} {cls}" for cls, n in sorted(classes.items())] or ["No systems in the inventory."]
    if discovery:
        d = discovery[-1]
        scope.append(f"Discovery {d['quarter']}: {d['found']} tools found against {d['inventoried']} inventoried.")
    risks = [f"{i} {title(i)}: residual {latest[i][1]['residual']}, dominant {latest[i][1]['dominant_dimension']}, "
             f"trend {trend(assessments_of(state, i))}, owner {live[i].get('owner') or 'not named'}" for i in material]
    persons = []
    for sys_id, s in sorted(systems.items()):
        if any(latest.get(i, (None, {}))[1].get("impact", {}).get("IND", 0) >= 4
               for i, l in live.items() if l.get("system_id") == sys_id):
            ia = s.get("impact_assessments") or {}
            persons.append(f"{sys_id} {s.get('name')}: DPIA {ia.get('DPIA', {}).get('date') or 'not recorded'}, "
                           f"FRIA {ia.get('FRIA', {}).get('date') or 'not recorded'}")
    accept = [f"{i}: residual {latest[i][1]['residual']}, " + (f"accepted by {latest[i][1]['acceptable_by']}"
                                                               if latest[i][1].get("acceptable") == "yes"
                                                               else "not accepted")
              for i in material if latest[i][1].get("residual", 0) >= 10]
    conc = concentration(systems, register)
    top = conc["provider"][0] if conc["provider"] else None
    quality = Counter(latest[i][1].get("data_quality") for i in material)
    movement = []
    for e in events:
        if e["entity"] == "register" and (last_report_at is None or e["ts"] > last_report_at):
            if e["field"] is None:
                movement.append(f"{e['entity_id']} added ({e['reason']})")
            elif e["field"] == "status" and '"retired"' in (e["new"] or ""):
                movement.append(f"{e['entity_id']} retired ({e['reason']})")
    decisions = [f"Accept or treat the residual of {i}" for i in material
                 if latest[i][1].get("acceptable") != "yes" and latest[i][1].get("residual", 0) >= 10]
    decisions += [f"Disagreement {k} on {d['line_id']} ({d['dimension']})"
                  for k, d in sorted(state.get("disagreement", {}).items()) if d.get("status") == "open"]
    return [
        (1, "Scope", scope, "System inventory; OPS-07 indicator"),
        (2, "Material risks", risks or ["No material lines."], "Risk ID, owner, residual score, trend"),
        (3, "Persons affected", persons or ["No system has harm to individuals at 4 or 5."],
         "Persons affected; inherent score; assessment dates"),
        (4, "Acceptance", accept or ["No material line has a residual of 10 or more."], "Residual score; audit trail"),
        (5, "Incidents and monitoring", [f"Incidents, Article 73 reports and override rates are {LATER}."],
         "Key risk indicators; incident log"),
        (6, "Concentration", [f"{len(top[1])} of {len(systems)} systems on {top[0]}."] if top else
         ["No model provider recorded."], "Indicators for OPS-01, MOD-05 and LEG-12; interaction field"),
        (7, "Change", [f"Changes released without a linked re-assessment are {LATER}."], "OPS-05 indicator"),
        (8, "Evidence quality", [", ".join(f"{q}: {n}" for q, n in sorted(quality.items())) or "No material lines."],
         "Data quality rating"),
        (9, "Calendar", [f"Next legal dates and open obligations are {LATER}."], "Regulatory hooks; LEG-09 indicator"),
        (10, "Movement", movement or ["No lines added or retired since the last report."], "Audit trail"),
        (11, "Process", [f"Lines reviewed on time and overdue actions are {LATER}."], "Review dates; clause 9.2"),
        (12, "Decisions", decisions or ["Nothing for the board to decide this period."], "Items 2 to 11"),
    ]
