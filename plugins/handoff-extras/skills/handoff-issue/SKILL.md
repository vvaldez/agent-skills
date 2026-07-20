---
name: handoff-issue
description: >
  Publishes session handoffs as GitHub issues instead of markdown files. Extends
  upstream /handoff: same content discipline (redaction, suggested skills, no
  duplication of tracked artifacts), but the deliverable is an issue labeled
  "handoff" that the next session finds, consumes, and closes. Falls back to the
  upstream markdown-to-temp-dir behavior when no issue tracker is available.
  Use when user says /handoff-issue, "handoff to an issue", or asks to hand off
  a session in a project that tracks work in GitHub issues.
---

# Handoff Issue

Extends upstream `/handoff` — it does not replace it. All upstream rules still apply:
summarize the conversation so a fresh agent can continue, include a "Suggested skills"
section, redact secrets and PII, and honor any arguments as a description of what the
next session will focus on.

What changes: the destination. A handoff that lives in the issue tracker is visible on
any machine, survives temp-dir cleanup, and sits next to the work it references.

## Step 1: Locate the issue tracker

1. If the repo documents its tracker (e.g. `docs/agents/issue-tracker.md`), follow that.
2. Otherwise detect GitHub via `git remote get-url origin` and use the `gh` CLI.
3. In multi-repo projects, file the handoff in the repo where the work items live
   (the one whose issues the handoff references), not necessarily the cwd.

**Fallback:** no repo, no remote, or no authenticated CLI → do exactly what upstream
`/handoff` does (markdown file in the OS temp directory) and tell the user why the
issue path was unavailable. A handoff must never fail for lack of a tracker.

## Step 2: Compose the body — dedup discipline

The prime rule: **an issue-tracker handoff carries only session state that is not
already tracked anywhere else.** Before writing, list what the session produced
(issues filed, PRs opened, docs/ADRs updated, lessons-learned entries) and reference
those by number or path instead of restating them.

Include (when applicable):

- **Pending work** — concrete next actions with enough context to start cold, in
  priority order. Name the skills to use (e.g. a ship/review workflow) per upstream's
  "suggested skills" requirement.
- **Unrecorded results** — anything the session established that has no artifact yet
  (e.g. test results awaiting a PR, measurements, decisions made verbally with the user).
- **Environment/data state** — running processes, test data left on shared accounts,
  uncommitted files, anything the next session would otherwise rediscover the hard way.
- **Standing context** — one-liners pointing at the queue/dashboard/ADRs that govern
  the work, by reference.

Redaction per upstream: no secrets, tokens, or PII. Issues are visible to everyone
with repo access — when the repo is public, treat the body as public.

## Step 3: Publish

- **Title:** `Session handoff YYYY-MM-DD: <one-line topic>`
- **Label:** `handoff` — create it if missing
  (`gh label create handoff --description "Session-state handoff for the next agent session" --color 5319E7`),
  then `gh issue create --label handoff ...`.
- **Preamble (first paragraph of the body):** state that this is a session-state
  handoff, that it carries only what is not tracked elsewhere, and that it should be
  **closed when consumed** — the next session reads it, folds its contents into real
  work items or completes them, and closes it with a short comment saying where each
  item went.

## Next-session pickup contract

A session starting cold in a repo that uses this skill should:

```bash
gh issue list --label handoff --state open
```

1. Read the newest open handoff issue **before** other re-entry briefings.
2. Work or re-home its items.
3. Close it with a comment mapping each item to where it landed.

Multiple open handoff issues mean prior sessions didn't consume them — merge stale
ones into the newest rather than leaving a trail.

## Composing with other skills

| Composition | What happens |
|-------------|--------------|
| `/handoff-issue` alone | Upstream `/handoff` content discipline, published as a labeled issue |
| `/handoff <focus args>` + this skill active | Focus args shape the issue body, same as upstream |
| Re-entry skills (e.g. a quickstart briefing) | Run the handoff-issue check first; the briefing covers the stable project, the handoff covers the perishable session state |
