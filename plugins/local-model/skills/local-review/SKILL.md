---
name: local-review
description: >
  Cheap first-pass code review by a locally-hosted model, for a diff that has not been
  committed yet — unstaged work, staged changes, a branch against another ref, or a subset
  of paths. Costs almost no context: the diff goes to a local endpoint and only a short list
  of candidate defects comes back. Use when the user says /local-review, "local review",
  "quick review", "cheap review", or wants a diff looked at without spending a full review
  on it. Its findings are candidates to check, never verdicts, and a clean result is weak
  evidence rather than an all-clear. REQUIRES the separate localllm tooling on this machine
  plus a running model worker; Windows and PowerShell 5.1 only. Without those it cannot run
  at all — say so and stop.
---

# Local Review

Run a locally-hosted model over a diff. Get back a short list of candidate
defects. The bulk text never enters this context — that asymmetry is the entire
reason the tool exists.

This skill is a **pointer**, not an implementation. The script owns the gate, the
encoding step, the preflight, and the warning text. Do not reimplement any of it
here.

## Before anything: can this run at all?

`local-review` calls `review-diff.ps1` from the **localllm** repo, which is
**not bundled with this plugin** and is not publicly available. It also needs a
model already loaded on a local worker, and Windows with PowerShell 5.1.

If any of that is missing, **say so plainly and stop.** Do not read the diff
yourself and call it a local review — that spends the context this skill exists
to save, under a label saying it didn't.

## Run it

One self-contained block. Do not split the resolution from the invocation:
PowerShell tool calls do not carry variables between invocations, so a second
call would run `& $null` and fail with an opaque parser error.

```powershell
$llmHome = if ($env:LOCALLLM_HOME) { $env:LOCALLLM_HOME } else { "$env:USERPROFILE\tools\localllm" }
$script  = Join-Path $llmHome 'review-diff.ps1'
if (-not (Test-Path $script)) {
    Write-Host "local-review: localllm not found at $llmHome. Set LOCALLLM_HOME."
    return
}
& $script -OutDir (Join-Path $env:TEMP "local-review-skill\$PID")
```

`-OutDir` is **mandatory and must be per-run**. Two reasons:

- The script's default is `.scratch`, relative to the current directory, and it
  writes `review-diff.txt` there — **the complete verbatim diff**. On a failure
  path that file can survive, leaving a full copy of a private diff untracked
  inside the repo being reviewed.
- `$env:TEMP\claude-local-review` is the commit hook's own working directory.
  Sharing it means a concurrent hook run deletes and rewrites the findings file
  under you, and you read another diff's results. Hence the `$PID` suffix.

## Scope selectors

Pick exactly one. **Read this table carefully — the default is narrower than it
looks.**

| Flag | Reviews |
|------|---------|
| *(none)* | **unstaged changes only** — working tree vs the index |
| `-Ref HEAD` | everything uncommitted, staged and unstaged |
| `-Staged` | staged changes only — what is about to be committed |
| `-Ref main` | working tree against `main`'s tip |
| `-Ref HEAD~1` | the last commit **plus any uncommitted changes** |

Two traps in that table:

**The no-flag default excludes staged work.** Bare `git diff` is the working
tree against the index. If the user has staged anything — `git add -p`, a
formatting hook, or your own earlier edits — it is not reviewed. When the user
says "review my changes" without distinguishing, prefer `-Ref HEAD`.

**`-Ref` is two-dot, not merge-base.** `git diff <ref>` compares the working
tree to that ref's tip. On a branch where `main` has advanced, `-Ref main`
therefore includes the inverse of main's newer commits — changes you did not
write — and the model will report defects in them. Prefer your own branch-point,
or narrow with `-Path src/auth.ts,src/session.ts`.

## How long it takes

**Seconds to minutes, and the clean answer is the expensive one.** Observed: 2s
on a small prose diff, 9s on an eight-line file, 99s on 700 lines. The tooling's
own notes record a clean 10,000-character diff costing 4.4 minutes, because
"nothing is wrong" takes more generation than "here is the bug."

Narrow with `-Path` before reaching for a whole branch. The commit hook refuses
anything over 60,000 characters; that is a sane manual ceiling too. The script
warns above roughly 100,000 tokens of diff and then **proceeds anyway** — if you
see that warning, expect truncation and narrow the scope instead of trusting the
result.

## Read the exit code before the output

| Code | Meaning | Do |
|------|---------|-----|
| `0` | it ran | report the candidates, or that it returned none — see the caveat below |
| `1` | usage error | fix the invocation |
| `2` | it could not run | **read the printed `review-diff:` line** — it says which cause |
| `3` | the model returned something unusable | report that; the raw output path is printed |
| `4` | **nothing to review — the diff was empty** | never report "no findings"; say nothing was sent, and check the scope selector |

**Exit 2 has four causes** and only two are fixed by starting a worker: a missing
install, not being in a git repo, `git diff` itself failing (a bad ref, a branch
that does not exist), and no model loaded. The script prints which one. Read that
line rather than guessing — starting a worker to fix a typo'd ref costs real time
and a GPU another session may be using.

**Exit 4 is the one to be careful with.** It means the model received nothing.
Reporting "no findings" there is a clean bill of health on unreviewed code.

## Then check every finding, and distrust a clean result

Measured precision on real diffs is about **50%**. It has caught a genuine bug
and invented two others in the same run, put the real one in the wrong file, and
cited a line one off from the defect. Open every cited line before acting, and
say plainly which candidates did not hold up.

There is a subtler failure worth naming: **correct observation, fabricated
impact.** It has raised a blocker about something genuinely present in the diff
whose stated consequence was invented. The verifiable half makes the invented
half more persuasive, not less.

**And zero findings is not an all-clear.** On one recorded diff it returned
nothing in 2s while two independent reviewers over the identical input found
four real defects, one a blocker both found separately. Report a clean result as
"the local pass found nothing," never as "this is clean."

## Model selection

Omit `-Model` and it uses whichever model the preflight line printed.

`-Model` selects among models **already loaded** — it does not swap them, and a
consumer GPU holds one at a time. Asking for a model that is not resident fails
as exit 3, which looks like a model fault and is not. Swapping is a heavier,
separate operation (`worker-start.ps1 -ModelKey <key>` in the localllm repo) that
unloads whatever is running, so do not do it while another session may be using
the worker.

## What this is not

- **Not a full code review.** It is a first pass. Run it before a thorough
  review, not instead of one.
- **Not made redundant by the commit hook.** If the hook is wired up it *may*
  already cover a commit — but it sees only **staged** changes, skips anything
  over 60,000 characters, and has been observed not firing at all. If the user
  asks for a review before committing, run this and say you did.
- **Not for judgement.** No planning, no architecture, no "should we do this."
