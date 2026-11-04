"""Proposing library lines for a system: chapter 5's straw man (SPEC.md 6.3, PLAN.md round 5).

"To cut it down, filter the lines by the system's role, lifecycle stage,
persons affected and classification ... Record the reason for every line you
remove" (chapter 5). :func:`screen_lines` sorts the 91 library lines into the
ones proposed for a system and the ones removed, each with its reasons:

- **Role.** A provider's line is removed for a pure deployer, and a deployer's
  line for a pure provider; lines for both roles, or for an external threat,
  stay. An unrecorded role removes nothing.
- **Stage.** A line whose lifecycle stages include the system's stage (or "all
  stages") is proposed. An unrecorded stage removes nothing.
- **Regulatory hooks.** The articles the system's classification, role,
  purchase and data engage (:func:`engaged_hooks`) are matched against the
  articles each line cites (:func:`line_hooks`, the Harness's lookup). A line
  outside the system's stage is still proposed when it cites an engaged
  article.
- **Persons affected.** Recorded groups add a reason to lines that harm
  people; an unrecorded list removes nothing (unknown is not none).

A proposal is a prompt to be challenged, not the system's risk list.
"""

from __future__ import annotations

import re

from riskid import importers
from riskid.model import LibraryLine, RegisterLine

AI_ACT = "AI Act"
GDPR = "GDPR"
_INSTRUMENTS = (AI_ACT, GDPR)

_HIGH_RISK = ("high-risk: Annex I", "high-risk: Annex III")
_PEOPLE = ("individuals", "customers", "groups", "society", "supply-chain workers")

# Articles a high-risk classification engages, by role (Regulation (EU) 2024/1689).
_PROVIDER_ARTICLES = (9, 10, 11, 12, 13, 14, 15, 16, 17, 43, 47, 48, 49, 72, 73)
_DEPLOYER_ARTICLES = (13, 14, 26, 27, 73, 86)

_ART = re.compile(r"\bArt(?:icle)?s?\.?\s*$")
_ARTICLE_NUMBER = re.compile(r"\s*(?:Art(?:icle)?s?\.?\s*)?([0-9]+)")
_ANNEX_A = re.compile(r"\bA\.[0-9]+(?:\.[0-9]+)*")


def _field(obj, name):
    if isinstance(obj, dict):
        return obj.get(name)
    return getattr(obj, name, None)


def _split(text) -> list:
    return [part.strip() for part in (text or "").split(";") if part.strip()]


def line_hooks(line) -> set:
    """The (instrument, article) pairs a library line's ``reg`` column cites.

    ``"GDPR Art 5(1)(b), 6, 14; AI Act Art 10(2)(b), 53(1)(c); EDPB Opinion
    28/2024"`` gives GDPR 5, 6 and 14 and AI Act 10 and 53. A segment that
    starts with "Art" keeps the instrument of the segment before it; a segment
    with no "Art" (a sector rule, an opinion, contract law) cites no article.
    """
    hooks = set()
    instrument = None
    for segment in _split(_field(line, "reg")):
        at = segment.find("Art")
        if at < 0:
            instrument = None
            continue
        named = segment[:at].strip()
        if named:
            # "AI Act Annex III(4), Art 10" names the AI Act; keep the instrument only.
            instrument = next((i for i in _INSTRUMENTS if named.startswith(i)), named.rstrip(" ,"))
        if instrument is None:
            continue
        for item in segment[at:].split(","):
            match = _ARTICLE_NUMBER.match(item.strip())
            if match:
                hooks.add((instrument, int(match.group(1))))
    return hooks


