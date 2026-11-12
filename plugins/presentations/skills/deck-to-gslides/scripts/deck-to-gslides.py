#!/usr/bin/env python3
"""deck-to-gslides - convert a markdown deck companion into a native Google Slides presentation.

Pipeline: markdown -> (adapter) -> pandoc PPTX -> Drive upload with conversion
(mimeType application/vnd.google-apps.presentation) -> post-upload verification.

Modes:
  companion  - input follows the quick-deck companion format (## Slide N - headings,
               > Contextual notes: blocks, --- separators). Notes become speaker notes.
  generic    - any markdown; HTML comments become speaker notes, # headings are slides.

With --into <deckId> the target deck is rebuilt IN PLACE (URL and presentationId
preserved): a staging deck is uploaded via the normal Drive-conversion path, its
slide structure is read back through the Slides API, and the target is rebuilt by
appending new slides and then atomically deleting the old ones in one batchUpdate.
The destructive swap is a single atomic batchUpdate, so a mid-run failure can
never leave the target deck empty or half-replaced.

Drive CLI contract (parameterized, see SKILL.md Local config):
  DECK_GSLIDES_DRIVE_CLI  command (single executable name or path) that speaks
  the Drive-API and Slides-API conventions:
      <cli> drive files create --json <JSON> --upload <path> --upload-content-type <mime>
      <cli> drive files get    --params <JSON>
      <cli> drive files update --params <JSON> --json <JSON>
      <cli> slides presentations get         --params <JSON>
      <cli> slides presentations batchUpdate --params <JSON> --json <JSON>
  Auth (Bitwarden wrappers, OAuth, etc.) is the CLI's own concern; wrappers
  with arguments must be packaged as a single wrapper script.

Non-JSON prefix lines in CLI output (e.g. session banners) are tolerated.
"""

import argparse
import atexit
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
import zipfile

PPTX_MIME = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
SLIDES_MIME = "application/vnd.google-apps.presentation"


def eprint(*args):
    print(*args, file=sys.stderr)


SENSITIVE_RE = re.compile(
    r"(?i)(token|key|secret|session|password|bearer)\s*[=:]\s*\S+")


def scrub(text, limit=200):
    """Redact credential-shaped assignments and truncate CLI output for error messages."""
    text = SENSITIVE_RE.sub(r"\1=<redacted>", text)
    return text[:limit] + ("..." if len(text) > limit else "")


def run(cmd):
    """Run a command, return (returncode, stdout, stderr). Never uses a shell.

    Error strings never include cmd[0] (the configured CLI value) - the
    caller's `what` label already identifies the failing call.
    """
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        return proc.returncode, proc.stdout, proc.stderr
    except FileNotFoundError:
        return 127, "", "command not found"
    except subprocess.TimeoutExpired:
        return 124, "", "timed out after 600s"
    except OSError as exc:
        return 126, "", "could not execute: %s" % exc


def parse_api_json(text):
    """Extract the first JSON object from CLI output, tolerating banner lines."""
    idx = text.find("{")
    if idx < 0:
        raise ValueError("no JSON object found in CLI output:\n%s" % scrub(text))
    obj, _ = json.JSONDecoder().raw_decode(text[idx:])
    return obj


class ApiError(Exception):
    """A CLI invocation failed, or the API returned an error object."""

    def __init__(self, code, message, raw=""):
        super().__init__(message)
        self.code = code
        self.message = message
        self.raw = raw


def call_json(cmd, what):
    """Run a CLI call, parse its JSON, and raise ApiError on any error object."""
    rc, out, err = run(cmd)
    try:
        payload = parse_api_json(out)
    except ValueError as exc:
        raise ApiError(None, "%s failed (rc=%d): %s | stderr: %s"
                       % (what, rc, exc, scrub(err or out)), out) from exc
    if isinstance(payload, dict) and "error" in payload:
        err_obj = payload["error"] or {}
        raise ApiError(err_obj.get("code"), err_obj.get("message", "unknown error"), out)
    if rc != 0:
        raise ApiError(None, "%s failed (rc=%d): %s" % (what, rc, scrub(err or out)), out)
    return payload


