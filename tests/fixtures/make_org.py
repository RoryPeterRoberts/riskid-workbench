"""Build the shared fixture organisation (PLAN.md section 4, round 3).

The fixture organisation is three systems standing in for a realistic
portfolio:

* a **credit-scoring model** the organisation bought and configured, where it
  is the deployer and the Article 6 outcome is high-risk;
* a **customer-service chatbot** it deploys, carrying the Article 50 duty;
* a **CV-screening tool** that is still in pilot well past its end date.

Run as a script, :func:`build_org` writes the fixture to
``tests/fixtures/org.riskid`` (gitignored, for manual use). The pytest suite
builds the same organisation in a temporary directory through the shared
fixture in ``tests/conftest.py`` so later rounds reuse it.

The CV-screening tool deliberately trips the round 2 ``pilot_overdue`` rule:
its ``pilot_end_date`` (2026-06-30) has already passed and its
``lifecycle_stage`` is still ``verification and validation`` — a stage before
deployment. The credit-scoring model and the chatbot sit at
``operation and monitoring`` with no pilot end date, so neither is overdue.
"""

from pathlib import Path

from riskid.model import Event, Organisation, System
from riskid.store import init as _init

# When the fixture was built. The packs load first (init, recorded as
# PACK_TS), then the organisation and its systems are recorded.
PACK_TS = "2026-11-01"
ORG_TS = "2026-11-02"
SYSTEM_TS = "2026-11-02"

ORG = Organisation(
    name="Northwind Analytics Ltd",
    sector="financial services",
    jurisdictions=["EU", "UK"],
    risk_criteria=("material when the inherent likelihood-impact score is 15 "
                   "or more, or the impact is 5; a line the library flags "
                   "material-on-impact-alone (LEG-08) is material whatever the "
                   "likelihood. A practice prohibited by Article 5 is not "
                   "accepted at any score."),
    accountable_executive="Chief Financial Officer",
    ai_officer="Chief AI Officer",
    facilitator="AI Risk Facilitator",
)

SYSTEMS = (
    System(
        id="SYS-001",
        name="Credit-scoring model",
        function="score loan applicants for creditworthiness",
        vendor_or_built="bought and configured",
        supplier="Meridian Financial Systems",
        role_under_act="deployer",
        article_6_outcome="high-risk",
        article_6_record_ref="AIA-2026-014",
        owner="Head of Lending",
        model_owner="Data Science Team",
        lifecycle_stage="operation and monitoring",
        jurisdictions=["EU", "UK"],
    ),
    System(
        id="SYS-002",
        name="Customer-service chatbot",
        function="answer customer service queries and draft replies",
        vendor_or_built="bought",
        supplier="Helix Conversations",
        model_provider="OpenAI",
        model_name="gpt-4o",
        role_under_act="deployer",
        article_50_duty="yes",
        owner="Customer Experience Lead",
        lifecycle_stage="operation and monitoring",
        jurisdictions=["EU", "UK"],
    ),
    System(
        id="SYS-003",
        name="CV-screening tool",
        function="rank candidates against a job description",
        vendor_or_built="bought",
        supplier="TalentGraph",
        role_under_act="deployer",
        owner="Head of Talent Acquisition",
        lifecycle_stage="verification and validation",
        pilot_end_date="2026-06-30",
        jurisdictions=["EU"],
    ),
)


def build_org(path: str | Path):
    """Build the fixture organisation at ``path`` and return its open store.

    The store is created with the data packs loaded (``riskid init``), then
    the organisation and its three systems are appended as events.
    """
    store = _init(path, when=PACK_TS)
    store.append(Event(
        timestamp=ORG_TS, actor="fixture", entity="organisation",
        entity_id="organisation", new=ORG.to_dict(),
        reason="fixture organisation",
    ))
    for system in SYSTEMS:
        store.append(Event(
            timestamp=SYSTEM_TS, actor="fixture", entity="system",
            entity_id=system.id, new=system.to_dict(),
            reason="fixture system",
        ))
    return store


if __name__ == "__main__":
    target = Path(__file__).parent / "org.riskid"
    build_org(target)
    print(f"wrote {target}")
