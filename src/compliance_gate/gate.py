"""The gate itself: deterministic hard blockers + optional independent reviewers.

Fail-closed throughout: a missing field, an unconfirmed caller-side check, a
reviewer that crashes or answers in an unexpected shape all REJECT.
"""
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Iterable, List, Optional


@dataclass
class Policy:
    """Your source of truth. Load from your DB / knowledge base.

    Text matching ignores case, extra whitespace and Unicode look-alikes
    (NFKC, invisible characters). Exceptions: ``claims`` in a draft must match
    ``verified_claims`` exactly, and compiled regexes in ``forbidden_patterns``
    are used as given (add ``re.IGNORECASE`` yourself).
    """
    real_people: set = field(default_factory=set)            # who may sign: people, or team signatures you use
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
    signature_names: List[str] = field(default_factory=list)   # names; a title in parentheses is ignored
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


# Phrases that assert an EXISTING relationship. Invitations ("partner with us",
# "explore partnering", "become our partner") are deliberately not matched.
_RELATIONSHIP_CUES = re.compile(
    r"\b(?:partnered with|in partnership with|(?<!become )(?<!be )our partners?\b"
    r"|official (?:partner|supplier|sponsor)|partner of|sponsored by|endorsed by"
    r"|backed by (?!our\b|us\b)|featured (?:in|on|by)|as seen (?:in|on)|trusted by"
    r"|certified by|in collaboration with|collaborated with|(?:have|has|we've) worked with"
    r"|award-winning|award winning|won (?:an?|the) [\w ]{0,60}?award)",
    re.IGNORECASE,
)

_SIGNOFF = re.compile(
    r"^\s*(?:best(?: regards| wishes)?|kind regards|warm regards|warmest regards|regards"
    r"|sincerely(?: yours)?|yours(?: truly| sincerely)?|cheers|thanks|thank you|many thanks"
    r"|warmly|all the best|respectfully|talk soon)"
    r"(?:\s*[,:!-]+\s*(?P<rest>.*?)|\s*[.!]?)\s*$",
    re.IGNORECASE,
)
_DASH_SIGNOFF = re.compile(r"^\s*(?:--|—|–)\s*(?P<rest>.*?)\s*$")   # not a single "-": bullets
_JOINT = re.compile(r"\s+(?:&|\+|and)\s+", re.IGNORECASE)                       # two signers on one line
_TITLE_SEP = re.compile(r"\s+[|/]\s+|\s+-\s+|,")                                # "Jane Doe | CEO"
_ABBREV = re.compile(r"(?:inc|llc|ltd|co|corp|jr|sr|gmbh)\.$", re.IGNORECASE)
_PROSE_WORDS = {
    "a", "an", "the", "to", "you", "your", "me", "my", "we", "our", "us", "i", "it", "is",
    "are", "be", "will", "let", "know", "what", "if", "for", "of", "in", "on", "with",
    "this", "that", "from", "again", "soon", "forward", "looking", "hope", "see", "think",
}
_NAME_PARTICLES = {"van", "von", "de", "der", "den", "da", "del", "di", "du", "la", "le", "bin", "al"}
_INVISIBLE = dict.fromkeys(map(ord, "­​‌‍⁠﻿"))
_DASHES = dict.fromkeys(map(ord, "‐‑‒–—―−"), "-")
_LOCAL_PART = re.compile(r"[A-Za-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[A-Za-z0-9!#$%&'*+/=?^_`{|}~-]+)*")
_DOMAIN = re.compile(r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)+")


def _norm(text, dashes: bool = True) -> str:
    """NFKC, invisible characters removed, Unicode dashes as '-'. Case is kept."""
    text = unicodedata.normalize("NFKC", str(text)).translate(_INVISIBLE)
    return text.translate(_DASHES) if dashes else text


def _fold(text) -> str:
    return " ".join(_norm(text).split()).casefold()