def utf16_len(text):
    """Slides API text indices are UTF-16 code units, not codepoints."""
    return len(text.encode("utf-16-le")) // 2


def scope_fail_exit(action, appended=0):
    if appended:
        eprint(
            "error: the configured CLI's credentials lost Google Slides write "
            "permission (HTTP 403) during %s.\n"
            "The original slides are intact; the target deck additionally has "
            "%d appended slide(s) from the partial rebuild.\n"
            "Remediation: resolve the permission/quota problem, then rerun; "
            "the rerun replaces the deck cleanly." % (action, appended)
        )
        return 1
    eprint(
        "error: the configured CLI's credentials lack Google Slides write "
        "permission (HTTP 403) while attempting %s.\n"
        "Nothing was mutated.\n"
        "Remediation: run a one-time re-auth for the CLI that includes the "
        "slides service, then rerun." % action
    )
    return 1


def trash_file(drive_cli, file_id):
    """Best-effort: move a Drive file to the trash."""
    try:
        call_json([drive_cli, "drive", "files", "update",
                   "--params", json.dumps({"fileId": file_id}),
                   "--json", json.dumps({"trashed": True})],
                  "trash staging deck")
    except ApiError as exc:
        eprint("warning: could not trash staging deck %s: %s" % (file_id, exc.message))


# ---------------------------------------------------------------------------
# Markdown adapter
# ---------------------------------------------------------------------------

def companion_to_pandoc(src):
    """Convert quick-deck companion markdown to pandoc pptx input.

    Returns (converted_markdown, mode). Companion mode: '## Slide N: Title'
    (or em-dash) headings become '# Title'; '> Contextual notes:' quote blocks
    become pandoc speaker-notes; the first block supplies the title slide.
    Generic mode: HTML comments become speaker-notes, everything else passes through.
    """
    blocks = re.split(r"\n---\n", src)
    is_companion = len(blocks) >= 2 and re.search(r"^## Slide \d+", blocks[1], re.M)
    if not is_companion:
        converted = re.sub(
            r"<!--\s*(.*?)\s*-->",
            lambda m: "::: notes\n%s\n:::" % m.group(1).strip(),
            src,
            flags=re.S,
        )
        return converted, "generic"

    out = []

    # First block: deck header -> title slide
    title = None
    body = []
    for line in blocks[0].strip().splitlines():
        s = line.strip()
        if s.startswith("# ") and title is None:
            title = s[2:]
        elif s.startswith("_") and s.endswith("_") and len(s) > 2:
            body.append(s.strip("_"))
        elif s.startswith("**") and s.endswith("**"):
            continue
        elif s:
            body.append(s)
    out.append("# %s\n\n%s" % (title or "Untitled deck", "\n\n".join(body)))

    # Slide blocks
    for block in blocks[1:]:
        content = []
        notes = []
        in_notes = False
        for line in block.strip().splitlines():
            s = line.rstrip()
            m = re.match(r"^## Slide \d+\s*[:\u2014-]\s*(.+)$", s)
            if m:
                in_notes = False
                content.append("# " + m.group(1).strip())
            elif s.startswith("> Contextual notes:"):
                in_notes = True
                notes.append(s.replace("> Contextual notes:", "", 1).strip())
            elif in_notes and s.startswith(">"):
                notes.append(s.lstrip("> ").strip())
            elif in_notes and not s.strip():
                continue
            else:
                in_notes = False
                content.append(s)
        while content and not content[0].strip():
            content.pop(0)
        while content and not content[-1].strip():
            content.pop()
        note_text = " ".join(n for n in notes if n)

        # Companion decks repeat the deck title as Slide 1 - fold it into the
        # title slide instead of emitting a duplicate.
        first_slide = len(out) == 1 and content and content[0] == "# " + title
        if first_slide:
            if note_text:
                out[0] = out[0] + "\n\n::: notes\n" + note_text + "\n:::"
            continue

        slide = "\n".join(content)
        if note_text:
            slide += "\n\n::: notes\n%s\n:::" % note_text
        out.append(slide)

    return "\n\n---\n\n".join(out) + "\n", "companion"


