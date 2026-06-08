# business_pitch: Charts 16x9 restyle

**Date:** 2026-06-07
**Status:** Design accepted; implementation landing alongside this spec.
**Scope:** Replace the bundled `business_pitch` template (manifest + .pptx) with the Charts 16x9 source deck. Restore the original four-slide-type structure (title / agenda / content / closing) now that the source deck has bullet-capable placeholders. No engine changes.

## Why this re-restyle

The earlier water-color restyle (see `2026-06-07-business-pitch-watercolor-design.md`) was constrained by the source deck: only three reachable layouts on Master 0, all with `BODY`-typed placeholders, no bullet styling. Result: `business_pitch` shrank to three text-only slide types (title / statement / closing) with no `agenda` and no bulleted `content`.

The Charts template the user uploaded next changes the constraint. It has:

| | Water-color | Charts |
|---|---|---|
| Size | 1.8 MB source | 642 KB source |
| Sample slides | 36 | 5 |
| Masters | 3 | 1 |
| Reachable layouts (Master 0) | 3 (Cover / End / 2_End) | 12 (full standard MS set) |
| Bullet-capable placeholders | None on Master 0 | `OBJECT` on layouts 1, 2, 4, 5, 7, 8 |
| Aspect ratio | 4:3-ish, 10x5.6 in | 16:9 widescreen, 10x5.6 in |

The Charts deck is structurally a standard PowerPoint template wearing a chart-styled visual theme. That means the original four-slide-type business_pitch structure becomes possible again, with proper bullet lists on the agenda and content slides.

## Scope

In scope:

| File | Change |
|---|---|
| `simplicitor/templates_engine/builtin/business_pitch/template.pptx` | Replaced. Rebuilt from the Charts 16x9 source via `scripts/build_business_pitch_pptx.py`, sample slides stripped. ~511 KB. |
| `simplicitor/templates_engine/builtin/business_pitch/manifest.yaml` | Rewritten. Four slide types: `title`, `agenda`, `content`, `closing`. `agenda` and `content` use proper `bullets` fields. |
| `tests/templates_engine/test_builtin_templates.py` | The `business_pitch_*` tests rewritten for the four-type structure. `technical_overview` tests untouched. |

Out of scope:

- The water-color spec at `2026-06-07-business-pitch-watercolor-design.md` is kept as the historical record of that phase. Not deleted.
- The build script `scripts/build_business_pitch_pptx.py` is unchanged; it takes the source path as a CLI argument and now lives a second purpose.
- `technical_overview` template is unchanged.
- Migration: users who already have the prior `business_pitch` (water-color, or even older) cached in `Documents\Simplicitor\Templates` keep their copy. `ensure_default_templates()` does not overwrite. Delete the folder to receive the Charts version on next launch. Same migration story as before.

## Manifest

```yaml
name: business_pitch
type: pptx
template_file: template.pptx
description: Business pitch deck with the Charts 16x9 design. Title, agenda, content, and closing slides.
slide_types:
  title:
    layout_index: 0          # Title Slide
    fields:
      - name: title
        placeholder_idx: 0
        kind: text
        required: true
        max_chars: 60
      - name: subtitle
        placeholder_idx: 1
        kind: text
        required: false
        max_chars: 120
  agenda:
    layout_index: 1          # Title and Content
    fields:
      - name: heading
        placeholder_idx: 0
        kind: text
        required: true
        max_chars: 40
      - name: items
        placeholder_idx: 1
        kind: bullets
        required: true
        max_items: 5
  content:
    layout_index: 1          # Title and Content
    fields:
      - name: heading
        placeholder_idx: 0
        kind: text
        required: true
        max_chars: 60
      - name: bullets
        placeholder_idx: 1
        kind: bullets
        required: false
        max_items: 6
  closing:
    layout_index: 3          # Section Header
    fields:
      - name: heading
        placeholder_idx: 0
        kind: text
        required: true
        max_chars: 60
      - name: statement
        placeholder_idx: 1
        kind: text
        required: true
        max_chars: 160
```

Notes on the closing layout choice: layout 3 (Section Header) carries `TITLE` (idx 0) and `BODY` (idx 1), conventionally used as section-name + section-description. For a closing slide, that maps cleanly to `heading` (the prominent closing line, e.g. "Thank You") + `statement` (the supporting message, e.g. "Reach out anytime."). Layout 6 (Title Only) was too sparse for a real closing; layout 8 (Content with Caption) was richer than needed and would require a third field we don't have a use for.

Both `agenda` and `content` map to layout 1 (Title and Content). The single layout intentionally serves both: `agenda` is the special-case "must have bullet items" usage, `content` is the general-purpose "may have bullets" usage. The shared layout keeps the rendered deck visually consistent.

## Build script

The existing `scripts/build_business_pitch_pptx.py` runs unchanged:

```
python scripts/build_business_pitch_pptx.py "C:\Users\nos\Downloads\162538-charts-template-16x9.pptx"
```

Strips the 5 sample slides, writes the new `template.pptx` to the bundled location. The script reports the layout count and file size on stdout; the operator re-runs `python scripts/inspect_template.py simplicitor/templates_engine/builtin/business_pitch/template.pptx` and confirms manifest indices.

## Tests

Net change in `tests/templates_engine/test_builtin_templates.py`:

Renamed / rewritten:
- `test_business_pitch_has_three_slide_types` → `test_business_pitch_has_four_slide_types`
- `test_business_pitch_all_three_slide_types_render` → `test_business_pitch_all_four_slide_types_render` (covers title/agenda/content/closing)

Added:
- `test_business_pitch_agenda_items_required_max_five` (verifies the restored bullet field)
- `test_business_pitch_closing_statement_required` (verifies the new closing's statement field)
- `test_business_pitch_agenda_items_exact_order_and_count` (verifies bullet ordering through render)

Updated:
- `test_business_pitch_title_subtitle_optional` (`max_chars` value updated from 80 to 120, matching the new manifest)

Deleted:
- `test_business_pitch_all_fields_are_text` (was a water-color-era invariant — no longer true now that bullets fields exist; deleting is correct, not a regression)

Discovery tests (`test_builtins_appear_in_list_templates`, `test_builtin_available_flag_true`) untouched: they assert template existence, not slide-type shape.

## Risks

| Risk | Symptom | Response |
|---|---|---|
| Section Header layout's BODY placeholder is positioned above the TITLE placeholder in this template's design. | The "statement" field renders above the "heading" field visually, opposite of typical Section Header layouts. | If the rendered closing slide reads wrong, swap the placeholder indices in the manifest (idx 0 ↔ idx 1). Manifest comment already tells readers to re-verify with `inspect_template.py`. |
| Long titles overflow the design. | Visual overflow in PowerPoint; no engine error. | `max_chars` is the soft guardrail; renderer logs a degrade warning when exceeded. |
| Users keep the old water-color or pre-water-color business_pitch they have cached. | They never see the Charts version. | Documented in CHANGELOG. Delete the folder to re-seed. |
