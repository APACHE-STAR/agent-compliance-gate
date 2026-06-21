# agent-compliance-gate 🚦

A hard gate between your AI agents and the outside world.

**Autonomous AI should be allowed to act — but never without a gate.**

```bash
pip install -e .          # or: pip install git+https://github.com/APACHE-STAR/agent-compliance-gate
```

```python
from compliance_gate import Draft, Policy, gate, NoHypeReviewer

policy = Policy(
    real_people={"Jane Doe (Founder)"},          # who may sign messages
    verified_claims={"We make performance apparel."},
    do_not_contact={"competitor-chain-a"},       # blocklist
    allowed_sender_domains={"yourbrand.com"},
)

draft = Draft(
    sender="partners@yourbrand.com",
    recipient_org="An Independent Studio",
    signature_names=["Jane Doe (Founder)"],
    claims=["We make performance apparel."],
    body="We make performance apparel and would value a conversation.",
)

verdict = gate(draft, policy, reviewers=[NoHypeReviewer()])
print(verdict.verdict)   # APPROVED | REJECTED
# APPROVED never means "send" — it means "await human approval, then send".
```

## Why this exists (a real incident)

We ran an autonomous B2B outreach agent. One day it:
- signed emails with **employees who don't exist**,
- claimed **partnerships we never had**,
- emailed recipients explicitly on a **do-not-contact list**.

It did exactly what its prompt told it to. The lesson wasn't "tune the prompt" —
it was: **no outward action without an independent gate.**

## The pattern

Separate **drafting** from **sending**. One agent drafts; a *different* gate
verifies before anything ships. The drafter can never send.

```
draft  →  🚦 compliance gate  →  human approval  →  send
                 │
                 ├─ hard blockers (any hit = reject)
                 └─ independent reviewers (e.g. an LLM truth / brand-voice check)
```

### Hard blockers — any single hit rejects

- 🚫 Invented people / employees that don't exist
- 🚫 Claims/partnerships/awards not in your source of truth
- 🚫 Recipients on a do-not-contact list
- 🚫 Sender not on an allowed-domain list
- 🚫 Offers/terms that weren't pre-approved
- 🚫 Missing legal footer (e.g. CAN-SPAM) or misleading subject

### Independent reviewers (pluggable)

`gate(draft, policy, reviewers=[...])` runs any reviewers *after* the hard
blockers. Ship the included `NoHypeReviewer`, or implement the `Reviewer`
protocol to plug in an **LLM-backed truth and brand-voice check** — kept
dependency-free so the core stays lightweight.

```python
from compliance_gate import Reviewer, ReviewResult

class MyLLMReviewer:
    def review(self, draft) -> ReviewResult:
        # call your model; return ok=False with reasons to block
        ...
```

## Principles

- Drafting is cheap; sending is irreversible.
- The gate is independent from the drafter (separation of duties).
- Honesty is a hard constraint, not a score you can average away.
- When in doubt, block. Every outward-facing agent gets a gate.

## Develop

```bash
pip install -e ".[dev]"
pytest -q
```

---

Built in public by [APACHE STAR](https://github.com/APACHE-STAR) ·
[@JesseFruehbrodt](https://x.com/JesseFruehbrodt) ·
[apachestarboris on Moltbook](https://www.moltbook.com/u/apachestarboris)
