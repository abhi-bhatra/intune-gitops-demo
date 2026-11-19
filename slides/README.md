# Slide Deck — Intune Meets GitOps

A self-contained, offline HTML/[reveal.js](https://revealjs.com) deck. No build step, no
internet connection needed at the venue — all library assets are vendored in
`vendor/reveal.js/`.

## Presenting

Open `index.html` directly in a browser (double-click it, or `open index.html` /
`xdg-open index.html`). Reveal.js handles the rest:

- **Arrow keys / space** — navigate slides
- **S** — open the Speaker Notes window (second screen / presenter laptop).
  Every slide has timing guidance and talking points in its notes.
- **F** — fullscreen
- **Esc** — slide overview grid

No local web server is required — everything is relative-pathed and loads fine from
`file://`.

## Exporting to PDF (backup copy)

Browser print-to-PDF works out of the box with reveal.js's built-in print stylesheet:

1. Open `index.html`, append `?print-pdf` to the URL (e.g.
   `file:///path/to/index.html?print-pdf`).
2. Open the browser's Print dialog, destination "Save as PDF", disable headers/footers,
   set margins to "None".
3. Save as a backup in case the venue laptop can't run a browser deck live.

## Structure

- `index.html` — the 18 slides and all speaker notes.
- `theme.css` — custom dark theme (colors, typography, every infographic component:
  pipeline diagram, ring diagram, timeline, stat cards, concept-mapping table, etc.)
- `vendor/reveal.js/dist/` — vendored reveal.js core + notes/highlight/zoom plugins.
  Fetched once via `npm install reveal.js` into a scratch directory and copied in; no
  `node_modules`/`package.json` is committed here.

## Content map

Slide content follows the same narrative as [`../DEMO_SCRIPT.md`](../DEMO_SCRIPT.md):
Problem → GitOps-for-Windows analogy → pipeline → rings → **live demo** (commands live
in DEMO_SCRIPT.md Acts 2–6, not duplicated here) → debrief → Device Health Attestation
gotcha → lessons → closing. See [`../GLOSSARY.md`](../GLOSSARY.md) for any Intune/Azure
jargon used on slides.

## Known placeholders

None currently — speaker name/role, event name/date, and contact details are filled
in. If reused for a different event, update:
- Slide 1 footer + `.brand` div, Slide 2 speaker block — name/role/event/date
- Slide 18 — contact chips
