#!/usr/bin/env python3
"""Parse Claude Code JSONL transcripts or the OpenCode session store and produce usage statistics."""

import argparse
import json
import os
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path


def parse_session(path: Path) -> dict:
    """Parse a single JSONL transcript and return stats dict."""
    slash_commands: Counter = Counter()
    tool_calls: Counter = Counter()
    files_modified: set = set()
    files_created: set = set()
    mrs_created: dict = {}  # title -> count, deduplicates compaction replays
    commits: dict = {}  # subject -> count, deduplicates compaction replays
    agents_spawned: Counter = Counter()
    doc_edits = {"lessons_md": 0, "claude_md": 0, "agents_md": 0}
    memory_files_created = 0
    timestamps: list = []

    with open(path) as f:
        for line in f:
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue

            ts = rec.get("timestamp")
            if ts:
                timestamps.append(ts)

            rtype = rec.get("type")

            if rtype == "user":
                msg = rec.get("message", {})
                content = msg.get("content", "")
                if isinstance(content, str):
                    _extract_commands(content, slash_commands)
                elif isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict):
                            text = block.get("text", "")
                            if text:
                                _extract_commands(text, slash_commands)
                            tc = block.get("content", "")
                            if isinstance(tc, str):
                                _extract_commands(tc, slash_commands)

            if rtype == "assistant":
                msg = rec.get("message", {})
                content = msg.get("content", [])
                if not isinstance(content, list):
                    continue
                for block in content:
                    if not isinstance(block, dict):
                        continue
                    if block.get("type") != "tool_use":
                        continue

                    name = block.get("name", "?")
                    tool_calls[name] += 1
                    inp = block.get("input", {})

                    fp = inp.get("file_path", "")
                    if name == "Write" and fp:
                        files_created.add(fp)
                        _check_doc_edit(fp, doc_edits)
                        if "/memory/" in fp:
                            memory_files_created += 1
                    elif name == "Edit" and fp:
                        files_modified.add(fp)
                        _check_doc_edit(fp, doc_edits)

                    if name == "Bash":
                        cmd = inp.get("command", "")
                        if "git commit" in cmd and "--amend" not in cmd:
                            subj = _extract_commit_subject(cmd)
                            commits[subj] = commits.get(subj, 0) + 1
                        if "glab mr create" in cmd or "gh pr create" in cmd:
                            title_match = re.search(r'--title\s+["\'](.+?)["\']', cmd)
                            mr_title = title_match.group(1) if title_match else "(MR/PR)"
                            mrs_created[mr_title] = mrs_created.get(mr_title, 0) + 1

                    if name == "Agent":
                        agent_type = inp.get("subagent_type", "general")
                        agents_spawned[agent_type] += 1

    active_seconds = _calc_active_duration(timestamps)

    return {
        "session_file": path.name,
        "duration_seconds": active_seconds,
        "duration_display": _format_duration(active_seconds),
        "slash_commands": dict(slash_commands.most_common()),
        "slash_commands_total": sum(slash_commands.values()),
        "tool_calls": dict(tool_calls.most_common()),
        "tool_calls_total": sum(tool_calls.values()),
        "files_modified": len(files_modified),
        "files_created": len(files_created),
        "mrs_created": list(mrs_created.keys()),
        "mrs_total": len(mrs_created),
        "commits": list(commits.keys()),
        "commits_total": len(commits),
        "agents_spawned": dict(agents_spawned.most_common()),
        "agents_total": sum(agents_spawned.values()),
        "doc_edits": doc_edits,
        "memory_files_created": memory_files_created,
    }


def _extract_commands(text: str, counter: Counter):
    for match in re.finditer(r"<command-name>(/[^<]+)</command-name>", text):
        counter[match.group(1)] += 1


def _extract_commit_subject(cmd: str) -> str:
    """Extract commit message subject from git commit command, handling HEREDOC."""
    # git commit -m "$(cat <<'EOF' ... )" — the OpenCode bash form
    heredoc = re.search(r"<<-?'?EOF'?\n(.+?)(?:\n|$)", cmd, re.DOTALL)
    if heredoc:
        return heredoc.group(1).strip().split("\n")[0][:70]
    msg_match = re.search(r'-m\s+"([^"]+)"', cmd)
    if msg_match:
        return msg_match.group(1).split("\n")[0][:70]
    msg_match = re.search(r"-m\s+'([^']+)'", cmd)
    if msg_match:
        return msg_match.group(1).split("\n")[0][:70]
    return "(commit)"