def detect_title(converted):
    m = re.search(r"^# (.+)$", converted, re.M)
    return m.group(1).strip() if m else "Untitled deck"


def count_slides(pptx_path):
    with zipfile.ZipFile(pptx_path) as z:
        return sum(1 for n in z.namelist() if re.match(r"ppt/slides/slide\d+\.xml$", n))


def count_notes(pptx_path):
    with zipfile.ZipFile(pptx_path) as z:
        return sum(1 for n in z.namelist() if "notesSlide" in n and n.endswith(".xml"))


# ---------------------------------------------------------------------------
# Slides structure extraction (shared by rebuild and verification)
# ---------------------------------------------------------------------------

def shape_paragraphs(shape):
    """Return (paragraphs, bullet_flags, nesting_levels) for a shape's text.

    Internal line breaks are flattened to spaces so each paragraph is one line;
    paragraphs map 1:1 to what insertText creates via newline characters.
    """
    txt = shape.get("text") or {}
    paras, flags, nestings = [], [], []
    cur = []
    for el in txt.get("textElements", []):
        if "textRun" in el:
            cur.append(el["textRun"].get("content", ""))
        elif "paragraphMarker" in el:
            pm = el["paragraphMarker"]
            bullet = pm.get("bullet") or {}
            # the paragraph-terminating \n rides on the last run of the
            # paragraph; normalize it (and any stray newline) to nothing
            paras.append("".join(cur).replace("\n", " ").strip())
            flags.append(bool(bullet))
            nestings.append(int(bullet.get("nestingLevel", 0) or 0))
            cur = []
    paras.append("".join(cur).replace("\n", " ").strip())
    flags.append(False)
    nestings.append(0)
    while paras and not paras[-1].strip():
        paras.pop()
        flags.pop()
        nestings.pop()
    return paras, flags, nestings


def read_notes_text(slide):
    """Read a slide's speaker-notes text via its notesPage (may be empty)."""
    notes_page = (slide.get("slideProperties") or {}).get("notesPage") or {}
    speaker_id = ((notes_page.get("notesProperties") or {}).get("speakerNotesObjectId"))
    if not speaker_id:
        return ""
    for el in notes_page.get("pageElements", []):
        if el.get("objectId") == speaker_id and "shape" in el:
            paras, _, _ = shape_paragraphs(el["shape"])
            return "\n".join(p for p in paras if p.strip())
    return ""


def table_grid(table):
    """Return (rows, cols, cell_texts) where cell_texts is a 2D list of strings."""
    rows = []
    for row in table.get("tableRows", []):
        cells = []
        for cell in row.get("tableCells", []) or []:
            paras, _, _ = shape_paragraphs({"text": cell.get("text") or {}})
            cells.append("\n".join(p for p in paras if p.strip()))
        rows.append(cells)
    n_cols = table.get("columns", 0)
    for row in rows:  # pad short rows (cell spans)
        while len(row) < n_cols:
            row.append("")
    return table.get("rows", len(rows)), n_cols, rows


def slide_blueprint(slide):
    """Extract the rebuildable content of a slide: placeholders + tables.

    Placeholders: ordered list of (placeholder_type, paragraphs, flags, nestings).
    Tables: ordered list of (rows, cols, cell_texts, transform_or_None).
    Non-placeholder shapes and images are intentionally skipped (structured
    text fidelity - see SKILL.md).
    """
    placeholders, tables = [], []
    for el in slide.get("pageElements", []):
        if "shape" in el:
            ph = (el["shape"].get("placeholder") or {}).get("type")
            if ph:
                paras, flags, nestings = shape_paragraphs(el["shape"])
                placeholders.append((ph, paras, flags, nestings))
        elif "table" in el:
            rows, cols, cells = table_grid(el["table"])
            tables.append((rows, cols, cells, el.get("transform")))
    return placeholders, tables


