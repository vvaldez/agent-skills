---
name: ship
description: >
  Unified MR/PR workflow — detects git state, creates a branch if on main, commits with
  conventional format, pushes, and creates a GitLab merge request (glab) or GitHub pull
  request (gh) in one command. Auto-detects platform from remote URL. Use when user says
  /ship, "create MR", "create PR", "ship this", "merge request", "pull request",
  "push and create MR/PR", "wrap up", or is done with changes and wants to get them into review.
---

# Ship

One command to go from working changes to a merge/pull request. Detects where you are in the
git workflow and picks up from there.

## Platform Detection

Before anything else, determine the platform:

```bash
git remote get-url origin 2>/dev/null
```

- URL contains `github.com` → use `gh` CLI, create **pull request**
- Otherwise → use `glab` CLI, create **merge request**

Store the result and use the correct CLI and terminology throughout.

## State Detection

Gather context:

```bash
git branch --show-current
```

```bash
git status --porcelain
```

```bash
git log origin/main..HEAD --oneline 2>/dev/null || echo "NO_COMMITS_AHEAD"
```

Then choose the right path:

### Case A: On `main` with uncommitted changes

You cannot commit to main. Ask the user for:

1. **Branch type**: `feature/`, `fix/`, `docs/`, `refactor/`
2. **Short description**: kebab-case, 2-4 words (e.g., `add-report-index`)

Create the branch:

```bash
git switch --create <type>/<description>
```

Then continue to the Commit Flow.

### Case B: On `main`, clean working tree, no commits ahead

Nothing to ship. Tell the user: "Nothing to ship — working tree is clean and no commits
ahead of origin/main. Start making changes first."

Stop here.

### Case C: On a feature branch (primary path)

Proceed to Commit Flow if there are uncommitted changes, or skip to Push + MR/PR Flow if
everything is already committed.

---

## Commit Flow

Only if there are uncommitted changes.

### Step 1: Review Changes

```bash
git status
```

```bash
git diff --stat
```

Show the user what will be committed. If there are both staged and unstaged changes, clarify
which files to include.

### Step 2: Check for Secrets

Before staging, scan for files that should NEVER be committed:

- `*.env` files
- `vault.yml` or `*vault*.yml`
- `credentials*`, `*.key`, `*.pem`
- Any file containing `password`, `token`, `secret` in its name

If found, warn the user and exclude those files. Do NOT proceed if secrets are detected
without explicit user override.

### Step 3: Stage Files

```bash
git add <specific-files>
```

Be selective. Do NOT use `git add -A` unless every changed file clearly belongs together.
If ambiguous, ask the user which files to include.

### Step 4: Generate Commit Message

Determine the conventional commit type from the changes:

| Type | When |
|------|------|
| `feat:` | New feature or capability |
| `fix:` | Bug fix |
| `refactor:` | Code restructuring, no behavior change |
| `docs:` | Documentation only |
| `test:` | Test additions or fixes |
| `chore:` | Maintenance, deps, config |

Generate a commit message:
- **Subject**: `<type>(<scope>): <description>` — under 50 chars, imperative mood
- **Body**: What changed and why (functional), wrapped at 72 chars
- **Footer**: Co-authorship attribution

### Step 5: Commit

```bash
git commit -m "$(cat <<'EOF'
<type>(<scope>): <description>

<body — what changed and why>

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

If pre-commit hooks modify files:
1. Check which files were modified (`git diff --name-only`)
2. If only YOUR files: re-stage and retry with a NEW commit (not `--amend`)
3. If UNRELATED files: `git checkout -- <unrelated>`, re-stage yours, retry

---

## Push + MR/PR Flow

### Step 1: Push

```bash
git push --set-upstream origin $(git branch --show-current)
```

If push fails:
- **"Could not resolve host"** or timeout → Remind user to check network/VPN and try
  `/ship` again.
- **"rejected" / "non-fast-forward"** → Branch diverged from remote. Ask user whether to
  force-push or pull first.

### Step 2: Analyze Changes for Description

```bash
git log origin/main..HEAD --oneline
```

```bash
git diff origin/main..HEAD --stat
```

If needed for context:
```bash
git diff origin/main..HEAD
```

### Step 3: Generate Description

**Style: objective and descriptive.** State what changed functionally. No marketing
language, no selling, no subjective terms.

```markdown
## Summary

- [1-3 bullet points: what this MR/PR does]

## Changes

- [Specific modifications made, grouped logically]

## Test Plan

- [ ] [Specific verification steps]

---

Generated with [Claude Code](https://www.anthropic.com/claude-code)
```

### Step 4: Create MR or PR

**GitLab (glab):**
```bash
glab mr create --title "<conventional-commit-style title, under 70 chars>" \
  --description "$(cat <<'EOF'
<generated description>
EOF
)"
```

**GitHub (gh):**
```bash
gh pr create --title "<conventional-commit-style title, under 70 chars>" \
  --body "$(cat <<'EOF'
<generated description>
EOF
)"
```

If the CLI fails:
- **Not authenticated** → Tell user to run `glab auth login` or `gh auth login`
- **No remote** → Suggest `git remote add origin <url>`
- **CLI not installed** → Tell user to install `glab` or `gh`

### Step 5: Report

Output the MR/PR URL from the CLI response. Format:

```
Shipped!
  Branch: feature/add-report-index
  Commit: feat(reports): add styled index pages for report server
  MR: https://gitlab.example.com/org/repo/-/merge_requests/103
```

Or for GitHub:

```
Shipped!
  Branch: feature/add-report-index
  Commit: feat(reports): add styled index pages for report server
  PR: https://github.com/org/repo/pull/42
```

---

## Constraints

- NEVER commit directly to main — always create a branch first
- NEVER commit files that look like secrets (.env, vault, credentials, keys)
- NEVER use `git add -A` without reviewing what's included
- NEVER use `--no-verify` to skip pre-commit hooks
- NEVER amend commits — always create new ones
- ALWAYS use conventional commit format
- ALWAYS include `Co-Authored-By` footer
- ALWAYS use HEREDOC pattern for multi-line commit messages and descriptions
- ALWAYS use `glab` or `gh` (auto-detected) for MR/PR creation

## Error Recovery

| Error | Action |
|-------|--------|
| On main, refuse to commit | Create branch first (ask user for name) |
| Pre-commit hook fails | Fix the issue, re-stage, NEW commit |
| Push fails (network/VPN) | Report requirement, stop |
| Push fails (diverged) | Ask user: force-push or pull first? |
| CLI not authenticated | Tell user to run auth command for their platform |
| CLI not installed | Tell user to install glab or gh |
| Nothing to commit | Skip to Push + MR/PR if commits exist, otherwise report nothing to ship |
| MR/PR already exists | Report existing URL instead of creating duplicate |