def engaged_hooks(system) -> dict:
    """The articles a system engages, as ``{(instrument, article or None): [why, ...]}``.

    ``None`` as the article means every article of the instrument (personal
    data engages the GDPR as a whole). A system classified out of scope of the
    Act engages nothing under it.
    """
    hooks: dict = {}

    def add(instrument, articles, why):
        for article in articles:
            hooks.setdefault((instrument, article), []).append(why)

    outcome = _field(system, "article_6_outcome")
    role = _field(system, "role_under_act")
    bought = _field(system, "vendor_or_built")
    if outcome != "out of scope":
        # Unrecorded is not out of scope: an unclassified system is LEG-07's concern.
        add(AI_ACT, (4,), "AI literacy applies to every AI system")
        add(AI_ACT, (6,), "the system's Article 6 classification" if outcome
            else "no Article 6 classification is recorded for the system")
    if outcome == "prohibited":
        add(AI_ACT, (5,), "classified as a prohibited practice")
    if outcome in _HIGH_RISK:
        if role in ("provider", "both"):
            add(AI_ACT, _PROVIDER_ARTICLES, "a provider of a high-risk system")
        if role in ("deployer", "both"):
            add(AI_ACT, _DEPLOYER_ARTICLES, "a deployer of a high-risk system")
    if outcome == "not high-risk: Article 6(3)":
        add(AI_ACT, (6, 49), "the Article 6(3) exception is documented and registered")
    if outcome and outcome != "out of scope" and (role == "both" or bought == "bought and configured"):
        add(AI_ACT, (25,), "configuring or repurposing a system can make its deployer the provider")
    if outcome != "out of scope" and bought in ("bought", "bought and configured"):
        add(AI_ACT, (13, 25, 53), "the system is bought, so its documentation comes from the supplier")
    duty = (_field(system, "article_50_duty") or "").strip().lower()
    if outcome != "out of scope" and duty and duty not in ("no", "none", "n/a"):
        add(AI_ACT, (50,), "an Article 50 transparency duty is recorded")
    data = _field(system, "data") or {}
    if data.get("personal"):
        add(GDPR, (None,), "the system processes personal data")
    if data.get("special_category"):
        add(GDPR, (9,), "the system processes special-category data")
    return hooks


def _role_reason(line_role, system_role):
    """(keep, reason) for the role test."""
    if line_role == "provider" and system_role == "deployer":
        return False, "removed: a provider's concern; the system's role is deployer"
    if line_role == "deployer" and system_role == "provider":
        return False, "removed: a deployer's concern; the system's role is provider"
    if not system_role:
        return True, "role: not recorded for the system, so no line is removed for it"
    if line_role == "both":
        return True, "role: the line applies to providers and deployers"
    if line_role and line_role.startswith("none"):
        return True, "role: an external threat, whatever the role"
    return True, f"role: {line_role}"


def screen_lines(system, lines=None) -> tuple[list, list]:
    """Sort the library into ``(proposed, removed)``, each a list of ``(line, reasons)``."""
    lines = importers.load_library() if lines is None else lines
    stage = _field(system, "lifecycle_stage")
    role = _field(system, "role_under_act")
    engaged = engaged_hooks(system)
    groups = [p.get("group") for p in (_field(system, "persons_affected") or [])
              if isinstance(p, dict) and p.get("group")]
    proposed, removed = [], []
    for line in lines:
        keep_role, role_reason = _role_reason(line.role, role)
        if not keep_role:
            removed.append((line, [role_reason]))
            continue
        stages = _split(line.lifecycle)
        hook_reasons = []
        for instrument, article in sorted(line_hooks(line)):
            why = engaged.get((instrument, article)) or engaged.get((instrument, None))
            if why:
                hook_reasons.append(f"{instrument} Art {article}: {'; '.join(why)}")
        if not stage:
            stage_reason = "stage: not recorded for the system, so no line is removed for it"
        elif stage in stages or "all stages" in stages:
            stage_reason = f"stage: the line covers {stage}"
        else:
            stage_reason = None
        if stage_reason is None and not hook_reasons:
            removed.append((line, [f"removed: the line covers {', '.join(stages)}; the system is "
                                   f"at {stage}, and none of the articles it cites is engaged"]))
            continue
        reasons = ([stage_reason] if stage_reason else []) + [role_reason] + hook_reasons
        if groups and any(h.lower() in _PEOPLE for h in _split(line.harmed)):
            reasons.append(f"persons affected: {', '.join(groups)}")
        proposed.append((line, reasons))
    return proposed, removed


def propose_lines(system, lines=None) -> list:
    """The library lines proposed for ``system``, each with its reasons (PLAN.md round 5)."""
    return screen_lines(system, lines)[0]


def annex_a_refs(text) -> list:
    """The ISO/IEC 42001 Annex A control references in a text, in order, once each."""
    seen = []
    for ref in _ANNEX_A.findall(text or ""):
        if ref not in seen:
            seen.append(ref)
    return seen


def register_line_from_library(line: LibraryLine, system_id: str) -> RegisterLine:
    """Adopt a library line for a system: a candidate register line that keeps its ID.

    Nothing is scored on adoption (SPEC.md section 3, day one). The owner is
    left empty because B.3 asks for a named person, never a role; the library's
    owner role is shown beside the line instead.
    """
    return RegisterLine(
        id=line.id, system_id=system_id, l1=line.l1, l2=line.l2,
        definition=line.description, status="candidate", source="library", trend="new",
        lifecycle_stages=_split(line.lifecycle), role=line.role,
        persons_affected=_split(line.harmed), regulatory_hooks=_split(line.reg),
        annex_a_controls=annex_a_refs(line.controls),
    )
