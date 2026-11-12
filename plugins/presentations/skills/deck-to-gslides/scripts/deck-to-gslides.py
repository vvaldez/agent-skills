#!/usr/bin/env python3
"""deck-to-gslides - convert a markdown deck companion into a native Google Slides presentation.

Pipeline: markdown -> (adapter) -> pandoc PPTX -> Drive upload with conversion
(mimeType application/vnd.google-apps.presentation) -> post-upload verification.

Modes:
  companion  - input follows the quick-deck companion format (## Slide N - headings,
               > Contextual notes: blocks, --- separators). Notes become speaker notes.
  generic    - any markdown; HTML comments become speaker notes, # headings are slides.

Drive CLI contract (parameterized, see SKILL.md Local config):
  DECK_GSLIDES_DRIVE_CLI  command (single executable name or path) that speaks
  the Drive-API convention:
      <cli> drive files create --json <JSON> --upload <path> --upload-content-type <mime>
      <cli> drive files get    --params <JSON>
  Auth (Bitwarden wrappers, OAuth, etc.) is the CLI's own concern; wrappers
  with arguments must be packaged as a single wrapper script.

Non-JSON prefix lines in CLI output (e.g. session banners) are tolerated.
"""

import argparse
import atexit
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

PPTX_MIME = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
SLIDES_MIME = "application/vnd.google-apps.presentation"


def eprint(*args):
    print(*args, file=sys.stderr)


SENSITIVE_RE = re.compile(r"(?i)(token|key|secret|session|password)\S*=\S+")


def scrub(text, limit=200):
    """Redact credential-shaped assignments and truncate CLI output for error messages."""
    text = SENSITIVE_RE.sub(r"\1=<redacted>", text)
    return text[:limit] + ("..." if len(text) > limit else "")


def run(cmd):
    """Run a command, return (returncode, stdout, stderr). Never uses a shell."""
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        return proc.returncode, proc.stdout, proc.stderr
    except FileNotFoundError:
        return 127, "", "command not found: %s" % cmd[0]
    except subprocess.TimeoutExpired:
        return 124, "", "timed out after 600s: %s" % cmd[0]


def parse_api_json(text):
    """Extract the first JSON object from CLI output, tolerating banner lines."""
    idx = text.find("{")
    if idx < 0:
        raise ValueError("no JSON object found in CLI output:\n%s" % scrub(text))
    obj, _ = json.JSONDecoder().raw_decode(text[idx:])
    return obj


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


def main():
    ap = argparse.ArgumentParser(description="Markdown deck companion -> native Google Slides")
    ap.add_argument("input", help="markdown file (quick-deck companion format or generic markdown)")
    ap.add_argument("--title", help="presentation title (default: first # heading)")
    ap.add_argument("--folder", help="Drive folder ID to create the presentation in (default: root)")
    ap.add_argument("--out", help="write the PPTX to this path (kept after upload; the scratch dir is still cleaned up)")
    ap.add_argument("--dry-run", action="store_true", help="build and verify the PPTX only; no upload (intermediates retained for inspection)")
    ap.add_argument("--keep-pptx", action="store_true", help="keep the scratch dir with the intermediate PPTX after upload")
    args = ap.parse_args()

    if not os.path.isfile(args.input):
        eprint("error: input not found: %s" % args.input)
        return 2

    pandoc = shutil.which("pandoc")
    if not pandoc:
        eprint("error: pandoc not found on PATH (brew install pandoc)")
        return 2

    drive_cli = os.environ.get("DECK_GSLIDES_DRIVE_CLI", "")
    if not drive_cli and not args.dry_run:
        eprint(
            "error: DECK_GSLIDES_DRIVE_CLI is not set.\n"
            "This skill needs a Drive-capable CLI (Local config placeholder <drive-cli>).\n"
            "Set it, e.g.: export DECK_GSLIDES_DRIVE_CLI=<your-drive-cli>"
        )
        return 2
    if drive_cli and not args.dry_run and not shutil.which(drive_cli):
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

    if args.dry_run:
        print("dry-run: upload skipped (DECK_GSLIDES_DRIVE_CLI=%s)" % ("set" if drive_cli else "<unset>"))
        return 0

    # 3. Upload with Drive conversion
    body = {"name": title, "mimeType": SLIDES_MIME}
    if args.folder:
        body["parents"] = [args.folder]
    cmd = [drive_cli, "drive", "files", "create",
           "--json", json.dumps(body),
           "--upload", pptx_path,
           "--upload-content-type", PPTX_MIME]
    rc, out, err = run(cmd)
    if rc != 0:
        eprint("error: Drive create failed (rc=%d):\n%s%s" % (rc, out, err))
        return 1
    try:
        created = parse_api_json(out)
    except ValueError as exc:
        eprint("error: could not parse Drive create response: %s" % exc)
        return 1
    file_id = created.get("id")
    if not file_id:
        eprint("error: Drive create returned no file id:\n%s" % out[:400])
        return 1

    # 4. Post-upload verification: re-fetch and confirm what actually landed
    rc, out, err = run([drive_cli, "drive", "files", "get", "--params", json.dumps(
        {"fileId": file_id,
         "fields": "name,mimeType,webViewLink,size,createdTime",
         "supportsAllDrives": True})])
    if rc != 0:
        eprint("error: verification GET failed (rc=%d):\n%s%s" % (rc, out, err))
        return 1
    try:
        landed = parse_api_json(out)
    except ValueError as exc:
        eprint("error: could not parse verification response: %s" % exc)
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
