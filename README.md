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
    do_not_contact={"competitor-chain-a"},       # blocklist, case-insensitive
    allowed_sender_domains={"yourbrand.com"},
    known_partners={"Trail Running Collective"}, # partnerships you can prove
    forbidden_patterns={"limited time only"},    # phrases or compiled regexes
)

draft = Draft(
    sender="partners@yourbrand.com",
    recipient_org="An Independent Studio",
    signature_names=["Jane Doe (Founder)"],
    claims=["We make performance apparel."],
    body="We make performance apparel and would value a conversation.\n\nBest,\nJane Doe",
    # caller-side checks: YOUR pipeline sets these, never the drafting model
    offers_preapproved=True, has_legal_footer=True, subject_truthful=True,
)

verdict = gate(draft, policy, reviewers=[NoHypeReviewer()])
print(verdict.verdict)   # APPROVED | REJECTED
print(verdict.reasons)   # every reason from every stage, empty when approved
# APPROVED never means "send" — it means "await human approval, then send".
```

## Why this exists

An agent that drafts outbound messages will sooner or later draft something
untrue: a signer who doesn't exist, a partnership you never had, a recipient
who asked not to be contacted. A better prompt makes that rarer; it can't rule
it out. Drafting is cheap and reversible; sending is not. So the check belongs
between the two, in code, independent from the drafter.

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

Fail-closed: a field the gate needs but cannot check rejects too.

- 🚫 Invented people: `signature_names`, and any signer found under a sign-off
  line in the body ("Best,\nJane Doe"), must be in `real_people`
- 🚫 Claims not in your source of truth: `claims` must match `verified_claims` exactly
- 🚫 Partnerships, sponsorships, endorsements or awards asserted in the body that
  don't name one of your `known_partners` (quoting a verified claim verbatim is fine)
- 🚫 Anything matching `forbidden_patterns` in the body
- 🚫 Recipient on the do-not-contact list, or `recipient_org` missing
- 🚫 Sender missing, malformed, or not on an allowed domain
- 🚫 Offer/terms, legal footer (e.g. CAN-SPAM) or subject line not confirmed by the caller

### Who sets what

The drafter is the thing you don't trust, so it must not grade itself.

| Field | Set by | If missing |
|---|---|---|
| `body`, `claims`, `signature_names` | drafter | `body` is scanned anyway; an empty `body` is REJECTED |
| `sender`, `recipient_org` | your pipeline | REJECTED |
| `offers_preapproved`, `has_legal_footer`, `subject_truthful` | your pipeline, after its own check (a lookup, a template, a person) | `None` = unknown = REJECTED |
| `Policy` | your source of truth (DB, CRM, legal) | empty `real_people`, `verified_claims`, `known_partners`, `allowed_sender_domains` reject whatever they would have to vouch for; empty `do_not_contact` and `forbidden_patterns` block nothing |

### Independent reviewers (pluggable)

`gate(draft, policy, reviewers=[...])` runs every reviewer after the hard
blockers, and collects all reasons. A reviewer is any object with
`review(draft) -> ReviewResult`. A reviewer that raises, or returns anything
but `ok=True`, rejects the draft with the reason.

- `NoHypeReviewer`: illustrative superlative check (`best`, `#1`, `guaranteed`, ...).
- `SupplementClaimsReviewer`: illustrative word list for supplement disease and
  performance claims, the kind the FTC objects to without substantiation
  ("prevents colds", "burn fat", "clinically proven"). Not legal advice; extend
  it with your counsel's list.
- `LLMReviewer`: wraps any `complete(prompt) -> str` function. The library never
  imports an SDK or reads a key. Only a clean `{"ok": true}` JSON answer passes;
  an exception, a refusal, non-JSON, or `ok: true` with reasons all reject.

```python
from compliance_gate import LLMReviewer

def complete(prompt: str) -> str:
    ...  # call your model, return its text; raise on any failure

verdict = gate(draft, policy, reviewers=[LLMReviewer(complete)])
```

`examples/llm_reviewer.py` wires this to Claude via the Anthropic SDK. Without
`ANTHROPIC_API_KEY` it rejects, which is the intended behavior.

## Limits (read this before you rely on it)

The deterministic checks are deliberately simple, so you can audit them. They
are a floor, not a proof of honesty.

- **Body scanning is pattern-based.** A partnership claim without one of the
  cue phrases ("partnered with", "sponsored by", "featured in", ...) is not
  caught, and a cue sentence passes as soon as it names one known partner,
  even if it also names an unknown one.
- **Signatures are found only under a sign-off line** (`Best,`, `Regards,`,
  `Thanks!`, `--`, ...). The line after a bare sign-off counts as a signer
  unless it reads like prose (common words like "you" or "the", more than
  eight words, ending in `.`/`?`/`!`). A name on the sign-off line itself
  ("Cheers, Jane") must be capitalized. Company and team signatures are
  signers too, so list the ones you use in `real_people`. Declare signers in
  `signature_names` as well.
- **Only a sentence that IS a verified claim is exempt** from the partnership
  check. A verified claim embedded in a longer sentence is checked like any
  other text (fail-closed).
- **Word lists miss paraphrases and flag harmless uses** ("prevent spills").
  That's why the LLM reviewer layer and a human approval step exist.
- **`do_not_contact` matches substrings of `recipient_org`.** It does not see
  email addresses; resolve the recipient's organization before you call the gate.
- **The gate never sends.** APPROVED means "a human may now approve it".

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
