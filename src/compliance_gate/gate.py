"""The gate itself: deterministic hard blockers + optional independent reviewers.

Fail-closed throughout: a missing field, an unconfirmed caller-side check, a
reviewer that crashes or answers in an unexpected shape all REJECT.
"""
import re
from dataclasses import dataclass, field
from typing import Iterable, List, Optional


@dataclass
class Policy:
    """Your source of truth. Load from your DB / knowledge base.

    Matching is case-insensitive everywhere except ``verified_claims``,
    which must match exactly (a claim is only verified in the wording you verified).
    """
    real_people: set = field(default_factory=set)            # who may sign messages
    verified_claims: set = field(default_factory=set)        # claims you can prove, exact wording
    do_not_contact: set = field(default_factory=set)         # blocklist, substring of recipient_org
    allowed_sender_domains: set = field(default_factory=set)
    known_partners: set = field(default_factory=set)         # orgs you really partner with
    forbidden_patterns: set = field(default_factory=set)     # phrases (str) or compiled regexes


@dataclass
class Draft:
    """What the drafting agent produced, plus what the CALLER confirmed.

    ``offers_preapproved``, ``has_legal_footer`` and ``subject_truthful`` are
    checks your pipeline performs outside the drafter (a lookup, a template,
    a person). They default to ``None`` = unknown, and anything but ``True``
    rejects. Never copy these values from the drafting model's own output.
    """
    body: str = ""
    sender: str = ""
    recipient_org: str = ""
    signature_names: List[str] = field(default_factory=list)
    claims: List[str] = field(default_factory=list)
    offers_preapproved: Optional[bool] = None
    has_legal_footer: Optional[bool] = None
    subject_truthful: Optional[bool] = None


@dataclass
class Verdict:
    verdict: str            # "REJECTED" | "APPROVED"
    reasons: List[str]
    may_send: bool
    next: Optional[str] = None


# Phrases that assert an EXISTING relationship. An invitation ("would you like
# to partner with us?") is deliberately not matched.
_RELATIONSHIP_CUES = re.compile(
    r"\b(?:partnered with|partnering with|in partnership with|our partners?\b"
    r"|official (?:partner|supplier|sponsor)|partner of|sponsored by|endorsed by"
    r"|backed by|featured (?:in|on|by)|as seen (?:in|on)|trusted by|certified by"
    r"|in collaboration with|collaborated with|(?:have|has|we've) worked with"
    r"|award[- ]winning|won (?:an?|the) [\w ]*award)",
    re.IGNORECASE,
)

_SIGNOFF = re.compile(
    r"^\s*(?:best(?: regards| wishes)?|kind regards|warm regards|regards|sincerely"
    r"|cheers|thanks|thank you|many thanks|warmly|all the best|yours(?: truly| sincerely)?"
    r"|respectfully|talk soon)\s*[,.!]*\s*(?P<rest>.*)$",
    re.IGNORECASE,
)
_DASH_SIGNOFF = re.compile(r"^\s*(?:--|—|–)\s*(?P<rest>.*)$")
_NAME_PARTICLES = {"van", "von", "de", "der", "den", "da", "del", "di", "du", "la", "le", "bin", "al"}


def _fold(text) -> str:
    return " ".join(str(text).split()).casefold()


