#!/usr/bin/env bash
#
# refresh-grill-wrappers.sh — restore the custom grill wrapper skills after
# a mattpocock/skills pack update.
#
# WHY THIS EXISTS
#
# The `npx skills@latest add mattpocock/skills` installer clobbers any
# same-named skill in the install dir. Our `grill-me` and `grill-with-docs`
# are thin custom wrappers that compose upstream /grilling (+ /domain-modeling)
# with the /grill-harness enhancements — same names as pack skills, so every
# pack update silently reverts them to upstream versions and the adversarial
# panel stops firing (drift incident 2026-11-11: the pack ALSO moved its
# install location from ~/.claude/skills to ~/.agents/skills, so the old
# ~/.claude/scripts/update-skills-pack.sh was restoring into a dead directory).
#
# Run this AFTER every pack update:
#
#   npx skills@latest add mattpocock/skills && ~/repos/agent-skills/scripts/refresh-grill-wrappers.sh
#
# Source of truth: <repo>/scripts/grill-wrappers/<name>/SKILL.md (versioned
# in git — no separate checksum file needed; `git diff` is the tamper check).
# Target: ~/.agents/skills/<name>/SKILL.md (the pack's current install dir).
#
# The script also verifies /grill-harness itself is deployed somewhere a
# harness reads, and tells you the deploy command if it isn't.

set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WRAPPERS_SRC="${REPO}/scripts/grill-wrappers"
SKILLS_DIR="${HOME}/.agents/skills"

info() { printf 'refresh-grill-wrappers: %s\n' "$1"; }
warn() { printf 'refresh-grill-wrappers: WARN: %s\n' "$1" >&2; }

[[ -d "$WRAPPERS_SRC" ]] || { warn "wrappers source not found: $WRAPPERS_SRC"; exit 1; }
mkdir -p "$SKILLS_DIR"

for name in "$WRAPPERS_SRC"/*/; do
    name="$(basename "$name")"
    src="$WRAPPERS_SRC/$name/SKILL.md"
    dest_dir="$SKILLS_DIR/$name"
    dest="$dest_dir/SKILL.md"

    [[ -f "$src" ]] || { warn "no SKILL.md in $WRAPPERS_SRC/$name, skipping"; continue; }

    # The pack installs skills as symlinks — replace, never write through one.
    if [[ -L "$dest_dir" ]]; then
        rm "$dest_dir"
        info "removed pack symlink: $name"
    fi
    mkdir -p "$dest_dir"
    cp "$src" "$dest"
    info "restored: $name"
done

# --- grill-harness visibility check -----------------------------------------
# The wrappers invoke /grill-harness by name; if no harness-visible location
# has it, the wrappers degrade to plain grilling. Deployed copies live in
# ~/.config/opencode/skills/ (via deploy-local-skills.sh) and the Claude Code
# plugin cache (skill-extras). ~/.claude/skills and ~/.agents/skills are also
# harness-readable locations.
found=""
for cand in \
    "$HOME/.config/opencode/skills/grill-harness/SKILL.md" \
    "$SKILLS_DIR/grill-harness/SKILL.md" \
    "$HOME/.claude/skills/grill-harness/SKILL.md" \
    "$HOME/.claude/plugins/cache/vvaldez-agent-skills"/skill-extras/*/skills/grill-harness/SKILL.md; do
    [[ -f "$cand" ]] && { found="$cand"; break; }
done

if [[ -n "$found" ]]; then
    info "grill-harness visible at: $found"
else
    warn "grill-harness NOT deployed to any harness-visible location."
    warn "Deploy it: ~/repos/agent-rules/scripts/deploy-local-skills.sh"
fi

info "done. Restart harness sessions to pick up the restored skills."
