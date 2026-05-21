#!/usr/bin/env python3
"""Parse Claude Code session transcripts and produce usage statistics."""

import argparse
import json
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
    heredoc = re.search(r"<<'?EOF'?\n(.+?)(?:\n|$)", cmd, re.DOTALL)
    if heredoc:
        return heredoc.group(1).strip().split("\n")[0][:70]
    msg_match = re.search(r'-m\s+"([^"]+)"', cmd)
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


def main():
    parser = argparse.ArgumentParser(description="Claude Code session statistics")
    parser.add_argument("path", nargs="?", help="Path to session .jsonl or project directory")
    parser.add_argument("--all", action="store_true", help="Aggregate all sessions in project")
    parser.add_argument("--global", dest="global_flag", action="store_true",
                        help="Aggregate across all projects")
    parser.add_argument("--cwd", default=".", help="Current working directory for project discovery")
    args = parser.parse_args()

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
