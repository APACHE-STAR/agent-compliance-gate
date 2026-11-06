"""Quickstart: pip install -e . && python examples/quickstart.py"""
from compliance_gate import Draft, Policy, gate, NoHypeReviewer

policy = Policy(
    real_people={"Jane Doe (Founder)"},
    verified_claims={"We make performance apparel."},
    do_not_contact={"competitor-chain-a"},
    allowed_sender_domains={"yourbrand.com"},
    known_partners={"Trail Running Collective"},
)

bad = Draft(sender="someone@gmail.com", recipient_org="Competitor-Chain-A Fitness",
            body="We partnered with a famous brand. The best deal, guaranteed!\n\nBest,\nMark Fakeman")
good = Draft(sender="partners@yourbrand.com", recipient_org="An Independent Studio",
             signature_names=["Jane Doe (Founder)"], claims=["We make performance apparel."],
             body="We make performance apparel and would value a conversation.\n\nBest,\nJane Doe",
             # caller-side checks: your pipeline confirms these, never the drafter
             offers_preapproved=True, has_legal_footer=True, subject_truthful=True)

for label, draft in (("BAD ", bad), ("GOOD", good)):
    verdict = gate(draft, policy, reviewers=[NoHypeReviewer()])
    print(f"{label}: {verdict.verdict}")
    for reason in verdict.reasons:
        print(f"      - {reason}")
