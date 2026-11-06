"""Regression tests for the fail-open probes measured against v0.1.0.

Every test here returned APPROVED (or crashed) on v0.1.0 although the draft
must be REJECTED. They stay as a permanent guard against reopening a hole.
"""

import compliance_gate
from compliance_gate import Draft, Policy, gate, NoHypeReviewer, ReviewResult

POLICY = Policy(
    real_people={"Jane Doe (Founder)"},
    verified_claims={"We make performance apparel."},
    do_not_contact={"competitor-chain-a"},
    allowed_sender_domains={"yourbrand.com"},
    known_partners={"Trail Running Collective"},
    forbidden_patterns={"limited time only"},
)


def _confirmed(**kw):
    """A clean draft whose caller-side checks were all confirmed."""
    base = dict(
        sender="partners@yourbrand.com",
        recipient_org="An Independent Studio",
        signature_names=["Jane Doe (Founder)"],
        claims=["We make performance apparel."],
        body="We make performance apparel and would value a conversation.",
        offers_preapproved=True,
        has_legal_footer=True,
        subject_truthful=True,
    )
    base.update(kw)
    return Draft(**base)


def _rejected(draft, policy=POLICY, reviewers=None):
    v = gate(draft, policy, reviewers=reviewers)
    assert v.verdict == "REJECTED", v
    assert v.may_send is False
    return v


# 1. Missing sender must reject (v0.1.0 skipped the domain check).


def test_probe1_empty_sender_rejects():
    _rejected(_confirmed(sender=""))


def test_probe1_sender_without_at_rejects():
    _rejected(_confirmed(sender="yourbrand.com"))


def test_probe1_sender_with_two_ats_rejects():
    _rejected(_confirmed(sender="x@evil.com@yourbrand.com"))


# 2. The body is scanned, not only the self-declared fields.


def test_probe2_partnership_in_body_only_rejects():
    v = _rejected(_confirmed(body="We partnered with Nike on our last collection."))
    assert any("partner" in r for r in v.reasons)


def test_probe2_invented_signer_in_body_rejects():
    v = _rejected(
        _confirmed(body="Would you be open to a call?\n\nBest,\nMark Fakeman")
    )
    assert any("Mark Fakeman" in r for r in v.reasons)


def test_probe2_forbidden_pattern_in_body_rejects():
    _rejected(_confirmed(body="Limited time only: 50% off for studios."))


# 3. do_not_contact is case-insensitive on both sides.


def test_probe3_do_not_contact_mixed_case_policy_entry():
    policy = Policy(**{**POLICY.__dict__, "do_not_contact": {"Competitor-Chain-A"}})
    _rejected(_confirmed(recipient_org="competitor-chain-a fitness"), policy)


# 4. A reviewer that raises must reject, not crash the gate.


class _Broken:
    def review(self, draft):
        raise TimeoutError("model did not answer")


def test_probe4_reviewer_exception_rejects_with_reason():
    v = _rejected(_confirmed(), reviewers=[_Broken()])
    assert any("TimeoutError" in r for r in v.reasons)


# 5. Caller-side checks default to unknown, and unknown rejects.


def test_probe5_unconfirmed_flags_reject():
    d = Draft(
        sender="partners@yourbrand.com",
        recipient_org="An Independent Studio",
        signature_names=["Jane Doe (Founder)"],
        claims=["We make performance apparel."],
        body="We make performance apparel.",
    )
    v = _rejected(d)
    assert len(v.reasons) == 3


# 6. Example reviewers ship with the package.


def test_probe6_supplement_reviewer_blocks_disease_claim():
    from compliance_gate import SupplementClaimsReviewer

    _rejected(
        _confirmed(body="Our greens powder helps prevent colds."),
        reviewers=[SupplementClaimsReviewer()],
    )


def test_probe6_llm_reviewer_fails_closed_without_model():
    from compliance_gate import LLMReviewer

    def no_model(prompt):
        raise RuntimeError("no API key configured")

    _rejected(_confirmed(), reviewers=[LLMReviewer(no_model)])


# 7. All reasons are collected, not only the first failing stage.


def test_probe7_collects_reasons_from_all_stages():
    d = _confirmed(
        sender="someone@gmail.com",
        signature_names=["Ghost Writer"],
        body="The best deal you will ever see.",
    )
    v = _rejected(d, reviewers=[NoHypeReviewer()])
    joined = " | ".join(v.reasons)
    assert "sender" in joined
    assert "Ghost Writer" in joined
    assert "'best'" in joined


def test_version_is_0_2_0():
    assert compliance_gate.__version__ == "0.2.0"
