---
name: deck-to-gslides
description: Convert a markdown deck (Red Hat quick-deck companion markdown or any markdown with slide headings) into a native, co-editable Google Slides presentation. Deterministic pipeline - markdown adapter, pandoc PPTX, Drive upload with native conversion, post-upload verification. With --into <deckId>, rebuilds an EXISTING deck in place, preserving its URL and ID. Use when user says /deck-to-gslides, "convert this deck to Google Slides", "Google Slides from markdown", "slides from the companion markdown", "put this deck in Google Slides", "overwrite the existing deck", "rebuild the deck keeping the same URL", or wants a shareable co-editing version of a quick-deck. Pairs with the red-hat-quick-deck HTML deck workflow (its companion .md is the primary input).
metadata:
  opencode/slash: "true"
---

# deck-to-gslides

Turn a markdown deck into a native Google Slides presentation that others can
co-edit in Workspace. The HTML deck remains the presentation artifact; this
produces the editable Workspace twin.

## Why this pipeline (do not substitute md2gslides)

md2gslides depends on Google's out-of-band OAuth code flow, which Google
disabled in 2023. Its auth cannot complete and there is no configuration fix.
Do not attempt it. This skill's path - pandoc PPTX, then a Drive upload with
`mimeType: application/vnd.google-apps.presentation` - uses only Drive scope
and needs no new OAuth consent when the Drive CLI is already authorized.

Also know: a Drive upload always **creates a new presentation**. It cannot
inject slides into an existing deck, and it can never replace a Google-native
file in place. To rebuild an existing deck while **keeping its URL**, use
`--into <deckId>` (see below). To merge a few slides into an existing deck,
the user imports via the Slides UI (File > Import slides) from the created
deck - partial imports are out of scope for this skill.

## Prerequisites

- `pandoc` on PATH (brew install pandoc)
- `python3`
- A Drive-capable CLI - see Local config. Auth is the CLI's concern; this
  skill never handles credentials.

## Local config

| Placeholder | Env var | Meaning |
|---|---|---|
| `<drive-cli>` | `DECK_GSLIDES_DRIVE_CLI` | Single executable name or path speaking the Drive-API and Slides-API conventions: `<cli> drive files create --json <JSON> --upload <path> --upload-content-type <mime>`, `<cli> drive files get --params <JSON>`, `<cli> drive files update --params <JSON> --json <JSON>`, `<cli> slides presentations get --params <JSON>`, and `<cli> slides presentations batchUpdate --params <JSON> --json <JSON>`. The Slides calls are only required for `--into` (in-place rebuild). The value is one argv entry, not a command line - wrappers that need arguments (Bitwarden session loaders, OAuth helpers) must be packaged as a single wrapper script. Auth is the CLI's own concern; this skill never handles credentials. |

If the env var is unset (and not a dry run), **stop and ask the user** for the
CLI command rather than guessing. Non-JSON banner lines in the CLI's stdout
(e.g. session notices) are tolerated by the script.

## Workflow

1. **Identify the input.** Preferred: the deck's companion markdown (the
   `.md` file saved alongside a quick-deck HTML). Also accepts any markdown:
   `#`/`##` headings are slides, `---` separators split slides, HTML comments
   become speaker notes.
2. **Dry-run first** when the input is untested:

   ```bash
   python3 <skill-dir>/scripts/deck-to-gslides.py deck.md --dry-run
   ```

   Confirms mode detection, slide count, and speaker-note count. A companion
   deck of N slides must produce N slides; a mismatch means the markdown
   shape drifted - fix the markdown, not the count expectation.
3. **Upload:**

   ```bash
   export DECK_GSLIDES_DRIVE_CLI=<drive-cli>
   python3 <skill-dir>/scripts/deck-to-gslides.py deck.md --title "Deck Title"
   ```

   Options: `--folder <driveFolderId>` to place it in a specific folder;
   `--keep-pptx` to retain the intermediate PPTX.

4. **Verify (mandatory).** The script performs the post-upload verification
   itself: re-fetches the file, asserts the landed mimeType is
   `application/vnd.google-apps.presentation` (conversion happened), and
   prints the webViewLink. Report the URL to the user. Do not declare success
   from the create call alone.

## Rebuilding an existing deck in place (--into)

When the user wants to regenerate a deck they already shared, `--into <deckId>`
rebuilds the target presentation in place. The deck ID is the long token in
the deck URL (`https://docs.google.com/presentation/d/<deckId>/edit`) - pass
the bare ID, never the URL.

```bash
python3 <skill-dir>/scripts/deck-to-gslides.py deck.md --into <deckId>
```

Safety behavior:

- Before any mutation the script prints a plan: the target's title, its
  current slide count, and the incoming slide/note counts. The explicit
  `--into` flag IS the consent; there is no interactive prompt.
- `--dry-run --into <deckId>` fetches and prints the plan only - nothing is
  written. Dry-run this first when the target or input is untested.
- All target mutations are Slides API `batchUpdate` calls. The rebuild runs
  in three phases: append the new slides (non-destructive), populate their
  text/bullets/tables/notes (non-destructive), then ONE atomic batchUpdate
  that deletes the old slides. If anything fails before that final swap, the
  original slides are intact. The swap itself is atomic: it either fully
  lands or fully rolls back, so the deck can never be left empty.
- A write-scope probe on the throwaway staging deck precedes any target
  mutation; a 403 (missing Slides scope) exits non-zero with re-auth
  guidance and mutates nothing.
- The staging deck used for the rebuild is trashed afterward (best-effort;
  on failure a warning is printed and it remains in Drive). The rebuilt
  deck keeps its presentationId, URL, and Drive location.

Fidelity is the same structured text as a fresh conversion: titles, bullets,
native tables, speaker notes. Theme and layout mapping is by layout name
between the staging and target decks; unknown layout names fall back to
Blank. When the target was itself produced by this pipeline the names
match exactly. On a FOREIGN target deck (any deck not produced by this
pipeline) every slide may map to Blank, and Blank slides often have no
text placeholders - the script warns loudly when placeholder text cannot
be rebuilt; tables and speaker notes still carry over.

## Expectations to set with the user

- The Slides theme is Google's default - pandoc carries content, not brand
  CSS. The user applies a theme in the Slides UI if wanted.
- Layout arrives as structured text: titles, bullets, native tables. Visual
  arrangements from the HTML deck (diagrams, stat grids) do not carry over.
- Speaker notes carry over when the markdown has contextual notes (companion
  format) or HTML comments (generic).

## Failure handling

- `pandoc` missing -> install it, rerun.
- `DECK_GSLIDES_DRIVE_CLI` unset -> ask the user; never guess a CLI.
- Drive 404 on a user-supplied target deck -> the deck is not visible to the
  authorized account. Ask the user to share it (editor) or confirm the ID.
  A Drive upload cannot write into an existing deck regardless; `--into`
  needs the same visibility (editor access to the target).
- `--into` 403 on read (before the plan prints) -> the target may not be
  shared (editor) with the authorized account, or the credential lacks read
  scope. Nothing was mutated.
- `--into` 403 on write -> the CLI's credentials lack the Slides write
  scope (or a permission/quota problem arose mid-run). The script prints
  the exact deck state (nothing mutated, or original slides intact plus
  appended slides) and exits non-zero. Do not retry blindly.
- Verification mimeType mismatch -> stop and report; do not retry blindly.
