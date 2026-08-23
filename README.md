# Agent Skills

Developer workflow and automation skills for AI coding agents. Built for daily use, not demos.

## Skills

### Dev Workflow

| Skill | Description |
|-------|-------------|
| `/tidy` | Gentle git housekeeping — fetch, prune, report branches, auto-delete merged, confirm unmerged |
| `/ship` | Unified MR/PR workflow — detect state, branch, commit, push, create merge/pull request |
| `/stats` | Session statistics dashboard — slash commands, tool calls, MRs, commits, doc edits |

### Automation

| Skill | Description |
|-------|-------------|
| `/ansibleize` | Audit and refactor any codebase to follow battle-tested Ansible patterns — module hierarchy, vault/security, role structure, tagging, idempotency. Converts bash/PowerShell scripts to proper Ansible. |

### Diagrams

| Skill | Description |
|-------|-------------|
| `/diagram` | Red Hat branded process flow diagrams — self-contained HTML with auto-PNG export. Nodes, arrows, decisions, dividers, watermarks. |

### Grilling Extras

| Skill | Description |
|-------|-------------|
| `/grill-harness` | Adversarial grilling harness — assembles expert panel from `~/.claude/agents/`, adds structured decision tables, enhanced CONTEXT.md format. Extends upstream `/grilling`. |

### Handoff Extras

| Skill | Description |
|-------|-------------|
| `/handoff-issue` | Session handoffs as GitHub issues — labeled `handoff`, close-when-consumed, dedup against existing tracked work. Extends upstream `/handoff`; falls back to markdown when no tracker. |

### Local Model

| Skill | Description |
|-------|-------------|
| `/local-review` | Cheap first-pass diff review by a locally-hosted model — working tree, staged, or a branch against `main`. The diff goes to the GPU; only a short candidate list comes back, so it costs almost no context. Findings are pointers to check, not verdicts. |

## Install

### Claude Code

From the terminal:

```bash
claude plugins marketplace add vvaldez/agent-skills
claude plugins install dev-workflow@vvaldez-agent-skills
claude plugins install automation@vvaldez-agent-skills
claude plugins install diagrams@vvaldez-agent-skills
claude plugins install grilling-extras@vvaldez-agent-skills
claude plugins install handoff-extras@vvaldez-agent-skills
claude plugins install local-model@vvaldez-agent-skills
```

Or from inside a Claude Code session:

```
/plugin marketplace add vvaldez/agent-skills
/plugin install dev-workflow@vvaldez-agent-skills
/plugin install automation@vvaldez-agent-skills
/plugin install diagrams@vvaldez-agent-skills
/plugin install grilling-extras@vvaldez-agent-skills
/plugin install handoff-extras@vvaldez-agent-skills
/plugin install local-model@vvaldez-agent-skills
/reload-plugins
```

To update after new releases (CLI only — `/plugin update` is not available in-session):

```bash
claude plugins update dev-workflow@vvaldez-agent-skills
claude plugins update automation@vvaldez-agent-skills
claude plugins update diagrams@vvaldez-agent-skills
claude plugins update grilling-extras@vvaldez-agent-skills
claude plugins update handoff-extras@vvaldez-agent-skills
claude plugins update local-model@vvaldez-agent-skills
```

Then reload in your active session:

```
/reload-plugins
```

### Ambient Ansible Patterns (CLAUDE.md Integration)

The `/ansibleize` skill includes comprehensive Ansible pattern references. You can make
these patterns available as ambient context for **all** Ansible work — not just explicit
`/ansibleize` audits — by adding this to your project's `CLAUDE.md`:

```markdown
## Ansible Patterns

Follow the patterns in the /ansibleize skill's reference documents for all Ansible work.
When the agent-skills plugin is installed, the references are at:

  ~/.claude/plugins/cache/vvaldez-agent-skills/automation/*/skills/ansibleize/references/

Read `ansible-patterns.md` for core Ansible patterns.
Read `ansible-automation-platform-patterns.md` for AAP-specific patterns (content tiers, secure logging).
Read `ansible-cop-baseline.md` for Red Hat Community of Practice baseline standards.

For a full codebase audit, invoke `/ansibleize`.
```

This gives you two access paths to the same source of truth:
- **Everyday coding**: CLAUDE.md points the agent to the reference docs. Patterns are
  consulted automatically when writing Ansible.
- **Deliberate audit**: `/ansibleize` runs a structured audit-then-fix workflow with
  categorized reporting and approval gates.

### Other Agents

Skills follow the [Agent Skills](https://agentskills.io) open standard. Copy the relevant
`SKILL.md` files into your agent's skill directory.

## Requirements

- **`/tidy`**: `git`
- **`/ship`**: `git` + `glab` (GitLab) or `gh` (GitHub) — auto-detected from remote URL
- **`/stats`**: `python3`
- **`/ansibleize`**: Ansible knowledge (reads bundled reference docs, no external deps)
- **`/diagram`**: Puppeteer for auto-PNG (`npx -y @mermaid-js/mermaid-cli` installs it)
- **`/grill-harness`**: Optional: `~/.claude/agents/` with expert personas (e.g., from [agency-agents](https://github.com/msitarzewski/agency-agents)). Works without agents but panel feature is skipped.
- **`/handoff-issue`**: `gh` (GitHub CLI, authenticated). Without it, falls back to upstream `/handoff` markdown behavior.
- **`/local-review`**: Windows + PowerShell 5.1, an LM Studio worker with a model loaded, and the `localllm` tooling — **not bundled here**. Set `LOCALLLM_HOME` if it is not at `~/tools/localllm`. Without it the skill reports the tool as missing and stops; it deliberately does not fall back to reviewing the diff itself, since that would spend the context the skill exists to save.

## License

MIT