def _mentions(folded_text: str, phrase) -> bool:
    """Case-insensitive whole-phrase match; ``folded_text`` must already be folded."""
    phrase = _fold(phrase)
    if not phrase:
        return False
    return bool(re.search(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", folded_text))


def _person_key(name) -> str:
    """'Jane Doe (Founder)', 'Jane Doe, Founder' and 'jane doe' -> 'jane doe'."""
    name = re.sub(r"\(.*?\)", " ", str(name))
    name = re.split(r",| \| | - ", name)[0]
    return _fold(name).strip(" .")


def _looks_like_name(line: str) -> bool:
    words = re.sub(r"\(.*?\)", " ", line).split(",")[0].split()
    if not 1 <= len(words) <= 5:
        return False
    for w in words:
        if w.casefold() in _NAME_PARTICLES:
            continue
        if not (w[0].isupper() and all(c.isalpha() or c in ".'-" for c in w)):
            return False
    return True


def _signoff_rest(line: str) -> Optional[str]:
    """For a sign-off line, the text after it ("" if none); None for any other line."""
    m = _SIGNOFF.match(line) or _DASH_SIGNOFF.match(line)
    if not m:
        return None
    rest = m.group("rest").strip()
    if "," in rest:
        # "Thanks, Sarah, for your time" addresses the reader, it is no signature.
        return None
    if rest and not _looks_like_name(rest):
        return None  # "Thanks for your note." is prose
    return rest


def signature_lines(body: str) -> List[str]:
    """Names found under a sign-off ("Best,\\nJane Doe", "Thanks, Jane", "-- Jane").

    Deterministic and deliberately narrow: a signer written without a
    recognized sign-off line is NOT found. Declare signers in
    ``Draft.signature_names`` as well; both are checked.
    """
    lines = (body or "").splitlines()
    found = []
    for i, line in enumerate(lines):
        rest = _signoff_rest(line)
        if rest is None:
            continue
        if not rest:
            rest = next((l.strip() for l in lines[i + 1:] if l.strip()), "")
        if rest and _looks_like_name(rest):
            found.append(rest)
    return found


def _sentences(text: str) -> Iterable[str]:
    return (s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", text) if s.strip())


def _body_blockers(draft: Draft, policy: Policy) -> List[str]:
    fails: List[str] = []
    body = draft.body or ""
    folded = _fold(body)

    for pattern in policy.forbidden_patterns:
        if isinstance(pattern, re.Pattern):
            if pattern.search(body):
                fails.append(f"forbidden pattern in body: {pattern.pattern!r}")
        elif _mentions(folded, pattern):
            fails.append(f"forbidden pattern in body: {pattern!r}")

    # Verified claims quoted verbatim are fine; scan what is left.
    rest = body
    for claim in policy.verified_claims:
        if claim:
            rest = rest.replace(claim, " ")
    for sentence in _sentences(rest):
        if not _RELATIONSHIP_CUES.search(sentence):
            continue
        s = _fold(sentence)
        if not any(_mentions(s, partner) for partner in policy.known_partners):
            fails.append(f"partnership/endorsement in body not backed by known_partners: {sentence!r}")

    people = {_person_key(p) for p in policy.real_people}
    for signer in signature_lines(body):
        if _person_key(signer) not in people:
            fails.append(f"invented person in body signature: {signer!r}")
    return fails


def hard_blockers(draft: Draft, policy: Policy) -> List[str]:
    """Return blocker reasons. Empty list = no hard blockers. Any hit rejects."""
    fails: List[str] = []

    people = {_person_key(p) for p in policy.real_people}
    for name in draft.signature_names:
        if _person_key(name) not in people:
            fails.append(f"invented person in signature: {name!r}")
    for claim in draft.claims:
        if claim not in policy.verified_claims:
            fails.append(f"unverifiable claim: {claim!r}")

    org = _fold(draft.recipient_org or "")
    if not org:
        fails.append("recipient_org missing: do-not-contact cannot be checked")
    elif any(_fold(b) in org for b in policy.do_not_contact):
        fails.append(f"recipient on do-not-contact list: {draft.recipient_org!r}")

    sender = (draft.sender or "").strip()
    local, at, domain = sender.rpartition("@")
    allowed = {_fold(d).lstrip("@") for d in policy.allowed_sender_domains}
    if not sender:
        fails.append("sender missing: sender domain cannot be checked")
    elif not at or not local or "@" in local or _fold(domain) not in allowed:
        fails.append(f"disallowed sender domain: {draft.sender!r}")

    fails.extend(_body_blockers(draft, policy))

    if draft.offers_preapproved is not True:
        fails.append("offer/terms not confirmed as pre-approved (caller must set offers_preapproved=True)")
    if draft.has_legal_footer is not True:
        fails.append("legal footer not confirmed, e.g. CAN-SPAM (caller must set has_legal_footer=True)")
    if draft.subject_truthful is not True:
        fails.append("subject line not confirmed truthful (caller must set subject_truthful=True)")
    return fails


def _run_reviewer(reviewer, draft: Draft) -> List[str]:
    name = getattr(reviewer, "name", None) or type(reviewer).__name__
    try:
        result = reviewer.review(draft)
    except Exception as e:  # fail closed: a crashed reviewer is a rejection
        return [f"{name}: reviewer failed ({type(e).__name__}: {e}), rejecting"]
    ok = getattr(result, "ok", None)
    if ok is True:
        return []
    if ok is not False:
        return [f"{name}: reviewer returned no ok=True/False verdict ({result!r}), rejecting"]
    reasons = [f"{name}: {r}" for r in (getattr(result, "reasons", None) or [])]
    return reasons or [f"{name}: rejected without a reason"]


def gate(draft: Draft, policy: Policy, reviewers=None) -> Verdict:
    """Decide whether a draft may proceed. When in doubt, block.

    1. Deterministic hard blockers.
    2. Optional independent reviewers (e.g. an LLM truth/voice check). They run
       even when a hard blocker already hit, so the verdict lists every reason.
    3. APPROVED never means "send": it means "await human approval, then send".
    """
    try:
        reasons = hard_blockers(draft, policy)
    except Exception as e:  # malformed draft or policy: reject, don't crash
        reasons = [f"hard blockers failed ({type(e).__name__}: {e}), rejecting"]
    for reviewer in (reviewers or []):
        reasons.extend(_run_reviewer(reviewer, draft))
    if reasons:
        return Verdict("REJECTED", reasons, may_send=False)
    return Verdict("APPROVED", [], may_send=False, next="await human approval, then send")
