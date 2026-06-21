"""The gate itself: deterministic hard blockers + optional independent reviewers."""
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Policy:
    """Your source of truth. Load from your DB / knowledge base."""
    real_people: set = field(default_factory=set)            # who may sign messages
    verified_claims: set = field(default_factory=set)        # claims you can prove
    do_not_contact: set = field(default_factory=set)         # blocklist (lowercase)
    allowed_sender_domains: set = field(default_factory=set)


@dataclass
class Draft:
    body: str = ""
    sender: str = ""
    recipient_org: str = ""
    signature_names: List[str] = field(default_factory=list)
    claims: List[str] = field(default_factory=list)
    offers_preapproved: bool = True
    has_legal_footer: bool = True
    subject_truthful: bool = True


@dataclass
class Verdict:
    verdict: str            # "REJECTED" | "APPROVED"
    reasons: List[str]
    may_send: bool
    next: Optional[str] = None


def hard_blockers(draft: Draft, policy: Policy) -> List[str]:
    """Return blocker reasons. Empty list = no hard blockers. Any hit rejects."""
    fails: List[str] = []
    for name in draft.signature_names:
        if name not in policy.real_people:
            fails.append(f"invented person in signature: {name!r}")
    for claim in draft.claims:
        if claim not in policy.verified_claims:
            fails.append(f"unverifiable claim: {claim!r}")
    org = draft.recipient_org.lower()
    if any(b in org for b in policy.do_not_contact):
        fails.append(f"recipient on do-not-contact list: {draft.recipient_org!r}")
    if draft.sender and draft.sender.split("@")[-1] not in policy.allowed_sender_domains:
        fails.append(f"disallowed sender domain: {draft.sender!r}")
    if not draft.offers_preapproved:
        fails.append("offer/terms not pre-approved")
    if not draft.has_legal_footer:
        fails.append("missing legal footer (e.g. CAN-SPAM)")
    if not draft.subject_truthful:
        fails.append("misleading subject line")
    return fails


def gate(draft: Draft, policy: Policy, reviewers=None) -> Verdict:
    """Decide whether a draft may proceed. When in doubt, block.

    1. Deterministic hard blockers (any hit -> REJECTED).
    2. Optional independent reviewers (e.g. an LLM truth/voice check).
    3. APPROVED never means "send" — it means "await human approval, then send".
    """
    fails = hard_blockers(draft, policy)
    if fails:
        return Verdict("REJECTED", fails, may_send=False)
    for reviewer in (reviewers or []):
        result = reviewer.review(draft)
        if not result.ok:
            return Verdict("REJECTED", list(result.reasons), may_send=False)
    return Verdict("APPROVED", [], may_send=False, next="await human approval, then send")
