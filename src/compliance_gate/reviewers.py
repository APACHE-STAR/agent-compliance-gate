"""Pluggable independent reviewers. The real value-add (an LLM truth/voice
reviewer) plugs in here — kept dependency-free so the core stays lightweight."""
from dataclasses import dataclass, field
from typing import List

try:
    from typing import Protocol
except ImportError:  # py<3.8
    Protocol = object


@dataclass
class ReviewResult:
    ok: bool
    reasons: List[str] = field(default_factory=list)


class Reviewer(Protocol):
    def review(self, draft) -> "ReviewResult":
        ...


class NoHypeReviewer:
    """Illustrative, dependency-free reviewer that rejects hype/superlatives.
    Swap this for an LLM-backed reviewer (truth + brand voice) in production."""
    HYPE = ("best", "#1", "revolutionary", "guaranteed", "game-changer", "world-class")

    def review(self, draft) -> ReviewResult:
        low = (getattr(draft, "body", "") or "").lower()
        hits = [w for w in self.HYPE if w in low]
        return ReviewResult(ok=not hits, reasons=[f"hype/superlative: {w!r}" for w in hits])
