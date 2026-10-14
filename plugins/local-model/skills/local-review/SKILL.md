---
name: local-review
description: >
  Cheap first-pass code review by a locally-hosted model, over any diff git can produce —
  unstaged work, staged changes, a branch against another ref, or a subset of paths.
  Costs almost no context: the diff goes to a local endpoint and only a short list
  of candidate defects comes back. Use when the user says /local-review, "local review",
  "quick review", "cheap review", or wants a diff looked at without spending a full review
  on it. Its findings are candidates to check, never verdicts, and a clean result is weak
  evidence rather than an all-clear. Two stacks, selected by an OS check up front:
  Windows (PowerShell 5.1 + the separate localllm tooling) or macOS (Ollama + a
  read-only opencode reviewer agent). Without that OS's stack it cannot run at all —
  say so and stop.
metadata:
  opencode/slash: "true"
---

# Local Review

Run a locally-hosted model over a diff. Get back a short list of candidate
defects. The bulk text never enters this context — that asymmetry is the entire
reason the tool exists.

This skill is a **pointer**, not an implementation. Each stack's script owns
the gate, the encoding step, the preflight, and the warning text. Do not
reimplement any of it here.

## First: OS check, then that stack's preflight

`uname -s` → `Darwin` = **macOS stack**; `MINGW*` / `MSYS*` / `CYGWIN*` =
**Windows stack** (under Windows PowerShell 5.1 there is no `uname` —
`$env:OS` is `Windows_NT`). Any other OS: say it is unsupported and stop.

Then run the preflight for that stack only. If its preflight fails, **say so
plainly and stop.** Do not read the diff yourself and call it a local review —
that spends the context this skill exists to save, under a label saying it
didn't.

### Windows preflight

`local-review` calls `review-diff.ps1` from the **localllm** repo, which is
**not bundled with this plugin** and is not publicly available. It also needs a
model already loaded on a local worker, Windows with PowerShell 5.1, and
**Node.js on PATH** — the `llm` entry point is a `.cmd` shim around a Node
script, and a missing `node` surfaces as exit 3, which looks like a model fault
and is not.

### macOS preflight

The macOS stack calls a `run-reviewer` script from a local agent-tools
checkout — **not bundled with this plugin**. Its path is baked into this
deployed copy (rendered from a gitignored local config at deploy time);
if the path below does not exist as an executable file, say so and stop.
It also needs, on this machine:

1. `opencode` and `python3` on PATH.
2. A read-only `local-reviewer` opencode agent, created once via the
   agent-tools `local-agent` SETUP (it is a machine-level agent, not part of
   this plugin).
3. The chosen model registered in `~/.config/opencode/opencode.jsonc` — the
   script checks and prints the fix (`local-ai-setup --model <tag>` or add it
   to the provider section).
4. For a bare Ollama tag, the model pulled locally (`ollama list`).

## Run it

Set the tool timeout to **600000** for either stack, and do not split the
resolution from the invocation.

### Windows

One self-contained PowerShell block. Do not split it: PowerShell tool calls do
not carry variables between invocations, so a second call would run `& $null`
and fail with an opaque parser error.

```powershell
$llmHome = if ($env:LOCALLLM_HOME) { $env:LOCALLLM_HOME } else { "$env:USERPROFILE\tools\localllm" }
$script  = Join-Path $llmHome 'review-diff.ps1'
if (-not (Test-Path $script)) {
    Write-Host "local-review: localllm not found at $llmHome. Set LOCALLLM_HOME."
    exit 2
}
$outDir = Join-Path $env:TEMP "local-review-skill\$PID"
try {
    & $script -OutDir $outDir
    $code = $LASTEXITCODE
} finally {
    Remove-Item $outDir -Recurse -Force -ErrorAction SilentlyContinue
}
Write-Host "local-review: review-diff exited $code"
exit $code
```

Three things in that block are load-bearing.

**The guard exits 2, not `return`.** `return` yields process exit 0, and the
table below reads 0 as "it ran" — so a missing install would be reported as a
clean local pass on code that was never sent anywhere. That is the exact
outcome the script's own exit 4 exists to prevent; do not reintroduce it in the
wrapper.

**The timeout must be raised.** The default PowerShell tool timeout is 120s and
the runtimes below exceed it — a clean 10,000-character diff is documented at
4.4 minutes. A killed process does not run the script's cleanup, which is the
one path that still strands the verbatim diff on disk.

**`-OutDir` is mandatory, per-run, and deleted afterwards.** The script's
default is `.scratch`, relative to the current directory — a private diff and
its findings, untracked, inside the repo being reviewed. `$env:TEMP\claude-local-review`
is the commit hook's own directory, and sharing it means a concurrent hook run
rewrites the findings file under you. `$PID` isolates the run; the `finally`
stops that isolation from accumulating one findings directory per invocation
in `%TEMP%` forever, each holding that repo's paths and defect text. The
compact list on stdout carries everything the JSON does, so nothing is lost —
but it does mean the `Full JSON:` path the script prints is already gone by
the time you read it. Report from the printed list.

### macOS

```bash
<local-review-script> "<target-dir>" "<base-ref>" [model]
```

- `<target-dir>`: the git checkout or worktree holding the changes. The
  reviewer agent gets read access to this directory (opencode `--dir`
  sandbox), so it can open the files it cites — not just the diff.
- `<base-ref>`: what is being compared against — `main`, `HEAD~1`, a tag.
  The script diffs `base...HEAD` (three-dot, from the merge base), so it does
  not pull in the inverse of newer base commits the way two-dot does.