def _check_doc_edit(fp: str, doc_edits: dict):
    basename = Path(fp).name.lower()
    if basename == "lessons.md":
        doc_edits["lessons_md"] += 1
    elif basename == "claude.md":
        doc_edits["claude_md"] += 1
    elif basename == "agents.md":
        doc_edits["agents_md"] += 1


def _parse_ts(ts: str) -> datetime | None:
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def _calc_active_duration(timestamps: list[str]) -> int:
    """Estimate active duration by summing gaps under 10 minutes."""
    if len(timestamps) < 2:
        return 0
    parsed = [_parse_ts(t) for t in timestamps]
    parsed = [t for t in parsed if t is not None]
    if len(parsed) < 2:
        return 0
    parsed.sort()
    gap_threshold = 600  # 10 minutes
    active = 0
    for i in range(1, len(parsed)):
        gap = (parsed[i] - parsed[i - 1]).total_seconds()
        if gap <= gap_threshold:
            active += gap
    return max(0, int(active))


def _format_duration(seconds: int) -> str:
    if seconds < 60:
        return f"{seconds}s"
    hours, rem = divmod(seconds, 3600)
    mins = rem // 60
    if hours:
        return f"{hours}h {mins}m"
    return f"{mins}m"


def aggregate_sessions(sessions: list[dict]) -> dict:
    """Aggregate stats across multiple sessions."""
    slash_total: Counter = Counter()
    tool_total: Counter = Counter()
    agents_total: Counter = Counter()
    total_duration = 0
    total_files_modified = 0
    total_files_created = 0
    all_mrs: set = set()
    all_commits: set = set()
    total_lessons = 0
    total_claude = 0
    total_agents_md = 0
    total_memory = 0

    for s in sessions:
        slash_total.update(s["slash_commands"])
        tool_total.update(s["tool_calls"])
        agents_total.update(s["agents_spawned"])
        total_duration += s["duration_seconds"]
        total_files_modified += s["files_modified"]
        total_files_created += s["files_created"]
        all_mrs.update(s["mrs_created"])
        all_commits.update(s["commits"])
        total_lessons += s["doc_edits"]["lessons_md"]
        total_claude += s["doc_edits"]["claude_md"]
        total_agents_md += s["doc_edits"]["agents_md"]
        total_memory += s["memory_files_created"]

    return {
        "session_count": len(sessions),
        "duration_seconds": total_duration,
        "duration_display": _format_duration(total_duration),
        "slash_commands": dict(slash_total.most_common()),
        "slash_commands_total": sum(slash_total.values()),
        "tool_calls": dict(tool_total.most_common()),
        "tool_calls_total": sum(tool_total.values()),
        "files_modified": total_files_modified,
        "files_created": total_files_created,
        "mrs_created": sorted(all_mrs),
        "mrs_total": len(all_mrs),
        "commits": sorted(all_commits),
        "commits_total": len(all_commits),
        "agents_spawned": dict(agents_total.most_common()),
        "agents_total": sum(agents_total.values()),
        "doc_edits": {
            "lessons_md": total_lessons,
            "claude_md": total_claude,
            "agents_md": total_agents_md,
        },
        "memory_files_created": total_memory,
    }


def find_project_dir(cwd: str) -> Path | None:
    """Find the Claude project directory for the given working directory."""
    projects_dir = Path.home() / ".claude" / "projects"
    if not projects_dir.exists():
        return None
    mangled = cwd.replace("/", "-")
    target = projects_dir / mangled
    if target.exists():
        return target
    for d in projects_dir.iterdir():
        if d.is_dir() and mangled in d.name:
            return d
    return None


def find_sessions(project_dir: Path) -> list[Path]:
    """Find all JSONL session files in a project directory."""
    return sorted(project_dir.glob("*.jsonl"), key=lambda p: p.stat().st_mtime)