def layout_names(pres):
    """Return (id_to_name, name_to_id) maps for a presentation's layouts."""
    id_to_name, name_to_id = {}, {}
    for lo in pres.get("layouts", []):
        lo_id = lo.get("objectId")
        name = (lo.get("layoutProperties") or {}).get("displayName") or ""
        if lo_id:
            id_to_name[lo_id] = name
            name_to_id.setdefault(name, lo_id)
    return id_to_name, name_to_id


def slides_get(drive_cli, pres_id, fields):
    return call_json([drive_cli, "slides", "presentations", "get",
                      "--params", json.dumps({"presentationId": pres_id, "fields": fields})],
                     "slides get %s" % pres_id)


def slides_batch(drive_cli, pres_id, requests, what):
    return call_json([drive_cli, "slides", "presentations", "batchUpdate",
                      "--params", json.dumps({"presentationId": pres_id}),
                      "--json", json.dumps({"requests": requests})],
                     what)


def upload_pptx_as_slides(drive_cli, pptx_path, name, folder=None):
    """Upload a PPTX for Drive conversion to native Slides; return the new file id."""
    body = {"name": name, "mimeType": SLIDES_MIME}
    if folder:
        body["parents"] = [folder]
    created = call_json([drive_cli, "drive", "files", "create",
                         "--json", json.dumps(body),
                         "--upload", pptx_path,
                         "--upload-content-type", PPTX_MIME],
                        "Drive create")
    file_id = created.get("id")
    if not file_id:
        raise ApiError(None, "Drive create returned no file id", json.dumps(created))
    return file_id


# ---------------------------------------------------------------------------
# In-place rebuild (--into)
# ---------------------------------------------------------------------------

def plan_rebuild(drive_cli, into_id, incoming_slides, incoming_notes):
    """Read the target deck and print the rebuild plan. Returns the target GET."""
    tgt = slides_get(drive_cli, into_id,
                     "presentationId,title,layouts(objectId,layoutProperties.displayName),"
                     "slides(objectId)")
    if tgt.get("presentationId") != into_id:
        raise ApiError(None, "slides get returned presentationId %r, expected %r"
                       % (tgt.get("presentationId"), into_id))
    print("plan: target title=%r current_slides=%d incoming_slides=%d incoming_notes=%d"
          % (tgt.get("title"), len(tgt.get("slides", [])), incoming_slides, incoming_notes))
    print("plan: the deck URL will not change")
    return tgt


