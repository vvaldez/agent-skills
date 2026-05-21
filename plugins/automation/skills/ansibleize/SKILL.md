---
name: ansibleize
description: >
  Audit and refactor any codebase to follow battle-tested Ansible automation patterns.
  Works on existing Ansible (roles, playbooks, collections), bash/PowerShell scripts,
  and loose automation code. Produces a pattern-categorized audit report, then fixes
  what you approve. Use when user says /ansibleize, "make this proper Ansible",
  "refactor to Ansible", "audit this Ansible code", "convert this script to Ansible",
  "check Ansible patterns", "ansible best practices review", or wants to improve
  Ansible code quality. Also trigger when reviewing Ansible PRs/MRs or onboarding
  to an existing Ansible codebase.
---

# Ansibleize

Audit and refactor automation code against battle-tested Ansible patterns developed over
11+ years of production use. Produces a categorized findings report, then applies fixes
you approve.

## Before You Begin

1. **Read the patterns reference**: `references/ansible-automation-patterns.md` — the
   authoritative patterns this skill enforces. Read the Table of Contents to understand
   the pattern categories, then read sections as needed during the audit.

2. **Read the CoP baseline**: `references/ansible-cop-baseline.md` — Red Hat Community
   of Practice standards. These are the floor; the patterns reference is the ceiling.

