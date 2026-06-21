"""Deterministic eval suite — runs in CI, no API key needed.
Proves the gate blocks what it must and approves only clean drafts."""
from compliance_gate import Draft, Policy, gate, NoHypeReviewer

POLICY = Policy(
    real_people={"Jane Doe (Founder)"},
    verified_claims={"We make performance apparel."},
    do_not_contact={"competitor-chain-a"},
    allowed_sender_domains={"yourbrand.com"},
)


def _clean(**kw):
    base = dict(sender="partners@yourbrand.com", recipient_org="An Independent Studio",
                signature_names=["Jane Doe (Founder)"], claims=["We make performance apparel."])
    base.update(kw)
    return Draft(**base)


def test_blocks_invented_person():
    assert gate(_clean(signature_names=["A Person Who Does Not Exist"]), POLICY).verdict == "REJECTED"


def test_blocks_unverified_claim():
    assert gate(_clean(claims=["Featured at a brand we never worked with."]), POLICY).verdict == "REJECTED"


def test_blocks_do_not_contact():
    assert gate(_clean(recipient_org="Competitor-Chain-A Fitness"), POLICY).verdict == "REJECTED"


def test_blocks_bad_sender_domain():
    assert gate(_clean(sender="someone@gmail.com"), POLICY).verdict == "REJECTED"


def test_blocks_missing_legal_footer():
    assert gate(_clean(has_legal_footer=False), POLICY).verdict == "REJECTED"


def test_approves_clean_draft():
    assert gate(_clean(), POLICY).verdict == "APPROVED"


def test_reviewer_blocks_hype():
    d = _clean(body="We're the best, #1, revolutionary solution, guaranteed!")
    assert gate(d, POLICY, reviewers=[NoHypeReviewer()]).verdict == "REJECTED"


def test_reviewer_passes_clean_body():
    d = _clean(body="We make performance apparel and would value a conversation.")
    assert gate(d, POLICY, reviewers=[NoHypeReviewer()]).verdict == "APPROVED"
