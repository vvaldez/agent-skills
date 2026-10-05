---
name: drain
description: >
  Drain the current session's residue into its durable sinks — audits what is NOT yet
  captured and routes each item: new lessons → propose to LESSONS.md, undrained gaps →
  proposed GitLab issues, git state (merged/stale worktrees and branches, stray files) →
  reported with recommended actions. Non-destructive: it proposes and reports, and defers
  actual git cleanup to /tidy and wt clean. Use when the user says /drain, "drain the
  context", "is anything left in context", "what haven't we captured yet", "did we file
  the lessons", or wraps up a session and wants to make sure nothing durable was lost.
---

# Drain

Drain the session's residue into its durable sinks so nothing worth keeping is lost when
the context closes.

A session produces three kinds of residue that live *nowhere* until captured:

1. **Lessons** — tool failure modes, gotchas, and confirmed behaviors that took more than
   one attempt to find.
2. **Gaps** — open questions, known-broken things, or follow-ups that deserve a tracked
   issue but were never filed.
3. **Git state** — merged-but-present worktrees/branches, stale bases, and stray untracked
   files that a finished session leaves behind.

`/drain` finds each kind and routes it to the right sink. It is **advisory**: it proposes
and reports. The only thing it writes without further confirmation is nothing — every
lesson is confirmed item-by-item, every issue is only *proposed*, and every git action is
*recommended* and left to `/tidy` (branches) or `wt clean` (worktrees).

This is distinct from:
- `/tidy` — git branch housekeeping only. `/drain` *reports* git state but does not delete.
- `/stats` — read-only session activity counts. `/drain` looks for what was *not* captured.

## Process

Work through the three sinks in order. Each is a separate set of Bash tool calls. Do not
stop at the first sink — a session can be clean on lessons but have stale worktrees.

### Step 1: Establish the session's change surface

Collect the facts the later sinks reason about. Run these in one batch:

```bash
git fetch origin --quiet
git status --short
git log --oneline -20
```

Identify: what this session changed (recent commits, modified files), what repos were
touched, and the set of MRs/issues involved (from commit messages and `git log`). This is
the "context" you are draining.

### Step 2: Lessons sink

Find candidate lessons — things that took more than one attempt, surprised the agent, or
contradicted an assumption. Sources, in order of reliability:

1. **The session itself** — recall the failure modes, retries, and "wait, that's not
   right" moments. These are the highest-signal lessons.
2. **Recent diffs** — new handling in scripts that encodes a workaround (a retry, a
   `command -v` dispatch, a charset validation) usually documents a lesson.

For each candidate, check whether it is **already captured** before proposing it:

```bash
grep -in "<distinctive phrase or command>" ~/.agents/LESSONS.md
```

If a match exists, skip it (do not re-file a recorded lesson). Only propose lessons that
are genuinely new and **confirmed** — no speculation, no "might be worth noting."

For each new lesson, prepare the exact edit: the text (one bullet, the failing command,
the symptom, the fix, and a `(verified <date>)` tag), the target section in
`~/.agents/LESSONS.md`, and a one-line why.

**Then present them to the user with the structured question tool** and get explicit
approval before writing anything. Group them so the user can approve all-at-once or pick
which to keep. Do not write to `LESSONS.md` until the user confirms.

After the user approves, append the confirmed lessons to the right section of
`~/.agents/LESSONS.md` and refresh the derived hot file:

```bash
bash ~/repos/agent-rules/scripts/seed-personal-rules.sh
```

Report how many were added and that the hot file was regenerated.

### Step 3: Issues sink

Find undrained gaps — things that are clearly a tracked unit of work but have no issue.
Look for:

- Known-broken behavior the session hit but did not fix (and did not file).
- Follow-ups explicitly named in an MR description or commit ("separate MR", "TODO").
- Open questions left unresolved that someone else should pick up.

For each, **propose** an issue: title (conventional, `<repo>: <summary>`), labels, and a
short body. Cross-check against open issues first so you do not propose a duplicate:

```bash
glab-cee-with-bw issue list 2>/dev/null | grep -i "<keyword>"
```

**Do not file issues.** List them in the report as "proposed — not filed" with enough
detail that the user can run `/issue-to-mr` or file them manually. Filing is a public
write and stays a deliberate user action.

### Step 4: Git-state sink (report only)

Inventory the git state and report it. Run:

```bash
git worktree list
git branch --verbose
git status --short
```

Classify each worktree and branch:

- **Merged-but-present** — branch HEAD is an ancestor of `origin/main` (verify with
  `git merge-base --is-ancestor <sha> origin/main`) but the worktree/branch still exists.
- **Stale base** — worktree is at a commit with 0 commits ahead of `origin/main` (a
  throwaway base left behind).
- **Untracked** — files in the working tree not under version control.

**Do not delete anything.** For each finding, state the recommended action and the tool
that performs it:

- Merged/stale **worktrees** → `wt clean --yes` (never auto-removes dirty worktrees).
- Merged **branches** → `/tidy`.
- Stray untracked files → name them; the user decides (they may be intentional).

Always confirm the actual `origin/main` SHA before claiming something is merged — a
worktree labeled `[main]` may be at a stale SHA.

### Step 5: Final report

End with one compact block. Omit a sink entirely if it is clean.

```
Drain Complete
  Lessons:   <N> proposed → <N> confirmed & written (hot regenerated) | none new
  Issues:    <N> proposed (not filed): <short titles>
  Git state: <N> merged worktrees → wt clean · <N> stale bases · <N> untracked files
  Sinks left for you: <exact next commands, e.g. "wt clean --yes", "/tidy">
```

Keep it to a few lines. The point is a clean "nothing durable was lost" or a precise
list of what remains and where to take it.

## Constraints

- NEVER write to `~/.agents/LESSONS.md` or `LESSONS.hot.md` without the user's explicit
  per-item or batch confirmation.
- NEVER file a GitLab/GitHub issue — propose only.
- NEVER run `wt clean`, `git worktree remove`, `git branch --delete`, `git reset --hard`,
  or `git clean` — recommend them; let `/tidy` and `wt clean` do the deleting.
- NEVER re-file a lesson already in `LESSONS.md` — check first.
- Only propose lessons that are confirmed (observed), never speculative.
- Verify `origin/main` before claiming a branch/worktree is merged.
- If the vault is locked (issues sink needs `glab-cee-with-bw`), skip the issues sink and
  say so — do not prompt for the password.
