# Agent Skills

Developer workflow skills for AI coding agents. Built for daily use, not demos.

## Skills

| Skill | Description |
|-------|-------------|
| `/tidy` | Gentle git housekeeping — fetch, prune, report branches, auto-delete merged, confirm unmerged |
| `/ship` | Unified MR/PR workflow — detect state, branch, commit, push, create merge/pull request |
| `/stats` | Session statistics dashboard — slash commands, tool calls, MRs, commits, doc edits |

## Install

### Claude Code

```
/install-plugin github:vvaldez/agent-skills
```

### Other Agents

Skills follow the [Agent Skills](https://agentskills.io) open standard. Copy the relevant
`SKILL.md` files into your agent's skill directory.

## Requirements

- **`/tidy`**: `git`
- **`/ship`**: `git` + `glab` (GitLab) or `gh` (GitHub) — auto-detected from remote URL
- **`/stats`**: `python3`

## License

MIT
