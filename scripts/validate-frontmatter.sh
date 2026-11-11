#!/usr/bin/env bash
#
# validate-frontmatter.sh — deterministic frontmatter conformance check
# for every skill in this repo.
#
# Checks per plugins/<plugin>/skills/<name>/SKILL.md:
#   - frontmatter block exists and parses as YAML
#   - `name` present, lowercase-hyphen form
#   - `name` matches the parent folder name (Cursor requirement)
#   - `description` present and non-empty
#   - `metadata.opencode/slash` is exactly the quoted string "true"
#
# Exit 0 = all pass. Exit 1 = at least one violation (each named).
# Exit 2 = environment problem (python3/pyyaml missing).
#
# Usage: scripts/validate-frontmatter.sh [repo-root]

set -euo pipefail

REPO="${1:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"

command -v python3 >/dev/null || { printf 'validate-frontmatter: python3 not found\n' >&2; exit 2; }

python3 - "$REPO" <<'PYEOF'
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("validate-frontmatter: pyyaml not available — install with: pip3 install pyyaml", file=sys.stderr)
    sys.exit(2)

repo = Path(sys.argv[1])
skills = sorted(repo.glob("plugins/*/skills/*/SKILL.md"))
if not skills:
    print(f"validate-frontmatter: no SKILL.md files found under {repo}/plugins", file=sys.stderr)
    sys.exit(1)

failures = 0
for p in skills:
    folder = p.parent.name
    text = p.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not m:
        print(f"FAIL {p}: no frontmatter block")
        failures += 1
        continue
    try:
        d = yaml.safe_load(m.group(1))
    except yaml.YAMLError as e:
        print(f"FAIL {p}: YAML parse error: {e}")
        failures += 1
        continue
    if not isinstance(d, dict):
        print(f"FAIL {p}: frontmatter is not a mapping")
        failures += 1
        continue

    name = d.get("name")
    if not name or not isinstance(name, str):
        print(f"FAIL {p}: missing or non-string 'name'")
        failures += 1
    elif not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", name):
        print(f"FAIL {p}: 'name' not lowercase-hyphen form: {name!r}")
        failures += 1
    elif name != folder:
        print(f"FAIL {p}: 'name' {name!r} != parent folder {folder!r} (Cursor requirement)")
        failures += 1

    desc = d.get("description")
    if not desc or not str(desc).strip():
        print(f"FAIL {p}: missing or empty 'description'")
        failures += 1

    meta = d.get("metadata")
    slash = meta.get("opencode/slash") if isinstance(meta, dict) else None
    if slash != "true":
        print(f"FAIL {p}: metadata.opencode/slash is {slash!r}, expected \"true\"")
        failures += 1

if failures:
    print(f"validate-frontmatter: {failures} violation(s)")
    sys.exit(1)
print(f"validate-frontmatter: all {len(skills)} skills conform")
PYEOF