# ---------------------------------------------------------------------------
# OpenCode store backend (opencode.db, read-only)
# ---------------------------------------------------------------------------
# Store schema (OpenCode v2): session_v2 (one row per session, ms-epoch
# time_created/time_updated, directory), session_message (type, data JSON —
# user text under $.text), part (tool invocations: $.tool, $.state.input,
# ms-epoch $.time.created). Connected via a read-only URI — never takes a
# write lock against the live store. Schema-mapping prior art:
# fieldcto-na dev-tools bin/gather-tooling-stats (session_message vs legacy
# message fallback, $.tokens/$.model paths).

def _oc_db_path() -> Path:
    return Path.home() / ".local" / "share" / "opencode" / "opencode.db"


def _oc_connect(db_path: Path):
    import sqlite3
    if not db_path.exists():
        return None
    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        conn.execute("SELECT 1 FROM session_v2 LIMIT 1")
        return conn
    except sqlite3.DatabaseError:
        return None


def _oc_select_sessions(conn, cwd: str, all_flag: bool, global_flag: bool) -> list[str]:
    """Resolve session ids by scope: current = latest session under cwd
    (latest overall as a last resort); --all = every session under cwd;
    --global = every session."""
    if global_flag:
        rows = conn.execute(
            "SELECT id FROM session_v2 ORDER BY time_updated").fetchall()
        return [r[0] for r in rows]
    # environment-named session wins (the live harness knows its own id) —
    # but only if it has tool activity; stub/title sessions carry zero
    # parts and would present an empty dashboard
    env_sid = os.environ.get("OPENCODE_SESSION_ID")
    if env_sid and not all_flag and not global_flag:
        row = conn.execute(
            "SELECT s.id FROM session_v2 s "
            "WHERE s.id = ? AND EXISTS (SELECT 1 FROM part p "
            "WHERE p.session_id = s.id AND json_extract(p.data,'$.tool') "
            "IS NOT NULL)", (env_sid,)).fetchone()
        if row:
            return [row[0]]
    if all_flag:
        rows = conn.execute(
            "SELECT id FROM session_v2 WHERE directory = ? ORDER BY time_updated",
            (cwd,)).fetchall()
        if not rows:
            # '/%' boundary: a sibling directory sharing the prefix must
            # not match ('/a/b/foo' must not catch cwd '/a/b/foobar')
            rows = conn.execute(
                "SELECT id FROM session_v2 WHERE ? LIKE directory || '/%' "
                "ORDER BY time_updated", (cwd,)).fetchall()
        return [r[0] for r in rows]
    row = conn.execute(
        "SELECT id FROM session_v2 WHERE directory = ? "
        "ORDER BY time_updated DESC LIMIT 1", (cwd,)).fetchone()
    if not row:
        row = conn.execute(
            "SELECT id FROM session_v2 WHERE ? LIKE directory || '/%' "
            "ORDER BY time_updated DESC LIMIT 1", (cwd,)).fetchone()
    if not row:
        # no sessions for this directory: fail loud rather than present
        # an unrelated session's stats as "the current session"
        return []
    return [row[0]]