3. **Detect what you're looking at** — the skill adapts to the input:

   | Input | Approach |
   |-------|----------|
   | Ansible collection | Full audit against all pattern categories |
   | Ansible roles/playbooks | Audit applicable patterns, suggest collection structure |
   | Bash/PowerShell scripts | Convert to Ansible tasks following the patterns |
   | Chef/Puppet code | Note that [x2ansible](https://github.com/x2ansible/) exists for dedicated migration, offer to help with post-conversion pattern compliance |

## Phase 1: Audit

Scan the codebase and produce a findings report categorized by pattern area. For each
finding, note the severity and the specific file/line.

### Pattern Categories

Audit in this order — each category builds on the previous:

#### 1. Module Hierarchy Compliance

Check the module priority hierarchy from the patterns reference:

| Tier | Source | Requirement |
|------|--------|-------------|
| 1 | Certified (`redhat.*`, `ansible.builtin.*`) | Preferred |
| 2 | Validated (`cloud.*`, `infra.*`) | Acceptable |
| 3 | Community (`community.general.*`) | Requires justification |
| 4 | Command/Shell | Last resort — search `ansible-doc -l` first |

Flag any `ansible.builtin.command`, `ansible.builtin.shell`, or `ansible.builtin.raw`
task that has a proper module replacement. This is the most common violation.

#### 2. Vault and Security

- Hardcoded credentials or passwords (any format)
- Missing `no_log` on tasks handling secrets
- `no_log: true` hardcoded instead of toggleable (`no_log: "{{ role_secure_logging }}"`)
- Empty string defaults for required credentials
- Vault files committed or tracked in git

#### 3. Role Structure

- Missing `argument_specs.yml` (REQUIRED for all roles)
- Missing or incomplete `meta/main.yml`
- Variables not namespaced with role prefix
- Internal variables not using `__` prefix
- Missing distribution-specific variable files

#### 4. Task Patterns

- `fail` + `when` instead of `assert` for validation
- Missing `loop_control.loop_var` on loops (NEVER use bare `item`)
- Missing task names
- Missing FQCN on module names
- `set_fact` + `loop` for filtering instead of `select`/`map` filters
- `delegate_to: localhost` on `set_fact` (unnecessary for lookups)

#### 5. Tagging

- Missing tags on tasks
- Tag inheritance gotchas (block-level tags propagating unexpectedly)
- Missing `never` tag on destructive operations
- Lifecycle tags not following the pattern: `always`, `setup`, `install`, `configure`, `teardown`, `never`

#### 6. Idempotency

- Tasks that aren't idempotent (create without check, missing `creates`/`removes`)
- External CLI tool operations not following the 6-step pattern
- Missing `changed_when` / `failed_when` on command tasks

#### 7. Variable Management

- Variables not namespaced with role prefix
- Missing defaults for optional variables
- Required variables without `assert` validation at role entry
- `gather_facts: true` on plays with phase gates (should be `false`)

#### 8. ISO Building (if applicable)

- Only audit this category if the codebase involves ISO creation, cloud-init, or kickstart
- Check against the ISO building patterns section of the reference

### Audit Report Format

Present findings grouped by category. Use this format:

```
Ansibleize Audit — <codebase name>

1. Module Hierarchy
   [MUST-FIX] roles/deploy/tasks/main.yml:42 — shell task `curl` has module replacement `ansible.builtin.uri`
   [MUST-FIX] roles/setup/tasks/main.yml:18 — command task `useradd` → use `ansible.builtin.user`
   [OK] No other command/shell tasks found

2. Vault and Security
   [MUST-FIX] roles/auth/defaults/main.yml:3 — empty string default for `auth_password`
   [SUGGEST] roles/deploy/tasks/main.yml:55 — add `no_log` with toggleable variable

3. Role Structure
   [MUST-FIX] roles/deploy/ — missing argument_specs.yml
   ...

Summary: 8 must-fix · 3 suggestions · 5 categories clean
```

Severity levels:
- **MUST-FIX**: Violates a hard rule from the patterns reference
- **SUGGEST**: Improvement opportunity, not a violation
- **OK**: Category passes — still list it so the user sees full coverage

## Phase 2: Fix

After presenting the audit report, ask the user what to fix. Options:

1. **Fix all MUST-FIX items** — apply all hard rule violations
2. **Fix specific categories** — user picks which categories to address
3. **Fix specific items** — user picks individual findings
4. **Export report only** — no changes, just the audit

When applying fixes:
- Follow all patterns from the references exactly
- Use long-form CLI options in any generated command tasks
- Use FQCN for all module names
- Add `argument_specs.yml` using `ansible-creator` if available
- Test changes if a molecule scenario exists

## Script Conversion (Bash/PowerShell)

When the input is a script, not Ansible:

1. Read the script and identify what it does
2. Map each operation to the appropriate Ansible module (Tier 1 preferred)
3. Generate an Ansible role following the patterns reference:
   - Proper directory structure
   - `argument_specs.yml` for all parameters
   - Distribution-specific variable files if needed
   - Idempotent tasks with proper `changed_when`
4. Present the generated role for review before writing

For Chef/Puppet codebases, recommend [x2ansible](https://github.com/x2ansible/) for
the initial conversion, then offer to run an audit on the converted output.

## Integrating with CLAUDE.md

The patterns enforced by this skill should also guide everyday Ansible coding — not just
explicit `/ansibleize` audits. Add this to your project's `CLAUDE.md` so the patterns are
ambient context for all Ansible work:

```markdown
## Ansible Patterns

Follow the patterns in the /ansibleize skill's reference documents for all Ansible work.
When the agent-skills plugin is installed, the references are at:

  ~/.claude/plugins/cache/agent-skills/automation/*/skills/ansibleize/references/

Read `ansible-automation-patterns.md` before writing or modifying any Ansible code.
Read `ansible-cop-baseline.md` for Red Hat Community of Practice baseline standards.

For a full codebase audit, invoke `/ansibleize`.
```

This gives you two access paths to the same source of truth:
- **Everyday coding**: CLAUDE.md points the agent to the reference docs. Patterns are
  consulted automatically when writing Ansible without invoking the skill.
- **Deliberate audit**: `/ansibleize` runs a structured audit-then-fix workflow using
  the same references but with categorized reporting and approval gates.

## Constraints

- NEVER skip the audit phase — always report before fixing
- NEVER use `ansible.builtin.command` or `ansible.builtin.shell` when a proper module exists
- NEVER hardcode `no_log: true` — always use a toggleable variable
- NEVER use bare `item` as a loop variable
- ALWAYS use FQCN for module names
- ALWAYS create `argument_specs.yml` for new roles
- ALWAYS validate required variables with `assert` at role entry
