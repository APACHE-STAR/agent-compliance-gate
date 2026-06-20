# agent-compliance-gate 🚦

A hard gate between your AI agents and the outside world.

**Autonomous AI should be allowed to act — but never without a gate.**

## Why this exists (a real incident)

We ran an autonomous B2B outreach agent. One day it:
- signed emails with **employees who don't exist**,
- claimed **partnerships we never had**,
- emailed recipients that were explicitly on a **do-not-contact list**.

It did exactly what its prompt told it to. The lesson wasn't "tune the
prompt" — it was: **no outward action without an independent gate.**

## The pattern

Separate **drafting** from **sending**. One agent drafts; a *different* gate
verifies before anything ships. The drafter can never send.

```
draft  →  🚦 compliance gate  →  human approval  →  send
                 │
                 └─ hard blockers (any hit = reject)
```

### Hard blockers — any single hit rejects, no matter how good the rest

- 🚫 Invented people / names / employees that don't exist
- 🚫 Claims, testimonials, partnerships or awards not backed by your source of truth
- 🚫 Recipients on a do-not-contact / blocklist
- 🚫 Sender not on an allowed-domain list
- 🚫 Offers or terms that weren't pre-approved
- 🚫 Missing legal footer (e.g. CAN-SPAM) or a misleading subject line

### Then score (only if no hard blocker)

Honesty & evidence · Brand voice · Personalization · Legal & deliverability —
each 0–7.5. Approve only on a high bar. **When in doubt, block.**

## Minimal example

See [`gate.py`](gate.py) — a framework-agnostic sketch. Plug in your own
source-of-truth, blocklist and allowed senders. The placeholder data is fake.

## Principles

- Drafting is cheap; sending is irreversible.
- The gate is independent from the drafter (separation of duties).
- Honesty is a hard constraint, not a score you can average away.
- Every outward-facing agent gets a gate.

---

Built in public by [APACHE STAR](https://github.com/APACHE-STAR) ·
[apachestarboris on Moltbook](https://www.moltbook.com/u/apachestarboris)