def _oc_parse_session(conn, session_id: str) -> dict:
    """Parse one OpenCode session from the store into the shared stats shape."""
    slash_commands: Counter = Counter()
    tool_calls: Counter = Counter()
    files_modified: set = set()
    files_created: set = set()
    mrs_created: dict = {}
    commits: dict = {}
    agents_spawned: Counter = Counter()
    doc_edits = {"lessons_md": 0, "claude_md": 0, "agents_md": 0}
    memory_files_created = 0
    activity: list[int] = []

    for tool, inp, created in conn.execute(
            "SELECT json_extract(data,'$.tool'), json_extract(data,'$.state.input'), "
            "time_created FROM part "
            "WHERE session_id = ? AND json_extract(data,'$.tool') IS NOT NULL",
            (session_id,)):
        if created:
            activity.append(created)
        tool_calls[tool] += 1

        # json_extract returns object paths as their JSON serialization —
        # decode before dict access.
        if isinstance(inp, str):
            try:
                inp = json.loads(inp)
            except json.JSONDecodeError:
                inp = {}
        if not isinstance(inp, dict):
            inp = {}

        if tool == "skill":
            # skill invocations double as slash-command usage
            name = (inp or {}).get("name")
            if name:
                slash_commands[f"/{name}"] += 1
        elif tool in ("edit", "write"):
            fp = (inp or {}).get("filePath", "")
            if fp:
                if tool == "write":
                    files_created.add(fp)
                else:
                    files_modified.add(fp)
                _check_doc_edit(fp, doc_edits)
                if "/memory/" in fp:
                    memory_files_created += 1
        elif tool == "bash":
            cmd = (inp or {}).get("command", "")
            if "git commit" in cmd and "--amend" not in cmd:
                subj = _extract_commit_subject(cmd)
                commits[subj] = commits.get(subj, 0) + 1
            # covers both `glab mr create` and the wrapper form
            # (`mr-create-with-attribution glab-cee mr create ...`), plus gh
            if ("mr create" in cmd and "glab" in cmd) or "gh pr create" in cmd:
                title_match = re.search(r'--title\s+["\'](.+?)["\']', cmd)
                mr_title = title_match.group(1) if title_match else "(MR/PR)"
                mrs_created[mr_title] = mrs_created.get(mr_title, 0) + 1
        elif tool == "task":
            agents_spawned["subagent"] += 1

    # typed slash commands from user message text (first token only)
    for (text,) in conn.execute(
            "SELECT json_extract(data,'$.text') FROM session_message "
            "WHERE session_id = ? AND type = 'user' AND data IS NOT NULL",
            (session_id,)):
        if isinstance(text, str) and text.startswith("/"):
            first = text.split()[0]
            # only command-shaped tokens: /name (lowercase, dashes) — a
            # message starting with a path ("/Users/...", "/etc/hosts")
            # is not a slash command
            if not re.match(r"^/[a-z][a-z0-9-]*$", first):
                continue
            # avoid double-counting: the skill-tool row is the authoritative
            # invocation record; typed text only adds commands with no part
            if slash_commands.get(first, 0) == 0:
                slash_commands[first] += 1

    row = conn.execute(
        "SELECT id, slug, time_created, time_updated FROM session_v2 "
        "WHERE id = ?", (session_id,)).fetchone()
    if not row:
        # session deleted between the id listing and this read
        return {
            "session_file": f"{session_id[:8]} (deleted mid-read)",
            "duration_seconds": 0, "duration_display": "0m",
            "slash_commands": {}, "slash_commands_total": 0,
            "tool_calls": {}, "tool_calls_total": 0,
            "files_modified": 0, "files_created": 0,
            "mrs_created": [], "mrs_total": 0,
            "commits": [], "commits_total": 0,
            "agents_spawned": {}, "agents_total": 0,
            "doc_edits": doc_edits, "memory_files_created": 0,
        }
    sid, slug, t_created, t_updated = row

    active_seconds = _calc_active_duration_ms(activity)
    if active_seconds == 0 and t_created and t_updated:
        active_seconds = max(0, int((t_updated - t_created) / 1000))

    return {
        "session_file": f"{slug} ({sid[:8]})",
        "duration_seconds": active_seconds,
        "duration_display": _format_duration(active_seconds),
        "slash_commands": dict(slash_commands.most_common()),
        "slash_commands_total": sum(slash_commands.values()),
        "tool_calls": dict(tool_calls.most_common()),
        "tool_calls_total": sum(tool_calls.values()),
        "files_modified": len(files_modified),
        "files_created": len(files_created),
        "mrs_created": list(mrs_created.keys()),
        "mrs_total": len(mrs_created),
        "commits": list(commits.keys()),
        "commits_total": len(commits),
        "agents_spawned": dict(agents_spawned.most_common()),
        "agents_total": sum(agents_spawned.values()),
        "doc_edits": doc_edits,
        "memory_files_created": memory_files_created,
    }


