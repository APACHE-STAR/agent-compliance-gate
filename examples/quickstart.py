"""Quickstart: pip install -e . && python examples/quickstart.py"""
from compliance_gate import Draft, Policy, gate, NoHypeReviewer

policy = Policy(
    real_people={"Jane Doe (Founder)"},
    verified_claims={"We make performance apparel."},
    do_not_contact={"competitor-chain-a"},
    allowed_sender_domains={"yourbrand.com"},
)

bad = Draft(sender="someone@gmail.com", recipient_org="Competitor-Chain-A Fitness",
            signature_names=["A Person Who Does Not Exist"], body="The best deal, guaranteed!")
good = Draft(sender="partners@yourbrand.com", recipient_org="An Independent Studio",
             signature_names=["Jane Doe (Founder)"], claims=["We make performance apparel."],
             body="We make performance apparel and would value a conversation.")

print("BAD :", gate(bad, policy, reviewers=[NoHypeReviewer()]))
print("GOOD:", gate(good, policy, reviewers=[NoHypeReviewer()]))
