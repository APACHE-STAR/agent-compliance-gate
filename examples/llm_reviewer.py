"""LLM reviewer example: wire any model into the gate, fail-closed.

    pip install anthropic          # only for this example; the library has no dependencies
    export ANTHROPIC_API_KEY=...   # never commit a key
    python examples/llm_reviewer.py

Without a key (or without the SDK, on a timeout, a refusal or an odd answer)
the reviewer raises or answers badly, and the gate REJECTS. That is the point:
a reviewer that cannot review must never wave a draft through.
"""
import os

from compliance_gate import Draft, LLMReviewer, Policy, gate


def claude_complete(prompt: str) -> str:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError("ANTHROPIC_API_KEY not set")
    import anthropic  # imported lazily so the package itself stays dependency-free

    client = anthropic.Anthropic(timeout=60.0)
    response = client.messages.create(
        model="claude-opus-5-5",
        max_tokens=16000,
        output_config={"effort": "low"},
        messages=[{"role": "user", "content": prompt}],
    )
    if response.stop_reason != "end_turn":  # refusal, max_tokens, ...: no verdict
        raise RuntimeError(f"no usable answer (stop_reason={response.stop_reason})")
    return "".join(block.text for block in response.content if block.type == "text")


reviewer = LLMReviewer(claude_complete)

policy = Policy(
    real_people={"Jane Doe (Founder)"},
    verified_claims={"We make performance apparel."},
    allowed_sender_domains={"yourbrand.com"},
)

draft = Draft(
    sender="partners@yourbrand.com",
    recipient_org="An Independent Studio",
    body="We make performance apparel and would value a conversation.\n\nBest,\nJane Doe",
    # set by YOUR pipeline after its own checks, never by the drafting model:
    offers_preapproved=True, has_legal_footer=True, subject_truthful=True,
)

if __name__ == "__main__":
    print(gate(draft, policy, reviewers=[reviewer]))
