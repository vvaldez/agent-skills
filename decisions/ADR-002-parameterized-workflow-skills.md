# ADR-002: publish parameterized workflow skills, keep team values local

**Status:** Accepted
**Date:** 2026-09-25

## Context

`/issue-to-mr` and `/mr-followthrough` encode a specific team's GitLab
workflow: a particular instance, a Linux test VM, a pipeline helper, and
designated reviewer handles. First drafts hardcoded those values and were
submitted to this public marketplace repo; a dual-blind code review
BLOCKed the hardcoding — internal infrastructure identifiers in a public
repo are unrecoverable once merged (instance hostname, network address,
service account, teammate handles).

The question: how to ship workflow skills that are inherently
team-specific through a public plugin marketplace.

## Decision

The public skills are parameterized. Team-specific values resolve from
`CLAUDE.local.md` (gitignored) in the repo root or from the environment,
via named placeholders (`<gitlab-host>`, `<gitlab-cli>`, `<pipeline-check>`,
`<vm-target>`, `<reviewer>`, `<approvers>`) — environment variables use
the uppercase placeholder name (`GITLAB_CLI`, `VM_TARGET`, …). Each
skill carries a **Local config** section listing its placeholders and
stops + asks when a value is missing rather than guessing or hardcoding.

The author's concrete values live in gitignored local config and in
private copies of the same skills; they never appear in the marketplace
repo.

## Consequences

- The public repo discloses no instance hostnames, network addresses,
  service accounts, or teammate handles.
- Installers from other teams adopt the skills by filling in their own
  `CLAUDE.local.md` — the skills are genuinely portable, not just
  de-identified.
- A missing local value is a stop condition, not a silent fallback: a
  misconfigured skill halts and asks rather than acting on guesses.
- The author keeps private, concrete copies of the same skills for
  day-to-day use; the public copy is the parameterized twin.

## Alternatives considered

| Option | Rejected because |
|--------|-----------------|
| Hardcode team values | Unrecoverable disclosure of internal infrastructure in a public repo (review BLOCK) |
| Keep the skills out of the marketplace | Loses composition value for other teams; the workflows are general, only the values are team-specific |
| Separate private marketplace/plugin | Dual distribution for what is a values-only difference |
