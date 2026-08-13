# Design

<!-- impeccable:design-schema 1 -->

## The world

**The paper triage tag.** IT triage borrows its name and its logic from
emergency medicine, and the physical triage tag is the support ticket's direct
ancestor: a card designed to assign priority fast, under pressure, on incomplete
information. That is this product's job description.

Triage tags are high-visibility utility objects — signal red, hazard amber,
triage green, heavy black rule work, perforations, serial numbers, rubber-stamp
overprints on bright card stock. They are not soft stationery. Nothing here is
cream, gradient, glass, or rounded.

Handled with restraint: the etymology is stated plainly so the lineage reads as
lineage, never as costume. No medical imagery beyond the form language itself.

## Color

Strategy: **full palette**, four named roles carried from the artifact.

| Token | Value | Role |
|---|---|---|
| `--card` | `#F2F0EB` | Card stock. The ground. Warm-grey pulp, not cream — it must read as stock, never as paper-for-mood. |
| `--ink` | `#141414` | Rule work, body text, printed labels. |
| `--immediate` | `#C8102E` | Signal red. P1 and errors only. Never decorative. |
| `--urgent` | `#E8A33D` | Hazard amber. P2. |
| `--delayed` | `#2E7D4F` | Triage green. P3/P4 and passing states. |
| `--stamp` | `#2B4C7E` | Stamp-pad blue. Overprints, corrections, annotations. |

Severity **must never be carried by colour alone.** Position on the strip and the
printed label both encode it, so the page reads correctly in greyscale and to a
colour-blind reader. This is the artifact's own logic, not an accessibility
retrofit — real tags are used in bad light by people under stress.

## Type

System faces only. No webfont, no build step — consistent with the project's
zero-dependency constraint, and correct for the world: these forms were printed
and typed, not designed in a browser.

- **Printed form matter** — condensed grotesque (`Arial Narrow` and its
  fallbacks). Field labels, headings, tag furniture. Uppercase with wide
  tracking is this world's native register for labels; it is form vocabulary,
  not a decorative eyebrow.
- **Filled-in data** — `Courier New`. Ticket text, model output, measurements.
  Monospace here is the face these forms were actually typed on and the face
  measurements belong in, not a costume for "technical".

The two faces carry the page's central distinction: **what was printed** versus
**what was written in**. Nothing else needs to signal that difference.

## Structure

- **Heavy rules over boxes.** 2–3px black rules divide the page. Same-size
  rounded cards are the lazy container and are not this world's grammar.
- **Perforation** (dotted rules) separates a detachable region from its parent —
  used only where something is genuinely separable in meaning, such as the
  scorecard stub from the tag body.
- **Serial numbers** are real identifiers (`INC-1001`, `EVAL-02`), never
  decorative section numbering.
- **Stamps** mark status: applied at a slight rotation, in `--stamp` or
  `--immediate`, overprinting the content beneath rather than sitting beside it.

## Motion

One authored moment: the severity strip tearing to its assigned priority, once,
on first view. Everything else is static. Content is fully visible without
JavaScript and without motion; the tear is a confirmation of a state already
rendered, never the delivery mechanism for it.

Respects `prefers-reduced-motion` by rendering the torn end state immediately.

## Prohibitions

Each is a device this world does not use, not a general rule:

- No gradients, glass, blur, or soft shadows. Print has hard edges; ink either
  sits on the stock or does not.
- No border radius above 2px. Card stock is guillotined, not rounded.
- No colour-only status encoding.
- No icon-plus-heading-plus-text card grids.

## Constraints

Single static file, no build step, no framework, no network requests on load.
Must work at 360px, be fully keyboard reachable, and remain legible with images
and JavaScript disabled.
