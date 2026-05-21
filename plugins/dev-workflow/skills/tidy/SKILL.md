---
name: tidy
description: >
  Gentle git housekeeping — fetches origin, prunes stale remote refs, reports branch status,
  auto-deletes merged branches, and confirms before touching unmerged ones. Non-destructive
  by default. Use when user says /tidy, "clean up git", "check branches", "housekeeping",
  "are my branches clean", or after merging an MR/PR and wanting to sync local state.
---

# Tidy

Gentle git housekeeping that syncs, reports, and cleans without destroying anything.

This is NOT a workspace reset. No `--hard`, no `clean -fdx`, no force anything. It fetches,
prunes, reports, and offers to clean up branches that are already merged. Think of it as
sweeping the floor, not demolishing the house.

## Process

Run each step as a separate Bash tool call.

### Step 1: Fetch and Prune

```bash
git fetch origin
```

```bash
git remote prune origin
```

Report how many stale refs were pruned (parse output for `[pruned]` lines).

### Step 2: Update Current Branch

Only if on a branch that tracks a remote:

```bash
git pull --ff-only
```

If this fails (diverged history), report it but do NOT force-pull or rebase. Tell the user
their branch has diverged and suggest they handle it manually.

### Step 3: Identify Branch Status

```bash
git branch --verbose --verbose
```

Classify each local branch:
- **Merged**: branch is fully merged into `origin/main` (check with `git branch --merged origin/main`)
- **Gone**: tracks a remote that no longer exists (`[origin/...: gone]`)
- **Active**: has a live remote tracking branch
- **Local-only**: never pushed (no tracking info)

### Step 4: Auto-Delete Merged Branches

For branches that are merged into `origin/main` AND are not the current branch AND are not `main`:

```bash
git branch --delete <branch-name>
```

Use `--delete` (safe delete), never `--delete --force`. Report each deletion. If `--delete`
refuses (branch not fully merged from git's perspective), skip it and report — do not force.

### Step 5: Handle Unmerged Branches with Deleted Remotes

If any branches have `gone` tracking refs but are NOT merged, list them with their last commit
date and message:

```bash
git log -1 --format="%ci %s" <branch-name>
```

Ask the user what to do with each one. Options:
- Delete it (use `git branch --delete --force` only with explicit user confirmation)
- Keep it

### Step 6: Final Report

Show a clean summary:

```
Git Tidy Complete
  Branch: main (up to date with origin/main)
  Pruned: 3 stale remote refs
  Deleted: 2 merged branches (feature/old-thing, fix/that-bug)
  Remaining: 1 local branch (main)
  Working tree: clean | 2 uncommitted changes
```

## Constraints

- NEVER run `git reset --hard`
- NEVER run `git clean -fd` or `git clean -fdx`
- NEVER run `git push --force`
- NEVER delete `main` branch
- NEVER delete the current branch
- Use `git branch --delete` (safe), not `--delete --force`, unless user explicitly confirms
- If anything looks wrong, report and stop — don't try to fix it automatically
