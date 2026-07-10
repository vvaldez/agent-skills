---
name: red-hat-quick-diagram
description: >
  Generate branded process flow diagrams as self-contained HTML files with auto-PNG export.
  Red Hat branded: Display/Text/Mono fonts, RHDS color palette, dark-mode aesthetic.
  Use when user says /diagram, /quick-diagram, "create a diagram", "draw a flowchart",
  "process flow", "workflow diagram", "visualize this process", or "diagram this workflow".
---

# Red Hat Quick Diagram

Generate process flow diagrams as self-contained HTML files with Red Hat branding.
Auto-renders to PNG via Puppeteer for embedding in Docs/Slides.

> Brand references derived from [red-hat-quick-deck](https://github.com/toddward/red-hat-quick-deck)
> by Todd Ward. Diagram layout and node system are original to this skill.

## Before You Begin

1. **Read `references/redhat-brand.md`** for the official color palette and typography.
2. **Read `references/rhds-icons.md`** for available RHDS icons.

## What You Produce

A single `.html` file that:
- Is completely self-contained (inline CSS, inline JS; Google Fonts via CDN)
- Opens in any browser, can be emailed or hosted
- Uses Red Hat brand colors, typography, and design tokens
- Renders process flows with positioned nodes, SVG arrows, and styled connections
- Includes a classification watermark (DRAFT/INTERNAL/CONFIDENTIAL/none)

After generating the HTML, auto-render to PNG using Puppeteer.

## Workflow

1. User describes diagram in natural language or pastes a step list
2. Ask the classification level (default: DRAFT)
3. Generate the HTML with all nodes, arrows, dividers, and watermark
4. Render PNG (headless Chrome preferred, Puppeteer fallback)
5. **Read the PNG back and visually verify** — arrows connect to edges, labels readable, no overlaps
6. Report both file paths to user

**HARD RULE:** Never declare "done" based on code changes alone. SVG coordinates and
CSS `transform:rotate()` produce visual results that differ from what the code suggests.
After every HTML edit: re-render PNG → read PNG → verify → report what you see.

**HARD RULE: Use a subagent for all editing and verification.**

Reading PNGs back into the main conversation repeatedly exhausts the context window in
3-5 iterations. Instead:

1. Spawn a **single long-lived subagent** (Agent tool) for the entire diagram task
2. The subagent does ALL work: edit HTML → render PNG → read PNG → verify → iterate
3. The subagent reports **text-only summaries** back to the main thread (never PNGs)
4. The main thread **never reads the PNG** — only relays file paths to the user
5. When the subagent reports all checks pass, the main thread reports the final paths

The subagent prompt should include: the full diagram description, classification level,
output file paths, and "read this skill's SKILL.md for all layout and arrow rules."

Complex diagrams (25+ nodes) take 3-5+ iterations. Set this expectation with the user.

## Layout Approach

**Use HTML/CSS absolute positioning with SVG overlay for arrows.**

Do NOT use Mermaid — it cannot handle side-by-side subgraphs, grid layouts, complex
crossing arrows, feedback loops, or horizontal divider lines.

### HTML Structure

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>DIAGRAM_TITLE</title>
<link href="https://fonts.googleapis.com/css2?family=Red+Hat+Display:wght@400;700&family=Red+Hat+Text:wght@400;500;700&family=Red+Hat+Mono:wght@400;500&display=swap" rel="stylesheet">
<!-- Inline all CSS -->
</head>
<body>
<div class="diagram" style="position:relative; width:1400px;">
  <h1>DIAGRAM_TITLE</h1>
  <p class="subtitle">WATERMARK_TEXT</p>

  <!-- SVG overlay for arrows -->
  <svg class="arrows" viewBox="0 0 1400 HEIGHT">
    <defs>
      <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="10" refY="3.5" orient="auto">
        <polygon points="0 0, 10 3.5, 0 7" fill="#c7c7c7"/>
      </marker>
      <marker id="arrowhead-red" markerWidth="10" markerHeight="7" refX="10" refY="3.5" orient="auto">
        <polygon points="0 0, 10 3.5, 0 7" fill="#ee0000"/>
      </marker>
    </defs>
    <!-- Arrows here -->
  </svg>

  <!-- Nodes as positioned divs -->
  <!-- Watermark -->
</div>
</body>
</html>
```

### Base CSS

```css
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
  background: #000;
  font-family: 'Red Hat Text', sans-serif;
  color: #fff;
  display: flex;
  justify-content: center;
  padding: 40px 20px;
}
.diagram { position: relative; width: 1400px; }
h1 {
  font-family: 'Red Hat Display', sans-serif;
  font-size: 28px;
  text-align: center;
  margin-bottom: 8px;
  color: #fff;
}
.subtitle {
  text-align: center;
  font-size: 14px;
  color: #a3a3a3;
  margin-bottom: 40px;
}
.node {
  position: absolute;
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  font-size: 13px;
  line-height: 1.3;
  padding: 10px 14px;
  z-index: 2;
}
.note {
  position: absolute;
  font-size: 12px;
  color: #c7c7c7;
  z-index: 1;
  max-width: 280px;
  line-height: 1.4;
}
.note strong { color: #fff; }

/* SVG arrows */
svg.arrows {
  position: absolute;
  top: 0; left: 0;
  width: 100%; height: 100%;
  z-index: 1;
  pointer-events: none;
}
.arrow { fill: none; stroke: #c7c7c7; stroke-width: 2; }
.arrow-dashed { fill: none; stroke: #c7c7c7; stroke-width: 2; stroke-dasharray: 6 4; }
.arrow-red { fill: none; stroke: #ee0000; stroke-width: 2; }
.arrow-red-dashed { fill: none; stroke: #ee0000; stroke-width: 2; stroke-dasharray: 6 4; }
.arrow-label { font-family: 'Red Hat Text', sans-serif; font-size: 11px; fill: #a3a3a3; }
```

## Node Types

Use these CSS classes for diagram nodes. All use Red Hat brand colors.

| Shape | CSS class | Visual | Colors |
|-------|-----------|--------|--------|
| Circle | `.actor` | People, roles, teams | red-50 `#ee0000` bg, red-60 `#a60000` border |
| Rectangle | `.tool` | Systems, tools, services | gray-80 `#292929` bg, orange-40 `#f5921b` border |
| Rounded rect | `.process` | Processing steps, intake tools | gray-80 `#292929` bg, yellow-40 `#dca614` border, 8px radius |
| Database | `.database` | Data stores, registries | gray-80 `#292929` bg, teal-50 `#37a3a3` border, cylinder shape |
| Cloud | `.cloud` | Actions, patches, abstract ops | gray-80 `#292929` bg, yellow-40 `#dca614` border, 30px radius |
| Output | `.output` | Deliverables, outputs, artifacts | teal-70 `#004d4d` bg, teal-50 `#37a3a3` border |
| Hexagon | `.hexagon` | Gates, milestones, checkpoints | teal-70 `#004d4d` bg, teal-50 `#37a3a3` border, clip-path |
| Diamond | `.decision` | Decision points, conditionals | gray-80 `#292929` bg, orange-40 `#f5921b` border, rotated |

### Node CSS

```css
.actor {
  border-radius: 50%;
  width: 130px; height: 130px;
  background: #ee0000;
  border: 3px solid #a60000;
  color: #fff;
  font-weight: 700;
}
.tool {
  background: #292929;
  border: 2px solid #f5921b;
  border-radius: 3px;
  color: #fff;
  min-width: 140px;
}
.process {
  background: #292929;
  border: 2px solid #dca614;
  border-radius: 8px;
  color: #fff;
  min-width: 150px;
}
.database {
  background: #292929;
  border: 2px solid #37a3a3;
  border-radius: 8px 8px 50% 50% / 8px 8px 20px 20px;
  color: #fff;
  min-width: 130px;
  padding: 14px;
}
.cloud {
  background: #292929;
  border: 2px solid #dca614;
  border-radius: 30px;
  color: #fff;
  min-width: 130px;
  padding: 14px 20px;
}
.output {
  background: #004d4d;
  border: 2px solid #37a3a3;
  border-radius: 3px;
  color: #fff;
  min-width: 140px;
}
.hexagon {
  background: #004d4d;
  border: 2px solid #37a3a3;
  color: #fff;
  min-width: 120px;
  clip-path: polygon(10% 0%, 90% 0%, 100% 50%, 90% 100%, 10% 100%, 0% 50%);
  padding: 16px 24px;
}
.decision {
  background: #292929;
  border: 2px solid #f5921b;
  color: #fff;
  width: 64px; height: 64px;  /* MUST be equal — never use min-width on diamonds */
  padding: 8px;
  transform: rotate(45deg);
}
.decision span {
  transform: rotate(-45deg);
  display: block;
  font-size: 11px;
}
```

## Arrow Types

| Type | CSS class | Use case |
|------|-----------|----------|
| Solid gray | `.arrow` | Primary flow connections |
| Dashed gray | `.arrow-dashed` | Secondary, informational |
| Solid red | `.arrow-red` | Critical paths, feedback loops |
| Dashed red | `.arrow-red-dashed` | Critical informational |

Use `<line>` for straight arrows, `<path>` for curved/bent arrows.
Add `marker-end="url(#arrowhead)"` or `marker-end="url(#arrowhead-red)"`.

Label arrows with `<text class="arrow-label">` positioned near the midpoint.
For labels near node boundaries, use HTML `<div>` with `z-index:3` instead of SVG
`<text>` — SVG renders behind HTML nodes (z-index 1 vs 2).

### Arrow Connectivity Rules

These rules prevent the most common visual bugs. Every one was learned from a real failure.

**Arrow endpoints must land exactly on the node's visual edge:**
- Rectangles: right edge = `left + width`, bottom = `top + height`
- Circles: edge at `center ± radius` in the direction of the arrow
- Rotated diamonds: visual edge = `center ± (size * 0.707)` — NOT `left + width`
- Add 2-4px clearance from edge. Account for arrowhead refX (~8px)

**Route arrows to node EDGES, never through nodes:**
- SVG lines render behind HTML divs — a line through a box looks broken
- Use `<path>` with L-shaped or Z-shaped waypoints to route around boxes
- For "enter from bottom": route DOWN past the box, then UP into bottom edge

**Route arrows around divider/embargo line text:**
- Cross divider lines at LEFT or RIGHT edges, never through center text
- Use L-shaped paths: horizontal first to clear text, then vertical through edge

**Parallel arrow separation:**
- When arrows run near a box edge, offset by 8px for visual separation

### Decision Diamond Rules

Diamonds are the hardest nodes to get right. CSS rotation shifts the visual bounding box.

**Sizing:** Default 64x64. Only use 80x80 if text needs 4+ words.
Never set `min-width` on `.decision` — it stretches the square into a rectangle.

**Visual edge calculation for a diamond at `left:L, top:T, width:S, height:S`:**
- Center: `(L + S/2, T + S/2)`
- Right point: `(center_x + S*0.707, center_y)`
- Bottom point: `(center_x, center_y + S*0.707)`
- Left point: `(center_x - S*0.707, center_y)`
- Top point: `(center_x, center_y - S*0.707)`

**Branch labels (Yes/No/Known/Novel):**
- Place OUTSIDE the arrow, past the diamond's rotated edge (at least 20px past)
- Bold weight, 12px minimum, high-contrast color (`#63993d` green for YES, `#ee0000` red for NO, `#f5921b` orange for other branches)
- Use HTML `<div>` with `z-index:3`, not SVG `<text>` — the rotated diamond covers SVG labels
- Verify every label is readable in the PNG

**BPMN connectors (A1, V1, etc.):**
- If using lettered connector circles, always include a legend
- Prefer dashed arrows without connectors for customer-facing diagrams — cleaner

## Divider Lines

Horizontal dashed lines spanning full width with centered label. Use for phase
boundaries, embargo windows, trust boundaries.

```css
.divider-line {
  position: absolute;
  width: 100%;
  height: 50px;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1;
}
.divider-line::before, .divider-line::after {
  content: '';
  position: absolute;
  left: 0; right: 0;
  height: 2px;
  background: repeating-linear-gradient(90deg, #5e40be 0, #5e40be 12px, transparent 12px, transparent 20px);
}
.divider-line::before { top: 0; }
.divider-line::after { bottom: 0; }
.divider-line span {
  background: #000;
  padding: 4px 16px;
  font-size: 14px;
  color: #876fd4;
  font-weight: 500;
  z-index: 2;
  font-family: 'Red Hat Display', sans-serif;
}
```

## Watermark System

Ask the user for classification level. Apply the matching watermark.

| Level | Rendering |
|-------|-----------|
| `draft` (default) | Orange dashed border box, bottom-left: "WARNING DRAFT -- Pending formal review -- {date}" |
| `internal` | Red border box: "RED HAT INTERNAL -- Not for external distribution" |
| `confidential` | Red background banner, full width: "RED HAT CONFIDENTIAL" |
| `none` | No watermark |

### Watermark CSS

```css
/* DRAFT — position in existing padding, don't extend the page */
.watermark-draft {
  position: absolute;
  bottom: 10px; right: 20px;
  color: #f5921b;
  font-size: 13px;
  border: 2px dashed #f5921b;
  padding: 8px 16px;
  border-radius: 3px;
  background: rgba(79,26,26,0.6);
}

/* INTERNAL */
.watermark-internal {
  position: absolute;
  bottom: 20px; left: 20px;
  color: #ee0000;
  font-size: 13px;
  border: 2px solid #ee0000;
  padding: 8px 16px;
  border-radius: 3px;
  background: rgba(79,26,26,0.6);
}

/* CONFIDENTIAL */
.watermark-confidential {
  position: absolute;
  bottom: 0; left: 0; right: 0;
  background: #ee0000;
  color: #fff;
  font-size: 16px;
  font-weight: 700;
  text-align: center;
  padding: 12px;
  font-family: 'Red Hat Display', sans-serif;
  letter-spacing: 2px;
}
```

## PNG Rendering

### Preferred: Headless Chrome (zero dependencies)

```bash
# OS detection — pick the right Chrome binary
if [[ "$(uname)" == "Darwin" ]]; then
  CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
elif command -v google-chrome &>/dev/null; then
  CHROME="google-chrome"
elif command -v chromium-browser &>/dev/null; then
  CHROME="chromium-browser"
elif command -v chromium &>/dev/null; then
  CHROME="chromium"
else
  echo "No Chrome/Chromium found" >&2; exit 1
fi

"$CHROME" \
  --headless --disable-gpu \
  --screenshot="/absolute/path/to/output.png" \
  --window-size=1920,1100 \
  --force-device-scale-factor=2 \
  "file:///absolute/path/to/diagram.html"
```

### Fallback: Puppeteer (better for web fonts)

Puppeteer's `waitUntil: 'networkidle0'` ensures Google Fonts load before screenshot.
Headless Chrome doesn't have this, so use Puppeteer when web font rendering is critical.

```bash
NODE_PATH=$(find ~/.npm/_npx -path "*/node_modules/puppeteer" -maxdepth 4 2>/dev/null \
  | head -1 | sed 's|/puppeteer$||') \
node -e "
const puppeteer = require('puppeteer');
(async () => {
  const browser = await puppeteer.launch({headless: true});
  const page = await browser.newPage();
  await page.setViewport({width: 1870, height: 1100, deviceScaleFactor: 2});
  await page.goto('file://' + process.argv[1], {waitUntil: 'networkidle0'});
  await page.screenshot({path: process.argv[2], fullPage: true});
  await browser.close();
})();
" /absolute/path/to/diagram.html /absolute/path/to/output.png
```

If neither Chrome nor Puppeteer is available:
```bash
npx -y @mermaid-js/mermaid-cli  # installs puppeteer as a dependency
```

### Self-Verification (MANDATORY)

After every HTML edit:
1. Render PNG via headless Chrome (or Puppeteer fallback)
2. Read the PNG back with the Read tool (Claude can view image files)
3. Visually verify: arrows connect to edges, labels readable, no overlaps
4. Report findings before declaring done

**Why:** Claude cannot look at a browser window. The only way to verify is screenshot
to file and Read it. There is no shortcut — the PNG step cannot be skipped.

Report both file paths when done:
```
Diagram generated!
  HTML: /path/to/diagram.html
  PNG:  /path/to/diagram.png
```

## Layout Rules

**SVG viewBox must match container:** If the diagram div is 1400x900, the SVG viewBox
must be `0 0 1400 900`. Mismatched dimensions cause arrows to appear offset from nodes.

**Container sizing:** Set height to content height + ~80px for watermark padding. Don't
set height too large — creates dead whitespace below the diagram. Render, check, adjust.

**Landscape target:** Aim for ~1.7:1 aspect ratio for Google Docs landscape. Viewport
1870x1100 at deviceScaleFactor:2 produces crisp print-quality PNGs.

**If content doesn't fit:** Split into two diagrams with continuation arrows (teal
rounded-rect nodes labeled "Continues on [diagram name]").

**Layout process:**
- Start by listing all nodes with their types and rough grouping (rows/columns)
- Place nodes top-to-bottom, left-to-right following the process flow
- Use 160-200px horizontal spacing between nodes in the same row
- Use 120-160px vertical spacing between rows
- Keep the diagram width at 1400px for consistent rendering
- Use `<small>` tags inside nodes for secondary text
- Add `.note` divs for contextual annotations outside the flow

## What NOT to Do

- Do NOT use Mermaid (layout limitations for complex flows)
- Do NOT use external CSS files (must be self-contained)
- Do NOT use the Red Hat logo or fedora imagery
- Do NOT use red to represent negative/error states (red = Red Hat brand)
- Do NOT create interactive features (hover, click, zoom) -- static diagrams only
