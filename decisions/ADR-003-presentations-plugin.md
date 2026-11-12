# ADR-003: presentations plugin and the Drive-conversion path for Google Slides

**Status:** Accepted
**Date:** 2026-11-12

## Context

A markdown-to-Google-Slides pipeline was needed so quick-deck companion
markdown (the `.md` saved alongside HTML decks) can produce a co-editable
Workspace deck. Three candidate paths were evaluated live:

1. **md2gslides** (googleworkspace) - rejected. Its OAuth flow depends on
   Google's out-of-band (OOB) code exchange, which Google disabled in 2023.
   The failure is structural (client redirect mismatch plus a dead flow), not
   a configuration problem, and patching means forking its auth code.
2. **Direct Slides API builder** - rejected for v1. Requires the Slides API
   scope (a new OAuth consent) and a per-slide layout engine; overkill until
   there is a repeat need for native layout control.
3. **pandoc PPTX + Drive upload with conversion** - selected. Uploading a
   `.pptx` with `mimeType: application/vnd.google-apps.presentation` makes
   Drive convert it to a native Slides deck on arrival. This uses only Drive
   scope, so an already-authorized Drive CLI needs no new consent. PPTX text
   is real and editable in Slides (unlike Marp's image-based PPTX).

A Drive upload always creates a new presentation; it cannot inject slides
into an existing deck. Merging into an existing deck is a Slides-UI import
(File > Import slides), documented in the skill.

## Decision

- New **`presentations` plugin** (one concern per plugin, matching `diagrams`
  and `local-model` precedent) with a single skill, **`deck-to-gslides`**.
- Not named `red-hat-quick-deck-gslides` or placed under a "red-hat" prefix:
  the output carries Google's default theme, not Red Hat brand styling, and
  the pipeline's contract is the companion markdown shape, not any specific
  deck skill. The skill description declares the pairing with quick-deck
  companions instead of implying ownership.
- The adapter (companion markdown -> pandoc input, contextual notes ->
  speaker notes) and the upload + verification steps are a **deterministic
  script** (`scripts/deck-to-gslides.py`), not prose instructions.
- Per ADR-002, the Drive CLI is a **parameterized placeholder**
  (`DECK_GSLIDES_DRIVE_CLI`, `<drive-cli>` in the skill's Local config
  section). The script stops and asks when it is unset. Auth wrappers
  (Bitwarden session loaders, OAuth helpers) are the local value's concern
  and never appear in the public repo. Non-JSON banner lines in the CLI's
  stdout are tolerated.
- **Post-upload verification is built in**: the script re-fetches the created
  file and asserts the landed mimeType is
  `application/vnd.google-apps.presentation` before reporting success.

## Consequences

- Slide fidelity is structured text (titles, bullets, native tables); HTML
  deck visuals do not carry over. This is stated in the skill so expectations
  are set before upload.
- If native layout control is later needed, a Slides API builder can join
  this plugin as a sibling skill without revisiting the plugin decision.
- **Delivered amendment (2026-11-12, issue #44):** URL-preserving
  regeneration is now possible via the hybrid path — the Drive-conversion
  pipeline still cannot replace a Google-native file in place, so
  `--into <deckId>` uploads a throwaway staging deck through the unchanged
  Drive path, reads its structure through the Slides API, and rebuilds the
  target natively (append new slides -> populate -> one atomic batchUpdate
  deleting the old slides). This was the deferred Slides-API scope from the
  context above; it arrived only when the URL-breakage need materialized,
  and the Drive-only path remains the default for fresh decks.
