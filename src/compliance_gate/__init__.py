"""agent-compliance-gate — a hard gate between your AI agents and the outside world.

Drafting and sending are SEPARATE. A draft never ships unless this gate passes.
Hard blockers reject outright; honesty is a constraint, not a score.
"""
from .gate import Draft, Policy, Verdict, hard_blockers, gate, signature_lines
from .reviewers import Reviewer, ReviewResult, NoHypeReviewer, SupplementClaimsReviewer, LLMReviewer

__all__ = [
    "Draft", "Policy", "Verdict", "hard_blockers", "gate", "signature_lines",
    "Reviewer", "ReviewResult", "NoHypeReviewer", "SupplementClaimsReviewer", "LLMReviewer",
]
__version__ = "0.2.0"
