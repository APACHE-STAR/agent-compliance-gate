"""agent-compliance-gate — a hard gate between your AI agents and the outside world.

Drafting and sending are SEPARATE. A draft never ships unless this gate passes.
Hard blockers reject outright; honesty is a constraint, not a score.
"""
from .gate import Draft, Policy, Verdict, hard_blockers, gate
from .reviewers import Reviewer, ReviewResult, NoHypeReviewer

__all__ = [
    "Draft", "Policy", "Verdict", "hard_blockers", "gate",
    "Reviewer", "ReviewResult", "NoHypeReviewer",
]
__version__ = "0.1.0"