def rebuild_into(drive_cli, pptx_path, into_id, title, tgt):
    """Rebuild the target deck in place. Returns (slide_count, notes_count)."""
    staging_name = "%s (deck-to-gslides staging)" % title
    staging_id = upload_pptx_as_slides(drive_cli, pptx_path, staging_name)
    try:
        # Read the staging deck's structure (the source of truth for the rebuild).
        src = slides_get(drive_cli, staging_id,
                         "presentationId,layouts(objectId,layoutProperties.displayName),"
                         "slides(objectId,slideProperties.layoutObjectId,"
                         "slideProperties.notesPage,pageElements)")
        src_slides = src.get("slides", [])
        if not src_slides:
            raise ApiError(None, "staging deck has no slides", "")
        src_names, _ = layout_names(src)
        _, tgt_by_name = layout_names(tgt)
        blank_layout = tgt_by_name.get("Blank") or ""
        old_ids = [s["objectId"] for s in tgt.get("slides", [])]

        blueprints = [slide_blueprint(s) for s in src_slides]

        # Write-scope probe on the STAGING deck: one atomic batchUpdate that
        # creates and deletes a probe slide (net zero). Fails closed before any
        # target mutation if the credential lacks the Slides write scope.
        probe_layout = src_slides[0].get("slideProperties", {}).get("layoutObjectId")
        probe_req = [{"createSlide": {"objectId": "d2gProbe01"}},
                     {"deleteObject": {"objectId": "d2gProbe01"}}]
        if probe_layout:
            probe_req[0]["createSlide"]["slideLayoutReference"] = {"layoutId": probe_layout}
        try:
            slides_batch(drive_cli, staging_id, probe_req, "write-scope probe")
        except ApiError:
            # fail closed: any probe failure (403 or otherwise) aborts before
            # the target is touched
            raise

        # Phase A (non-destructive): append new slides (+ their tables) to the
        # target. Old slides are untouched; failure leaves the target unchanged
        # except for appended slides.
        # Object IDs are unique per RUN (random prefix): a re-run against a
        # deck this tool previously rebuilt would otherwise collide with the
        # IDs it minted last time (verified live - idempotency probe).
        run_prefix = "d2g" + secrets.token_hex(4)
        new_ids = []
        phase_a = []
        for i, (placeholders, tables) in enumerate(blueprints):
            sid = "%ss%02d" % (run_prefix, i + 1)
            new_ids.append(sid)
            create = {"objectId": sid}
            layout_name = src_names.get(
                src_slides[i].get("slideProperties", {}).get("layoutObjectId"), "")
            layout_id = tgt_by_name.get(layout_name) or blank_layout
            if layout_id:
                create["slideLayoutReference"] = {"layoutId": layout_id}
            phase_a.append({"createSlide": create})
            for j, (rows, cols, _cells, transform) in enumerate(tables):
                tid = "%st%02d%d" % (run_prefix, i + 1, j)
                ep = {"pageObjectId": sid}
                if transform:
                    ep["transform"] = transform
                phase_a.append({"createTable": {"objectId": tid, "elementProperties": ep,
                                                "rows": rows, "columns": cols}})
        try:
            slides_batch(drive_cli, into_id, phase_a, "rebuild phase A (append slides)")
        except ApiError as exc:
            if exc.code == 403:
                raise
            eprint("error: phase A failed; the target deck was NOT modified beyond "
                   "any slides already appended atomically. %s" % exc.message)
            raise

        # Discover the new slides' placeholder shape IDs and notes shape IDs.
        fresh = slides_get(drive_cli, into_id,
                           "slides(objectId,pageElements.objectId,"
                           "pageElements.shape.placeholder,"
                           "slideProperties.notesPage.notesProperties)")
        fresh_by_id = {s["objectId"]: s for s in fresh.get("slides", [])}

        # Phase B (non-destructive): populate the new slides' text, bullets,
        # table cells, and speaker notes.
        phase_b = []
        dropped_text = []  # placeholder text with no matching fresh placeholder
        for i, (placeholders, tables) in enumerate(blueprints):
            sid = new_ids[i]
            new = fresh_by_id.get(sid) or {}
            ph_ids = {}
            for el in new.get("pageElements", []):
                ph = ((el.get("shape") or {}).get("placeholder") or {}).get("type")
                if ph:
                    ph_ids.setdefault(ph, []).append(el.get("objectId"))
            # match source placeholders to target placeholders by type + occurrence
            src_by_type = {}
            for ptype, paras, flags, nestings in placeholders:
                src_by_type.setdefault(ptype, []).append((paras, flags, nestings))
            for ptype, src_list in src_by_type.items():
                for (paras, flags, nestings), dst_id in zip(src_list, ph_ids.get(ptype, [])):
                    if not dst_id:
                        if any(p.strip() for p in paras):
                            dropped_text.append((i + 1, ptype,
                                                 (paras[0] or "")[:50]))
                        continue
                    text = "\n".join(paras)
                    if not text.strip():
                        continue
                    # fresh layout placeholders are empty: insert only, no deleteText
                    # (deleteText ALL on an empty shape is rejected by the API)
                    phase_b.append({"insertText": {"objectId": dst_id, "text": text,
                                                   "insertionIndex": 0}})
                    # per-paragraph bullets, indices in UTF-16 code units
                    for k, flagged in enumerate(flags):
                        if not flagged or not paras[k].strip():
                            continue
                        start = utf16_len("\n".join(paras[:k])) + k
                        phase_b.append({
                            "createParagraphBullets": {
                                "objectId": dst_id,
                                "textRange": {"type": "FIXED_RANGE",
                                              "startIndex": start,
                                              "endIndex": start + utf16_len(paras[k])},
                                "bulletPreset": "BULLET_DISC_CIRCLE_SQUARE"}})
            # table cell text (cells are empty on a fresh table)
            for j, (_rows, _cols, cells, _transform) in enumerate(tables):
                tid = "%st%02d%d" % (run_prefix, i + 1, j)
                for r, row in enumerate(cells):
                    for c, val in enumerate(row):
                        if val.strip():
                            phase_b.append({"insertText": {
                                "objectId": tid,
                                "cellLocation": {"rowIndex": r, "columnIndex": c},
                                "text": val, "insertionIndex": 0}})
            # speaker notes: the notes shape may not exist yet; insertText using
            # the speakerNotesObjectId auto-creates it (documented API behavior)
            note_text = read_notes_text(src_slides[i])
            speaker_id = (((new.get("slideProperties") or {}).get("notesPage")
                           or {}).get("notesProperties") or {}).get("speakerNotesObjectId")
            if note_text.strip() and speaker_id:
                phase_b.append({"insertText": {"objectId": speaker_id,
                                               "text": note_text, "insertionIndex": 0}})
        try:
            slides_batch(drive_cli, into_id, phase_b, "rebuild phase B (populate content)")
        except ApiError as exc:
            eprint("error: phase B failed; new slides are appended but unpopulated and "
                   "the original slides are still intact. %s" % exc.message)
            if exc.code == 403:
                exc.appended = len(new_ids)
            raise
        if dropped_text:
            eprint("warning: %d placeholder(s) had text in the staging deck but no "
                   "matching placeholder on the rebuilt slides (layout-name mapping "
                   "fell back to Blank); their text was NOT rebuilt. Affected: %s"
                   % (len(dropped_text),
                      "; ".join("slide %d %s %r" % d for d in dropped_text[:5])))

        # Phase C (the ONLY destructive step, one atomic batchUpdate): delete the
        # old slides. The new slides were appended after them, so deletion both
        # removes the old content and moves the new slides to the front. If this
        # fails, the batch rolls back and the target keeps its old slides.
        try:
            slides_batch(drive_cli, into_id,
                         [{"deleteObject": {"objectId": old_id}} for old_id in old_ids],
                         "rebuild phase C (atomic swap)")
        except ApiError as exc:
            eprint("error: phase C failed; the target deck still has its original "
                   "slides plus %d appended slides at the end. %s"
                   % (len(new_ids), exc.message))
            if exc.code == 403:
                exc.appended = len(new_ids)
            raise

        # Verification: re-fetch and assert what actually landed. At this point
        # the destructive swap has ALREADY landed - be explicit about that if
        # verification fails, so the user never misreads the deck's state.
        try:
            landed = slides_get(drive_cli, into_id,
                                "presentationId,slides(objectId,slideProperties.notesPage)")
            if landed.get("presentationId") != into_id:
                raise ApiError(None, "verification: presentationId changed (%r != %r)"
                               % (landed.get("presentationId"), into_id), "")
            landed_slides = landed.get("slides", [])
            expected = len(new_ids)
            if len(landed_slides) != expected:
                raise ApiError(None, "verification: landed %d slides, expected %d"
                               % (len(landed_slides), expected), "")
            expected_notes = sum(1 for s in src_slides if read_notes_text(s).strip())
            landed_notes = sum(1 for s in landed_slides if read_notes_text(s).strip())
            if landed_notes != expected_notes:
                raise ApiError(None, "verification: landed %d slides with speaker notes, "
                               "expected %d" % (landed_notes, expected_notes), "")
        except ApiError:
            eprint("error: the rebuild swap already completed - the deck now contains "
                   "the rebuilt content; only the post-rebuild verification failed.")
            raise
        return len(landed_slides), landed_notes
    finally:
        trash_file(drive_cli, staging_id)


# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="Markdown deck companion -> native Google Slides")
    ap.add_argument("input", help="markdown file (quick-deck companion format or generic markdown)")
    ap.add_argument("--title", help="presentation title (default: first # heading)")
    ap.add_argument("--folder", help="Drive folder ID to create the presentation in (default: root)")
    ap.add_argument("--out", help="write the PPTX to this path (kept after upload; the scratch dir is still cleaned up)")
    ap.add_argument("--dry-run", action="store_true", help="build and verify the PPTX only; no upload (intermediates retained for inspection; with --into, fetch and print the plan only)")
    ap.add_argument("--keep-pptx", action="store_true", help="keep the scratch dir with the intermediate PPTX after upload")
    ap.add_argument("--into", help="rebuild this existing presentation IN PLACE (deck ID; URL preserved). Mutates the target: all its slides are replaced.")
    args = ap.parse_args()

    if not os.path.isfile(args.input):
        eprint("error: input not found: %s" % args.input)
        return 2
    if args.into and args.folder:
        eprint("error: --folder cannot be combined with --into (the target deck keeps its location)")
        return 2
    if args.into and not re.fullmatch(r"[A-Za-z0-9_-]+", args.into):
        eprint("error: --into expects a bare deck ID (the long token in the deck URL), not a URL")
        return 2

    pandoc = shutil.which("pandoc")
    if not pandoc:
        eprint("error: pandoc not found on PATH (brew install pandoc)")
        return 2

    drive_cli = os.environ.get("DECK_GSLIDES_DRIVE_CLI", "")
    needs_cli = not args.dry_run or bool(args.into)
    if not drive_cli and needs_cli:
        eprint(
            "error: DECK_GSLIDES_DRIVE_CLI is not set.\n"
            "This skill needs a Drive-capable CLI (Local config placeholder <drive-cli>).\n"
            "Set it, e.g.: export DECK_GSLIDES_DRIVE_CLI=<your-drive-cli>"
        )
        return 2
    if drive_cli and needs_cli and not shutil.which(drive_cli):
        eprint("error: DECK_GSLIDES_DRIVE_CLI is set but not found on PATH (value not shown)")
        return 2

    # 1. Adapt markdown (normalize CRLF so --- separators and headings match)
    with open(args.input, encoding="utf-8") as f:
        src = f.read().replace("\r\n", "\n")
    converted, mode = companion_to_pandoc(src)
    title = args.title or detect_title(converted)

    # 2. Build PPTX via pandoc.
    # Temp dir lives under the CWD: some Drive CLIs validate --upload paths
    # against the current directory and reject system-temp locations.
    try:
        tmpdir = tempfile.mkdtemp(prefix=".deck-to-gslides-", dir=os.getcwd())
    except OSError as exc:
        eprint("error: cannot create temp dir under %s (not writable?): %s" % (os.getcwd(), exc))
        return 2
    # --out keeps only the PPTX at its own path; --dry-run/--keep-pptx keep the
    # whole scratch dir. Everything else is removed at exit.
    keep_tmpdir = bool(args.dry_run or args.keep_pptx)
    if not keep_tmpdir:
        atexit.register(shutil.rmtree, tmpdir, True)
    md_path = os.path.join(tmpdir, "deck-pandoc.md")
    pptx_path = args.out or os.path.join(tmpdir, "deck.pptx")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(converted)

    rc, out, err = run([pandoc, md_path, "-f", "markdown+pipe_tables", "-t", "pptx",
                        "--slide-level=1", "-o", pptx_path])
    if rc != 0:
        eprint("error: pandoc failed (rc=%d):\n%s%s" % (rc, out, err))
        return 1
    if not os.path.isfile(pptx_path) or os.path.getsize(pptx_path) == 0:
        eprint("error: pandoc produced no PPTX")
        return 1

    slides = count_slides(pptx_path)
    notes = count_notes(pptx_path)
    if slides == 0:
        eprint("error: PPTX contains zero slides")
        return 1
    print("mode=%s title=%r slides=%d notes=%d pptx=%s" % (mode, title, slides, notes, pptx_path))

    # --into: plan (read-only), then either stop (dry-run) or rebuild in place.
    if args.into:
        try:
            tgt = plan_rebuild(drive_cli, args.into, slides, notes)
        except ApiError as exc:
            if exc.code == 403:
                eprint("error: could not read the target deck (HTTP 403). It may "
                       "not be shared (editor) with the authorized account, or "
                       "the credential lacks read scope. Nothing was mutated.")
                return 1
            raise
        if args.dry_run:
            print("dry-run: plan only, nothing was written to the target deck")
            return 0
        try:
            landed_slides, landed_notes = rebuild_into(drive_cli, pptx_path, args.into,
                                                       title, tgt)
        except ApiError as exc:
            if exc.code == 403:
                return scope_fail_exit("the in-place rebuild",
                                       appended=getattr(exc, "appended", 0))
            eprint("error: rebuild failed: %s" % exc.message)
            if exc.code is None and exc.raw:
                eprint(scrub(exc.raw))
            return 1
        print("rebuilt id=%s (unchanged) slides=%d notes=%d" % (args.into, landed_slides, landed_notes))
        print("url=https://docs.google.com/presentation/d/%s/edit" % args.into)
        if args.out:
            print("pptx kept at %s" % pptx_path)
        elif keep_tmpdir:
            print("intermediate files kept in %s" % tmpdir)
        else:
            print("intermediate files removed (use --keep-pptx to retain)")
        return 0

    if args.dry_run:
        print("dry-run: upload skipped (DECK_GSLIDES_DRIVE_CLI=%s)" % ("set" if drive_cli else "<unset>"))
        return 0

    # 3. Upload with Drive conversion
    try:
        file_id = upload_pptx_as_slides(drive_cli, pptx_path, title, args.folder)
    except ApiError as exc:
        eprint("error: Drive create failed: %s" % exc.message)
        if exc.raw:
            eprint(scrub(exc.raw))
        return 1

    # 4. Post-upload verification: re-fetch and confirm what actually landed
    try:
        landed = call_json([drive_cli, "drive", "files", "get", "--params", json.dumps(
            {"fileId": file_id,
             "fields": "name,mimeType,webViewLink,size,createdTime",
             "supportsAllDrives": True})], "verification GET")
    except ApiError as exc:
        eprint("error: verification GET failed: %s" % exc.message)
        return 1
    if landed.get("mimeType") != SLIDES_MIME:
        eprint("error: landed mimeType is %r, expected %r - conversion did not happen"
               % (landed.get("mimeType"), SLIDES_MIME))
        return 1

    print("created id=%s" % file_id)
    print("verified name=%r mimeType=%s" % (landed.get("name"), landed.get("mimeType")))
    print("url=%s" % landed.get("webViewLink", "https://docs.google.com/presentation/d/%s/edit" % file_id))

    if args.out:
        print("pptx kept at %s" % pptx_path)
    elif keep_tmpdir:
        print("intermediate files kept in %s" % tmpdir)
    else:
        print("intermediate files removed (use --keep-pptx to retain)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
