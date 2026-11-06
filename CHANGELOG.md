# Changelog

## 0.2.0 (2026-11-06)

Hardening release: every check now fails closed. Each fix has a regression
test in `tests/test_probes.py` that failed against 0.1.0.

### Breaking

- `offers_preapproved`, `has_legal_footer` and `subject_truthful` default to
  `None` (unknown) instead of `True`, and anything but `True` rejects. Your
  pipeline (not the drafting model) must set them after its own checks.
- A missing `sender` or `recipient_org` rejects. 0.1.0 skipped the sender
  domain check when `sender` was empty.
- Senders must look like `local@domain` with exactly one `@`.
- `gate()` collects reasons from every stage: hard blockers and all reviewers
  run, and `Verdict.reasons` lists everything. Reviewer reasons are prefixed
  with the reviewer's name, e.g. `"NoHypeReviewer: hype/superlative: 'best'"`.
- `NoHypeReviewer` matches whole words (`bestseller` no longer trips `best`)
  and ignores sign-off lines such as `Best,`.

### Added

- Body scanning, so self-declared fields are no longer the only input:
  - `Policy.forbidden_patterns`: phrases (case-insensitive, whole words) or
    compiled regexes that must not appear in the body.
  - `Policy.known_partners`: a sentence that asserts an existing relationship
    ("partnered with", "sponsored by", "featured in", "award-winning", ...)
    must name a known partner, unless it quotes a verified claim verbatim.
  - Signers under a sign-off line ("Best,\nJane Doe", "Cheers, Jane",
    "-- Jane") must be in `Policy.real_people`. `signature_lines()` is public.
- `SupplementClaimsReviewer`: illustrative, deterministic word list for
  supplement disease/performance claims (FTC style). Not legal advice.
- `LLMReviewer`: wraps any `complete(prompt) -> str` function, fail-closed.
  Anything but a clean `{"ok": true}` JSON answer rejects. Example with the
  Anthropic SDK in `examples/llm_reviewer.py`; tests use fakes, no network.
- CI matrix for Python 3.9 to 3.13; the quickstart runs in CI.

### Fixed

- `do_not_contact` and `allowed_sender_domains` are case-insensitive on both
  sides (0.1.0 only matched lowercase policy entries).
- A reviewer that raises, or returns something without a boolean `ok`,
  rejects with the reason instead of crashing `gate()` or passing.
- A malformed draft (e.g. `signature_names=None`) rejects instead of raising.
- Name matching ignores case and titles: `"Jane Doe"` matches
  `"Jane Doe (Founder)"`.

### Docs

- README matches the code: "Who sets what", a "Limits" section, and the
  quickstart sample is executed by a test. The motivation section is now a
  neutral description of the pattern.

### CI

- `actions/setup-python` v5 to v7 (supersedes Dependabot PR #5).

## 0.1.0

- First pip-installable release: `Draft`, `Policy`, `gate()`, `NoHypeReviewer`.