def _mentions(folded_text: str, phrase) -> bool:
    """Case-insensitive whole-phrase match; ``folded_text`` must already be folded."""
    phrase = _fold(phrase)
    if not phrase:
        return False
    return bool(re.search(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", folded_text))


def _person_key(name) -> str:
    """'Jane Doe (Founder)', 'Jane Doe, Founder', 'Jane Doe | CEO', 'jane doe' -> 'jane doe'."""
    name = re.sub(r"\(.*?\)", " ", _norm(name))
    return _fold(_TITLE_SEP.split(name)[0]).strip(" .")


def _split_signers(line: str) -> List[str]:
    """'Mark Fakeman | CEO' -> ['Mark Fakeman']; 'Jane Doe & Mark Fakeman' -> both."""
    line = re.sub(r"\(.*?\)", " ", line)
    names = (_TITLE_SEP.split(part)[0].strip(" .") for part in _JOINT.split(line))
    return [n for n in names if n]


def _looks_like_name(name: str) -> bool:
    words = name.split()
    if not 1 <= len(words) <= 5:
        return False
    for w in words:
        if w.casefold() in _NAME_PARTICLES:
            continue
        if not (w[0].isupper() and all(c.isalpha() or c in ".'-" for c in w)):
            return False
    return True


def _is_prose(line: str) -> bool:
    words = line.split()
    if not words or len(words) > 8 or line.endswith(("?", "!", ":")):
        return True
    if line.endswith(".") and not _ABBREV.search(words[-1]) and len(words[-1]) > 2:
        return True
    return any(w.casefold().strip(".,") in _PROSE_WORDS for w in _JOINT.sub(" ", line).split())


def _signoff_rest(line: str) -> Optional[str]:
    """For a sign-off line, the text after the sign-off ("" if none); None for other lines."""
    line = _norm(line, dashes=False)
    m = _DASH_SIGNOFF.match(line) or _SIGNOFF.match(line.translate(_DASHES))
    return None if m is None else (m.group("rest") or "")


def signature_lines(body: str) -> List[str]:
    """Signers found under a sign-off ("Best,\\nJane Doe", "Cheers, Jane", "-- Jane").

    The line after a bare sign-off counts as a signature in any case or script
    unless it reads like prose. A name on the sign-off line itself must look
    like a capitalized name. Several signers on one line ("A & B") are split;
    titles after "|", " - " or "," are dropped. Heuristic by design: a signer
    written without a recognized sign-off is NOT found, so declare signers in
    ``Draft.signature_names`` as well; both are checked.
    """
    lines = [_norm(l) for l in (body or "").splitlines()]
    found: List[str] = []
    for i, line in enumerate(lines):
        rest = _signoff_rest(line)
        if rest is None:
            continue
        if rest:
            # "Thanks, Sarah, for your time." / "Thanks, Sarah." address the reader.
            if "," in rest or rest.endswith((".", "?", "!")):
                continue
            names = _split_signers(rest)
            if names and all(_looks_like_name(n) for n in names):
                found.extend(names)
            continue
        nxt = next((l.strip() for l in lines[i + 1:] if l.strip()), "")
        if nxt and not _is_prose(nxt):
            found.extend(_split_signers(nxt))
    return found


def _sentences(text: str) -> Iterable[str]:
    """Sentences, with hard-wrapped lines rejoined (only blank lines end a paragraph)."""
    for para in re.split(r"\n\s*\n", text):
        flat = " ".join(para.split())
        yield from (s for s in re.split(r"(?<=[.!?])\s+", flat) if s)


def _claim_key(text) -> str:
    return _fold(text).rstrip(" .!?")


def _body_blockers(draft: Draft, policy: Policy) -> List[str]:
    fails: List[str] = []
    body = draft.body or ""
    if not body.strip():
        return ["body missing: nothing to check"]
    normed = _norm(body)
    folded = _fold(body)

    for pattern in policy.forbidden_patterns:
        if isinstance(pattern, re.Pattern):
            if pattern.search(body) or pattern.search(normed):
                fails.append(f"forbidden pattern in body: {pattern.pattern!r}")
        elif _mentions(folded, pattern):
            fails.append(f"forbidden pattern in body: {pattern!r}")

    verified = {_claim_key(c) for c in policy.verified_claims if c}
    for sentence in _sentences(normed):
        if _claim_key(sentence) in verified or not _RELATIONSHIP_CUES.search(sentence):
            continue
        s = _fold(sentence)
        if not any(_mentions(s, partner) for partner in policy.known_partners):
            fails.append(f"partnership/endorsement in body not backed by known_partners: {sentence!r}")

    people = {_person_key(p) for p in policy.real_people}
    for signer in signature_lines(body):
        if _fold(signer).strip(" .") not in people:
            fails.append(f"invented person in body signature: {signer!r}")
    return fails


def hard_blockers(draft: Draft, policy: Policy) -> List[str]:
    """Return blocker reasons. Empty list = no hard blockers. Any hit rejects.

    Raises on a malformed draft or policy; ``gate()`` turns that into REJECTED.
    """
    fails: List[str] = []

    people = {_person_key(p) for p in policy.real_people}
    for name in draft.signature_names:
        if _fold(re.sub(r"\(.*?\)", " ", _norm(name))).strip(" .") not in people:
            fails.append(f"invented person in signature: {name!r}")
    for claim in draft.claims:
        if claim not in policy.verified_claims:
            fails.append(f"unverifiable claim: {claim!r}")

    org = _fold(draft.recipient_org or "")
    if not org:
        fails.append("recipient_org missing: do-not-contact cannot be checked")
    elif any(_fold(b) in org for b in policy.do_not_contact):
        fails.append(f"recipient on do-not-contact list: {draft.recipient_org!r}")

    # The sender is checked as the mail system will see it: no normalization.
    sender = draft.sender or ""
    local, at, domain = sender.rpartition("@")
    allowed = {str(d).strip().lower().lstrip("@") for d in policy.allowed_sender_domains}
    allowed.discard("")
    if not sender.strip():
        fails.append("sender missing: sender domain cannot be checked")
    elif not (at and _LOCAL_PART.fullmatch(local) and _DOMAIN.fullmatch(domain.lower())
              and domain.lower() in allowed):
        fails.append(f"disallowed sender domain: {draft.sender!r}")

    fails.extend(_body_blockers(draft, policy))

    if draft.offers_preapproved is not True:
        fails.append("offer/terms not confirmed as pre-approved (caller must set offers_preapproved=True)")
    if draft.has_legal_footer is not True:
        fails.append("legal footer not confirmed, e.g. CAN-SPAM (caller must set has_legal_footer=True)")
    if draft.subject_truthful is not True:
        fails.append("subject line not confirmed truthful (caller must set subject_truthful=True)")
    return fails


def _describe(e: Exception) -> str:
    try:
        return f"{type(e).__name__}: {e}"
    except Exception:
        return type(e).__name__


def _run_reviewer(reviewer, draft: Draft) -> List[str]:
    try:
        name = str(getattr(reviewer, "name", None) or type(reviewer).__name__)
    except Exception:
        name = type(reviewer).__name__
    try:
        result = reviewer.review(draft)
        ok = getattr(result, "ok", None)
        if ok is True:
            return []
        if ok is not False:
            return [f"{name}: reviewer returned no ok=True/False verdict ({type(result).__name__}), rejecting"]
        reasons = getattr(result, "reasons", None) or []
        if isinstance(reasons, str):
            reasons = [reasons]
        return [f"{name}: {r}" for r in reasons] or [f"{name}: rejected without a reason"]
    except Exception as e:  # fail closed: a crashed reviewer is a rejection
        return [f"{name}: reviewer failed ({_describe(e)}), rejecting"]


def gate(draft: Draft, policy: Policy, reviewers=None) -> Verdict:
    """Decide whether a draft may proceed. When in doubt, block. Never raises.

    1. Deterministic hard blockers.
    2. Optional independent reviewers (e.g. an LLM truth/voice check). They run
       even when a hard blocker already hit, so the verdict lists every reason.
    3. APPROVED never means "send": it means "await human approval, then send".
    """
    try:
        reasons = hard_blockers(draft, policy)
    except Exception as e:  # malformed draft or policy: reject, don't crash
        reasons = [f"hard blockers failed ({_describe(e)}), rejecting"]
    if hasattr(reviewers, "review"):
        reviewers = [reviewers]
    try:
        reviewers = list(reviewers or [])
    except TypeError:
        reasons.append("reviewers must be a list of reviewers, rejecting")
        reviewers = []
    for reviewer in reviewers:
        reasons.extend(_run_reviewer(reviewer, draft))
    if reasons:
        return Verdict("REJECTED", reasons, may_send=False)
    return Verdict("APPROVED", [], may_send=False, next="await human approval, then send")
