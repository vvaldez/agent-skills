---
name: stats
description: >
  Session statistics dashboard — parses Claude Code JSONL transcripts or the OpenCode
  session store (auto-detected) to show slash command usage, tool call counts, MRs/PRs
  created, commits, agent spawns, doc edits, and session duration.
  Use when user says /stats, "session stats", "what did I do", "how many MRs", "how many PRs",
  "usage report",
  or wants to review their session activity. Also use when the user asks about their habits,
  patterns, or productivity in Claude Code or OpenCode sessions.
metadata:
  opencode/slash: "true"
---

# Stats

Parse the current session's transcript (Claude Code) or the session store
(OpenCode) and present a compact usage dashboard.

## How It Works

A bundled Python script (`scripts/stats.py`) does all the heavy lifting — single-pass
JSONL parsing (Claude Code) or read-only SQLite reads against the OpenCode store
(`~/.local/share/opencode/opencode.db`, never write-locked). Zero tokens spent on
interpretation. You just run the script, read the JSON output, and format it using
the template below.

## Step 1: Pick the Harness (auto-detected)

The script auto-detects the data source: OpenCode environment variables win,
then Claude Code, then the OpenCode store (if it has sessions for the current
directory). Override
explicitly with `--harness opencode` or `--harness claude` when auto-detection
picks the wrong side.

- **Claude Code**: the current session's transcript is a `.jsonl` file in
  `~/.claude/projects/<project-hash>/<session-uuid>.jsonl`
- **OpenCode**: sessions live in `~/.local/share/opencode/opencode.db`; scope is
  resolved from the session's recorded working directory

For Claude Code, find the project directory and the most recent session file:

```bash
ls -t ~/.claude/projects/$(pwd | sed 's|/|-|g')/*.jsonl 2>/dev/null | head -1
```

If that fails (path mangling mismatch), try:

```bash
ls -dt ~/.claude/projects/*/ | while read d; do
  if echo "$d" | grep -q "$(basename $(pwd))"; then
    ls -t "$d"*.jsonl 2>/dev/null | head -1
    break
  fi
done
```

## Step 2: Run the Script

The script lives at `scripts/stats.py` relative to this skill's base directory.

### Current session (default)
```bash
python3 <skill-base-dir>/scripts/stats.py --cwd "$(pwd)"
```

### All sessions in current project
```bash
python3 <skill-base-dir>/scripts/stats.py --all --cwd "$(pwd)"
```

### All sessions across all projects
```bash
python3 <skill-base-dir>/scripts/stats.py --global
```

For Claude Code you may also pass the transcript path or project directory
directly as the positional argument, as before:

```bash
python3 <skill-base-dir>/scripts/stats.py <path-to-session.jsonl>
```

## Step 3: Present the Results

Parse the JSON output and format using this exact template. Omit sections where all values
are zero.

### Single Session Template

```
Session Stats (<duration_display>)
  Slash commands:  <each command × count, space-separated, top 6>
  Tool calls:      <top 5 tools with counts, separated by " · ">
  Git:             <N> commits · <N> MRs/PRs created · <files_modified + files_created> files touched
  Agents:          <N> spawned (<breakdown by type>)
  Docs:            <LESSONS.md +N> · <CLAUDE.md +N> · <AGENTS.md +N> · <N memory files>
```

### Aggregate Template (--all or --global)

```
All Sessions (<session_count> sessions, <duration_display> total)
  Slash commands:  <each command × count, space-separated, top 8>
  Tool calls:      <top 5 tools with counts, separated by " · ">
  Git:             <N> commits · <N> MRs/PRs · <files touched> files touched
  Agents:          <N> spawned (<breakdown by type>)
  Docs:            LESSONS.md +<N> · CLAUDE.md +<N> · AGENTS.md +<N> · <N> memory files
```

### Formatting Rules

- Use × (multiplication sign) for counts: `/compact ×12`
- Use · (middle dot) as separator for tool counts: `Bash 1301 · Read 370`
- Keep it to one line per category — no tables, no headers, no markdown formatting
- If a category has zero activity, omit the entire line
- For slash commands, show top 6 (single) or top 8 (aggregate)
- For tool calls, show top 5 by count
- Round duration to hours and minutes

## Flags

| Flag | Behavior |
|------|----------|
| (none) | Current session, current project |
| `--all` | All sessions, current project |
| `--global` | All sessions, all projects |