- `model`: omit for the default, `deepseek-r1:8b` (a public Ollama reasoning
  model). A bare tag means `ollama/<tag>`; a full `provider/model` ID is used
  as-is.

Scope caveat, different from Windows: this reviews **committed** changes
against the base. Uncommitted work is not in `HEAD` — if the user wants
unstaged changes reviewed, say so and either make a WIP commit with them
(first confirm with the user) or use the Windows-style manual diff path with
their explicit OK.

The script prints `=== Verdict (<model>) ===` followed by the verdict text,
and ends with `Full results: <dir>` — a per-run results dir holding
`verdict.md`, the raw event stream, a sanitized session export, and token
usage in `meta.json`. Report from the printed verdict; the results dir is for
the user's inspection, not for relaying.

## Scope selectors (Windows)

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

On macOS the equivalent narrowing is choosing the base ref (and the script's
three-dot diff already avoids the two-dot trap), or reviewing a narrower
branch-point.

## How long it takes

**Seconds to minutes, and the clean answer is the expensive one.** Observed on
Windows: 2s on a small prose diff, 9s on an eight-line file, 99s on 700 lines.
The tooling's own notes record a clean 10,000-character diff costing 4.4
minutes, because "nothing is wrong" takes more generation than "here is the
bug." On macOS the default is a reasoning model — expect the multi-minute end
of that range for anything but a small diff, which is why the timeout is
raised on both stacks.

This is why narrowing is not just politeness: concurrent reviews serialize on
the local GPU/worker (one loaded model on Windows; one Ollama slot per loaded
model on macOS), so the second waits for both.

Narrow the scope before reaching for a whole branch. The Windows commit hook
refuses anything over 60,000 characters; that is a sane manual ceiling too.
`review-diff.ps1` warns above roughly 100,000 tokens of diff and then
**proceeds anyway** — if you see that warning, expect truncation and narrow the
scope instead of trusting the result.

## Read the exit code before the output

### Windows

| Code | Meaning | Do |
|------|---------|-----|
| `0` | it ran | report the candidates, or that it returned none — see the caveat below |
| `1` | usage error | fix the invocation |
| `2` | it could not run | **read the printed `review-diff:` line** — it says which cause |
| `3` | the model returned something unusable | report that — and read the printed lines, see below |
| `4` | **nothing to review — the diff was empty** | never report "no findings"; say nothing was sent, and check the scope selector |

**Exit 2 has five causes** and only two are fixed by starting a worker: a
missing install file, not being in a git repo, `git diff` itself failing (a bad
ref, a branch that does not exist), no worker running at all, and a worker
running with no model loaded. The script prints which one, and the printed line
is the authority — this list exists so you recognise that "no worker at
http://localhost:1234/v1" is a real member of it, not so you can skip reading.
Starting a worker to fix a typo'd ref costs real time and a GPU another session
may be using.

**Exit 3 does not always mean the model.** Every non-zero exit from the `llm`
entry point collapses to 3, including a missing `node` (exit 9009) and a network
failure. The script now says whether raw output was actually written: if it
reports that nothing was written, the cause is in the lines above it, not in a
result file, and it is not a GPU problem.

**Exit 4 is the one to be careful with.** It means the model received nothing.
Reporting "no findings" there is a clean bill of health on unreviewed code.

### macOS

| Outcome | Meaning | Do |
|---------|---------|-----|
| exit `0` | it ran | report the verdict under the precision caveat below |
| exit `1` with an `Error:` line | usage/preflight: bad target dir, bad ref, `opencode`/`python3` missing, model not registered, or **empty diff** | read the printed line; an empty diff means nothing was sent — never report "no findings", check the base ref and that the changes are committed |
| other non-zero | the opencode run itself failed | read `run.log` in the printed results dir before reporting; it is an execution fault, not a model verdict |

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

### Windows

Omit `-Model` and the script resolves the reviewer itself — the first model the
worker reports — and prints `reviewing with <id>` whenever that choice is not
obvious. Read that line. It is not decoration: the preflight line lists *every*
loaded model, and until 2026-08-23 an environment variable could substitute a
different reviewer without the output changing.

**If it prints a `WARNING ... is marked rejected` line, stop and say so.** That
model was measured out for review work — one of them scored 0.0 on the control
and invented a finding every single run. Its output must not be reported under
the 50% precision caveat below, which is far too generous for it.

`-Model` selects among models **already loaded** — it does not swap them, and a
consumer GPU holds one at a time. Asking for a model that is not resident fails
as exit 3, which looks like a model fault and is not. Swapping is a heavier,
separate operation (`worker-start.ps1 -ModelKey <key>` in the localllm repo) that
unloads whatever is running, so do not do it while another session may be using
the worker.

### macOS

The default is `deepseek-r1:8b` unless the user names a model. Anything passed
must already be registered in `opencode.jsonc` — the script's preflight rejects
unregistered specs and prints the fix. `ollama list` shows what is actually on
the machine; a model that is pulled but unregistered fails the preflight, and
the fix is `local-ai-setup --model <tag>` (or adding it to the provider
section). Ollama loads a model on demand rather than holding one resident slot,
but concurrent reviews of large diffs still serialize on the GPU — do not start
a second run while one is in flight.

## What this is not

- **Not a full code review.** It is a first pass. Run it before a thorough
  review, not instead of one.
- **Not made redundant by the commit hook.** If the hook is wired up it *may*
  already cover a commit — but on Windows it sees only **staged** changes,
  skips anything over 60,000 characters, and has been observed not firing at
  all. If the user asks for a review before committing, run this and say you
  did.
- **Not for judgement.** No planning, no architecture, no "should we do this."
