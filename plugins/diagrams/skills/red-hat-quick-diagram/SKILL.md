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
4. Auto-screenshot to PNG via Puppeteer
5. Report both file paths to user

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
  width: 100px; height: 100px;
  transform: rotate(45deg);
}
.decision span {
  transform: rotate(-45deg);
  display: block;
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
/* DRAFT */
.watermark-draft {
  position: absolute;
  bottom: 20px; left: 20px;
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

## Auto-PNG Generation

After writing the HTML file, render to PNG using Puppeteer:

```bash
NODE_PATH=$(find ~/.npm/_npx -path "*/node_modules" -maxdepth 3 2>/dev/null | head -1) \
node -e "
const puppeteer = require('puppeteer');
(async () => {
  const browser = await puppeteer.launch({headless: true});
  const page = await browser.newPage();
  await page.setViewport({width: 1500, height: 1900, deviceScaleFactor: 2});
  await page.goto('file://HTML_PATH', {waitUntil: 'networkidle0'});
  const body = await page.\$('body');
  const box = await body.boundingBox();
  await page.setViewport({width: Math.ceil(box.width) + 80, height: Math.ceil(box.height) + 80, deviceScaleFactor: 2});
  await page.screenshot({path: 'PNG_PATH', fullPage: true});
  await browser.close();
  console.log('PNG saved to PNG_PATH');
})();
"
```

If Puppeteer is not installed, tell the user:
```bash
npx -y @mermaid-js/mermaid-cli  # This installs puppeteer as a dependency
```

Report both file paths when done:
```
Diagram generated!
  HTML: /path/to/diagram.html
  PNG:  /path/to/diagram.png
```

## Layout Tips

- **Start by listing all nodes** with their types and rough grouping (rows/columns)
- **Place nodes top-to-bottom, left-to-right** following the process flow
- **Use 160-200px horizontal spacing** between nodes in the same row
- **Use 120-160px vertical spacing** between rows
- **Keep the diagram width at 1400px** for consistent rendering
- **Adjust `min-height` on `.diagram`** to fit all content
- **Use `<small>` tags** inside nodes for secondary text
- **Add `.note` divs** for contextual annotations outside the flow

## What NOT to Do

- Do NOT use Mermaid (layout limitations for complex flows)
- Do NOT use external CSS files (must be self-contained)
- Do NOT use the Red Hat logo or fedora imagery
- Do NOT use red to represent negative/error states (red = Red Hat brand)
- Do NOT create interactive features (hover, click, zoom) -- static diagrams only
