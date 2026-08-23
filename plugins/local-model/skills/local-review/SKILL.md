---
name: local-review
description: >
  Cheap first-pass code review by a locally-hosted model, for a diff that has not been
  committed yet — working tree, staged changes, a branch against main, or a subset of paths.
  Costs almost no context: the diff goes to a local GPU and only a short list of candidate
  defects comes back. Use when the user says /local-review, "local review", "quick review",
  "cheap review", "review this before I commit", or wants a diff looked at without spending
  a full review on it. Also use when a diff is too large to read but too small to justify
  the two-axis code-review skill. Requires the localllm worker on this machine; Windows and
  PowerShell 5.1 only.
---

# Local Review

Run a locally-hosted model over a diff. Get back a short list of candidate
defects. The bulk text never enters this context — that asymmetry is the entire
reason the tool exists.

This skill is a **pointer**, not an implementation. The script owns the gate, the
encoding step, the preflight, and the warning text. Do not reimplement any of it
here.

## Prerequisite

The `localllm` tooling must be installed on this machine. It is a separate repo
and is **not** bundled with this plugin.

Resolve its location in this order:

1. `$env:LOCALLLM_HOME`
2. `C:\Users\<you>\tools\localllm`

```powershell
$home_ = if ($env:LOCALLLM_HOME) { $env:LOCALLLM_HOME } else { "$env:USERPROFILE\tools\localllm" }
$script = Join-Path $home_ 'review-diff.ps1'
if (-not (Test-Path $script)) { "local-review: localllm not found at $home_. Set LOCALLLM_HOME." }
```

If it is not there, say so and stop. Do not improvise a review by reading the
diff yourself and calling it a local review — that spends the context this skill
exists to save, under a label that says it didn't.

## Run it

```powershell
& $script -OutDir "$env:TEMP\claude-local-review"
```

Add exactly one scope selector:

| Flag | Reviews |
|------|---------|
| *(none)* | uncommitted work against `HEAD` |
| `-Staged` | staged changes only |
| `-Ref main` | this branch against `main` (three-dot, vs the merge-base) |
| `-Ref HEAD~1` | the last commit |

Narrow a wide diff with `-Path src/auth.ts,src/session.ts`.

**Always pass `-OutDir "$env:TEMP\claude-local-review"`.** The script's default is
`.scratch`, relative to the current directory, and the findings file quotes the
diff — so the default writes model output derived from the project's source into
the project's own tree. Only localllm's `.gitignore` covers that path. No other
repo's does.

## Read the result

Only the compact list prints. Full JSON stays on disk at the path the script
names. **Do not read that file back.** Reading it defeats the purpose. Read the
printed list; open the JSON only for a single finding actually being chased.

Exit codes:

| Code | Meaning | Do |
|------|---------|-----|
| `0` | ok, including zero findings | report the list, or "no findings" |
| `1` | usage error | fix the invocation |
| `2` | no worker loaded, or not a repo | run `worker-start.ps1`, or report the review did not run |
| `3` | model returned something unusable | report it; the raw output path is printed |

On `2`, never report "no findings". "The review did not happen" and "the review
found nothing" are different answers and the difference matters.

## Then check every finding

Measured precision on real diffs is about **50 percent**. It has caught a genuine
bug and invented two others in the same run, put the real one in the wrong file,
and cited a line one off from the actual defect.

Open every cited line before acting on it. Then say plainly which candidates did
not hold up. Passing an unverified finding to the user as fact is the failure
mode this tool sits one step away from.

## Model choice

Omit `-Model` to use whatever is already resident. Pass
`-Model gemma-4-12b-it-qat` when a false positive costs more than a miss. Avoid
coder-tuned small models for review work — in testing they were the most
confident and the least correct.

`-Model` targets an **already-loaded** model. A consumer card holds one at a
time; this flag does not swap them.

## What this is not

- **Not `code-review`.** That runs two axes in parallel sub-agents against the
  repo's documented standards and the originating spec. This is a nine-second
  smell check. Run this first if at all; it does not substitute.
- **Not the commit hook.** If `review-hook.ps1` is wired into settings, every
  `git commit` is already reviewed automatically. Do not invoke this skill for a
  commit that is about to happen.
- **Not for judgement.** No planning, no architecture, no "should we do this."
  Local models are for bulk text with a checkable answer.
