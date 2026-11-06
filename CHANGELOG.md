# Changelog

## 0.2.0 (2026-11-06)

Hardening release: every check now fails closed. The seven probes that
passed bad drafts through 0.1.0 are pinned in `tests/test_probes.py` (13 tests,
all failing on 0.1.0); edge cases from a second review are in
`tests/test_hardening.py`.

### Breaking

- `offers_preapproved`, `has_legal_footer` and `subject_truthful` default to
  `None` (unknown) instead of `True`, and anything but `True` rejects. Your
  pipeline (not the drafting model) must set them after its own checks.
- A missing `sender`, `recipient_org` or `body` rejects. 0.1.0 skipped the
  sender domain check when `sender` was empty.
- Senders are checked as the mail system sees them: exactly one `@`, a plain
  ASCII local part (no spaces, commas or line breaks) and an ASCII domain on
  the allowed list. No Unicode normalization on the sender.
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
  - Signers under a sign-off line ("Best,\nJane Doe", "Best regards - Jane",
    "-- Jane") must be in `Policy.real_people`, including each name in
    "Jane Doe & Mark Roe" and names in any case or script on the line after a
    bare sign-off. `signature_lines()` is public.
  - Text matching uses NFKC, drops invisible characters and treats Unicode
    dashes as "-", so look-alike spellings don't slip past.
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
- `gate()` never raises: a malformed draft (e.g. `signature_names=None`),
  odd reviewer results (`reasons=5`, a failing `__repr__`) or a non-list
  `reviewers` argument reject. `hard_blockers()` alone still raises on a
  malformed draft. A single reviewer object is accepted as `reviewers=`.
- Name matching ignores case, whitespace and a title in parentheses or after
  `,`, `|` or ` - `: `"Jane Doe"` matches `"Jane Doe (Founder)"`. Declared
  `signature_names` drop only parenthesized titles, so
  `"Jane Doe, Mark Roe"` cannot smuggle a second name.
- `LLMReviewer` escapes every case/spacing variant of the closing draft tag
  and rejects JSON with duplicate keys.

### Docs

- README matches the code: "Who sets what", a "Limits" section, and the
  quickstart sample is executed by a test. The motivation section is now a
  neutral description of the pattern.

### CI

- `actions/setup-python` v5 to v7 (supersedes Dependabot PR #5).

## 0.1.0

- First pip-installable release: `Draft`, `Policy`, `gate()`, `NoHypeReviewer`.
