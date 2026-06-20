"""
agent-compliance-gate — a minimal, framework-agnostic gate for AI agents.

Drafting and sending are SEPARATE. A draft never ships unless this gate
passes. Hard blockers reject outright; honesty is not negotiable.

This is an illustrative sketch — wire in your own source-of-truth,
blocklist, and allowed senders. The placeholder data below is fake.
"""

from dataclasses import dataclass, field

# --- Your source of truth (load from your DB / knowledge base) ---
REAL_PEOPLE = {"Jane Doe (Founder)"}  # who may actually sign messages
VERIFIED_CLAIMS = {"We make performance apparel."}  # only claims you can prove
DO_NOT_CONTACT = {"competitor-chain-a", "competitor-chain-b"}  # blocklist
ALLOWED_SENDER_DOMAINS = {"yourbrand.com"}


@dataclass
class Draft:
    sender: str  # e.g. "partners@yourbrand.com"
    recipient_org: str
    signature_names: list = field(default_factory=list)
    claims: list = field(default_factory=list)
    offers_preapproved: bool = True
    has_legal_footer: bool = True
    subject_truthful: bool = True


def hard_blockers(d: Draft) -> list:
    """Return a list of blocker reasons. Empty list = no hard blockers."""
    fails = []
    for name in d.signature_names:
        if name not in REAL_PEOPLE:
            fails.append(f"invented person in signature: {name!r}")
    for claim in d.claims:
        if claim not in VERIFIED_CLAIMS:
            fails.append(f"unverifiable claim: {claim!r}")
    if any(b in d.recipient_org.lower() for b in DO_NOT_CONTACT):
        fails.append(f"recipient on do-not-contact list: {d.recipient_org!r}")
    if d.sender.split("@")[-1] not in ALLOWED_SENDER_DOMAINS:
        fails.append(f"disallowed sender domain: {d.sender!r}")
    if not d.offers_preapproved:
        fails.append("offer/terms not pre-approved")
    if not d.has_legal_footer:
        fails.append("missing legal footer (e.g. CAN-SPAM)")
    if not d.subject_truthful:
        fails.append("misleading subject line")
    return fails


def gate(d: Draft) -> dict:
    """Decide whether a draft may proceed. When in doubt, block."""
    fails = hard_blockers(d)
    if fails:
        return {"verdict": "REJECTED", "reasons": fails, "may_send": False}
    # ... optional scoring step (honesty / brand / personalization / legal) ...
    # Approve only on a high bar, then require human approval before sending.
    return {
        "verdict": "APPROVED",
        "reasons": [],
        "may_send": False,
        "next": "await human approval, then send",
    }


if __name__ == "__main__":
    bad = Draft(
        sender="someone@gmail.com",
        recipient_org="Competitor-Chain-A Fitness",
        signature_names=["A Person Who Does Not Exist"],
        claims=["We are featured at a brand we never worked with."],
    )
    print(gate(bad))

    good = Draft(
        sender="partners@yourbrand.com",
        recipient_org="An Independent Local Studio",
        signature_names=["Jane Doe (Founder)"],
        claims=["We make performance apparel."],
    )
    print(gate(good))
