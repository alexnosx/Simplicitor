# business_pitch: Water-Colored Splashes restyle

**Date:** 2026-06-07
**Status:** Design accepted; awaiting implementation plan.
**Scope:** Replace the bundled `business_pitch` default template (manifest + .pptx) so its visual style comes from the Water-Colored-Splashes deck. Three slide types. No engine changes.

## Goal

Refresh the default `business_pitch` look so it matches the Water-Colored-Splashes PowerPoint that ships with this work. Keep the work contained to the one template; do not touch the templates engine, prompt builder, or renderer.

## Constraints (from the brainstorming session)

The water-color source deck has 36 sample slides, 3 masters, 20 layouts. Simplicitor's renderer (`prs.slide_layouts[layout_index]` in `simplicitor/templates_engine/render_pptx.py`) reaches only the first master's layouts. On the water-color deck that is exactly 3 layouts, all with two `BODY` placeholders at `idx=10` and `idx=11`:

| Master 0 layout | Sample text on idx=10 (top, larger) | Sample text on idx=11 (below, smaller) |
|---|---|---|
| `[0] Cover Slide layout` | "FREE PPT TEMPLATES" | "INSERT THE TITLE OF YOUR PRESENTATION HERE" |
| `[1] End Slide Layout` | "Thank you" | "Insert the title of your subtitle Here" |
| `[2] 2_End Slide Layout` | "Welcome!!" | "Insert the title of your subtitle Here" |

Implications accepted by choosing this approach (path "A1" in the brainstorming session):

1. No styled bullet placeholders exist on Master 0. All fields are `kind: text`.
2. The richer content layouts (Agenda, Basic, Section Break, Images and Contents) live on Master 1 and Master 2 and are unreachable without an engine change. We do not change the engine.
3. Generated decks of 4+ slides will visually repeat: the LLM will reuse the same three layouts.
4. Text does not autosize; long titles overflow the design.

These are known trade-offs, not bugs.

## Scope

In scope:

| File | Change |
|---|---|
| `simplicitor/templates_engine/builtin/business_pitch/template.pptx` | Replaced with the water-color deck, sample slides stripped (0 slides remain). |
| `simplicitor/templates_engine/builtin/business_pitch/manifest.yaml` | Rewritten for 3 slide types: `title`, `statement`, `closing`. |
| `scripts/build_business_pitch_pptx.py` | New one-shot script that strips sample slides from a source `.pptx` and writes the bundled `template.pptx`. Makes the result reproducible if the source deck is ever re-downloaded or replaced. |
| `tests/templates_engine/test_builtin_templates.py` | The seven `business_pitch_*` tests are rewritten against the new 3-slide-type structure. `technical_overview` tests are left alone. |

Out of scope (deferred, not forgotten):

- "Default of 3 slides" enforcement at generation time. Today slide count is decided by the LLM from the user's prompt; the manifest has no count concept. Adding one needs a `default_slide_count` field and a `prompt_builder` change. Track separately if wanted.
- Extending the renderer to address layouts across all masters.
- Visual restyling of `technical_overview`.
- Dropping unused masters (Master 1, Master 2) from the file. File grows from 27 KB to roughly 1.8 MB. We accept the bloat.
- Migration of users who already have the old `business_pitch` in their `Documents\Simplicitor\Templates`. `ensure_default_templates()` will not overwrite the existing folder; users who want the new look delete the folder manually. Note in CHANGELOG.

## Manifest

```yaml
name: business_pitch
type: pptx
template_file: template.pptx
description: Business pitch deck with the Water-Colored Splashes design. Cover, key message, and thank-you slides.
slide_types:
  title:
    layout_index: 0          # Cover Slide layout
    fields:
      - name: title
        placeholder_idx: 10
        kind: text
        required: true
        max_chars: 60
      - name: subtitle
        placeholder_idx: 11
        kind: text
        required: false
        max_chars: 80
  statement:
    layout_index: 2          # 2_End Slide Layout (centered)
    fields:
      - name: heading
        placeholder_idx: 10
        kind: text
        required: true
        max_chars: 40
      - name: subhead
        placeholder_idx: 11
        kind: text
        required: false
        max_chars: 80
  closing:
    layout_index: 1          # End Slide Layout (Thank-you band)
    fields:
      - name: message
        placeholder_idx: 10
        kind: text
        required: true
        max_chars: 40
      - name: subtitle
        placeholder_idx: 11
        kind: text
        required: false
        max_chars: 80
```