def _calc_active_duration_ms(stamps_ms: list[int]) -> int:
    """Same gap-threshold algorithm as the Claude parser, on ms epochs."""
    if len(stamps_ms) < 2:
        return 0
    stamps = sorted(stamps_ms)
    gap_threshold_ms = 600_000  # 10 minutes
    active = 0
    for i in range(1, len(stamps)):
        gap = stamps[i] - stamps[i - 1]
        if 0 <= gap <= gap_threshold_ms:
            active += gap
    return max(0, active // 1000)


def _detect_harness(explicit: str, cwd: str) -> str:
    """auto: env vars name the live harness; fall back to whichever data
    source has sessions for the working directory."""
    if explicit != "auto":
        return explicit
    if os.environ.get("OPENCODE") or os.environ.get("OPENCODE_SESSION_ID"):
        return "opencode"
    if os.environ.get("CLAUDECODE") or os.environ.get("CLAUDE_CODE_ENTRYPOINT"):
        return "claude"
    if (_oc_db_path()).exists():
        import sqlite3
        conn = _oc_connect(_oc_db_path())
        if conn:
            try:
                row = conn.execute(
                    "SELECT COUNT(*) FROM session_v2 WHERE ? LIKE directory || '/%'",
                    (cwd,)).fetchone()
                if row and row[0] > 0:
                    return "opencode"
            finally:
                conn.close()
    return "claude"


def main():
    parser = argparse.ArgumentParser(description="Session statistics (Claude Code JSONL or OpenCode store)")
    parser.add_argument("path", nargs="?", help="Path to session .jsonl or project directory")
    parser.add_argument("--all", action="store_true", help="Aggregate all sessions in project")
    parser.add_argument("--global", dest="global_flag", action="store_true",
                        help="Aggregate across all projects")
    parser.add_argument("--cwd", default=".", help="Current working directory for project discovery")
    parser.add_argument("--harness", choices=("auto", "claude", "opencode"), default="auto",
                        help="Data source: Claude Code JSONL transcripts or the OpenCode session store")
    args = parser.parse_args()
    cwd = str(Path(args.cwd).resolve())

    if args.harness == "auto":
        args.harness = _detect_harness("auto", cwd)

    if args.harness == "opencode":
        conn = _oc_connect(_oc_db_path())
        if not conn:
            print(json.dumps({"error": f"OpenCode store not found at {_oc_db_path()}"}))
            sys.exit(1)
        try:
            session_ids = _oc_select_sessions(conn, cwd, args.all, args.global_flag)
            if not session_ids:
                print(json.dumps({"error": f"No sessions found in the OpenCode store for {cwd}"}))
                sys.exit(1)
            sessions = [_oc_parse_session(conn, sid) for sid in session_ids]
            result = (aggregate_sessions(sessions)
                      if (args.all or args.global_flag or len(sessions) > 1)
                      else sessions[0])
            print(json.dumps(result, indent=2))
        finally:
            conn.close()
        return

    # --- Claude Code JSONL backend (unchanged below) ---
    if args.global_flag:
        projects_dir = Path.home() / ".claude" / "projects"
        if not projects_dir.exists():
            print(json.dumps({"error": "No projects directory found"}))
            sys.exit(1)
        all_sessions = []
        for proj in projects_dir.iterdir():
            if proj.is_dir():
                for f in find_sessions(proj):
                    all_sessions.append(parse_session(f))
        if not all_sessions:
            print(json.dumps({"error": "No sessions found"}))
            sys.exit(1)
        print(json.dumps(aggregate_sessions(all_sessions), indent=2))
        return

    if args.path:
        target = Path(args.path)
    else:
        proj = find_project_dir(args.cwd)
        if not proj:
            print(json.dumps({"error": f"No project directory found for {args.cwd}"}))
            sys.exit(1)
        target = proj

    if target.is_file():
        if args.all:
            project_dir = target.parent
            sessions = [parse_session(f) for f in find_sessions(project_dir)]
            print(json.dumps(aggregate_sessions(sessions), indent=2))
        else:
            print(json.dumps(parse_session(target), indent=2))
    elif target.is_dir():
        sessions_files = find_sessions(target)
        if not sessions_files:
            print(json.dumps({"error": f"No .jsonl files in {target}"}))
            sys.exit(1)
        if args.all:
            sessions = [parse_session(f) for f in sessions_files]
            print(json.dumps(aggregate_sessions(sessions), indent=2))
        else:
            latest = sessions_files[-1]
            print(json.dumps(parse_session(latest), indent=2))
    else:
        print(json.dumps({"error": f"Path not found: {target}"}))
        sys.exit(1)


if __name__ == "__main__":
    main()