Layout-index reconciliation: indices are taken from a fresh inspection of the water-color deck's Master 0 (Cover Slide = 0, End Slide = 1, 2_End Slide = 2). The existing `scripts/inspect_template.py` is the source of truth post-build; the manifest's leading comment will tell readers to re-verify with it if `template.pptx` is rebuilt.

Field-naming decision (Cover Slide layout): `idx=10` (the larger, upper box) is named `title`; `idx=11` (the smaller, lower box) is named `subtitle`. The water-color designer used the boxes in the opposite sense in their sample, but for a pitch deck a prominent project name in the larger box is the right default.

## Build script

`scripts/build_business_pitch_pptx.py` is a one-shot rebuild tool. Not wired into the regular `build.py`; it runs only when the source deck changes.

Behaviour:

1. Accept the source `.pptx` path as a single required CLI argument. There is no default path: the source deck lives outside the repo (a designer's machine, a download folder), and a silent default risks rebuilding the bundled template from the wrong file. Missing/invalid argument: print usage and exit 1.
2. Open it with `python-pptx`.
3. Delete every slide. Keep masters and layouts untouched.
4. Save to `simplicitor/templates_engine/builtin/business_pitch/template.pptx`.
5. Report the layout count and file size on stdout so the operator can sanity-check.

Errors:

- Missing source file: exit with a clear message; do not write a partial output.
- python-pptx open failure: re-raise; this is a one-shot dev tool, not user-facing.

The script does not modify the manifest. After running it, the operator runs `python scripts/inspect_template.py simplicitor/templates_engine/builtin/business_pitch/template.pptx` and confirms the layout indices in the manifest still hold.

## Tests

The Tier-1 manifest tests in `tests/templates_engine/test_builtin_templates.py` that target `business_pitch` are rewritten. The Tier-2 render tests (gated on `business_pitch/template.pptx` existing) are rewritten to use the new placeholder indices (`10`, `11`) and the new slide types.

Test list after rewrite:

- `test_business_pitch_manifest_loads` (kept; same shape)
- `test_business_pitch_has_three_slide_types` (renamed from `_four_`; checks `{title, statement, closing}`)
- `test_business_pitch_lint_clean` (kept)
- `test_business_pitch_subtitle_optional` (replaces the old `closing_contact_not_required`; asserts `title.subtitle.required is False`)
- `test_business_pitch_title_slide_renders` (rewritten: uses `placeholders[10]`, not `[0]`)
- `test_business_pitch_all_three_slide_types_render` (renamed; covers title/statement/closing)
- `test_business_pitch_subtitle_absent_no_issues` (replaces `closing_contact_absent_no_issues` with the new optional field)
- `test_business_pitch_subtitle_written` (replaces `closing_contact_written`)

Deleted from the suite (no analog in the new template):

- `test_business_pitch_agenda_items_required_max_five` (no `agenda` slide type)
- `test_business_pitch_agenda_items_exact_order_and_count` (no `agenda` slide type)

Discovery tests (`test_builtins_appear_in_list_templates`, `test_builtin_available_flag_true`) are untouched: they assert template existence, not slide-type shape.

`technical_overview` tests are untouched.

## Migration note

When the new template ships, existing users will keep the old `business_pitch` they have cached in their templates folder, because `ensure_default_templates()` preserves anything already present. This is intentional behaviour. The CHANGELOG entry tells users that deleting `Documents\Simplicitor\Templates\business_pitch` triggers a re-seed with the new design on next launch.

## Risks and how they show up

| Risk | Symptom | Response |
|---|---|---|
| Layout indices in the manifest go stale if the source deck changes. | Render-time `ManipulationError` from `render_pptx._get_placeholder` ("Manifest and template are out of sync"). | Re-run `scripts/inspect_template.py`; update manifest indices. |
| Long titles overflow the design. | Visual overflow in PowerPoint; no engine error. | `max_chars` in the manifest is the soft guardrail; the renderer logs a degrade warning when exceeded. |
| Multi-master file bloat surprises the build size budget. | `dist\Simplicitor.exe` grows. | If it matters, take the deferred work to drop Master 1 / Master 2; not now. |
| User keeps using the old `business_pitch`. | They never see the new look. | Documented in CHANGELOG. No code response. |
