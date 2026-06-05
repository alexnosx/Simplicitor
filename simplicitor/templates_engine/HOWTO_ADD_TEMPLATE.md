# How to add a template to Simplicitor

A template is a folder containing two files: a stripped `.pptx` (design only, no slides) and a `manifest.yaml` that describes the slide types and their fillable fields. This guide walks through both the automated path (upload through the app or CLI) and the manual path (hand-crafting a built-in template).

---

## Option A: Upload through the app or CLI (user templates)

This is the normal path for templates you or a client have built. Simplicitor imports the deck and generates a draft manifest automatically.

### 1. Build your PowerPoint deck using real layout placeholders

The deck must use PowerPoint's built-in placeholder system -- not manually inserted text boxes. The simplest way to verify this is to open the deck, go to a slide, and look at the Outline view. If text appears there, the slide uses placeholders. If the outline is empty but the slide has text, those are text boxes and the deck will fail the usability check.

Each layout you want to use as a slide type needs at least one content placeholder (idx >= 1). The title placeholder (idx 0) is always available.

### 2. Import the deck

**Via CLI:**
```
python simplicitor/cli.py import path/to/your_deck.pptx
```

**Via app:** Click "From template..." in the Create panel, then "Upload a .pptx...". Select your deck.

Simplicitor will inspect the deck, score the layouts, and -- if at least one layout is usable -- strip the content and write the template folder. The output folder is created under `%APPDATA%\Simplicitor\templates\<name>\` on Windows.

If the deck fails the usability check, you will see the hard-stop message. Go back to PowerPoint, rebuild the slides using slide layouts, and re-import.

### 3. Review and fix the draft manifest

The import produces a draft `manifest.yaml`. Open it. Any placeholder that could not be auto-labeled has a name like `NEEDS_LABEL_<idx>`. Replace those names with something meaningful (e.g. `body`, `caption`, `logo`).

The manifest is in `%APPDATA%\Simplicitor\templates\<name>\manifest.yaml`.

**Validate your edits:**
```
python simplicitor/cli.py list-templates
```

If the manifest has errors, the template is silently skipped. Check that YAML parses cleanly (no tabs, correct indentation) and that `kind` is one of `text`, `bullets`, or `image`.

### 4. Lint the manifest (optional but recommended)

The CLI `render` command validates the manifest when it loads it. A quick lint check:
```python
from templates_engine.manifest import load_manifest, lint_manifest
m = load_manifest("path/to/manifest.yaml")
for w in lint_manifest(m): print(w)
```

Common warnings: slide types with no fields (blank slides), `max_chars` on a `bullets` field (has no effect).

### 5. Test with a hand-written spec

Write a minimal JSON spec and render it to confirm the template works end to end:
```
python simplicitor/cli.py render --template <name> --spec test_spec.json --out test_out.pptx
```

Where `test_spec.json` follows the shape the manifest expects:
```json
{
  "slides": [
    {"type": "title", "fields": {"title": "Test Title", "subtitle": "Subtitle here"}},
    {"type": "content", "fields": {"heading": "Section One", "bullets": ["Point A", "Point B"]}}
  ]
}
```

Open the output in PowerPoint and verify it looks correct.

---

## Option B: Hand-craft a built-in template

Built-in templates ship with the app (read-only, available to all users). They live in `simplicitor/templates_engine/builtin/<name>/`. Follow these steps when adding a new built-in.

### 1. Design and save the .pptx

Build the deck in PowerPoint. Use the Slide Master view to define layouts with named placeholders. Each layout becomes one slide type in the manifest.

Save the file to `simplicitor/templates_engine/builtin/<name>/template.pptx`.

### 2. Run the inspector to get placeholder indices

```
python simplicitor/cli.py inspect simplicitor/templates_engine/builtin/<name>/template.pptx
```

Read the output carefully. For each layout you want to expose:
- Note the `layout_index` (the number in `[  N]`).
- Note the `idx` of each placeholder you want to fill.
- Custom placeholders (`[CUSTOM]`, idx >= 10) are skipped by the renderer -- do not reference them.

### 3. Write the manifest by hand

Create `simplicitor/templates_engine/builtin/<name>/manifest.yaml`. Use an existing built-in as a reference (`builtin/business_pitch/manifest.yaml` is a good starting point).

**Required top-level keys:**
| Key | Value |
|-----|-------|
| `name` | Short identifier, snake_case, matches the folder name |
| `type` | `pptx` (always) |
| `template_file` | `template.pptx` |
| `description` | One sentence describing the template |
| `slide_types` | Dict of slide type name -> slide type definition |

**Each slide type:**
| Key | Value |
|-----|-------|
| `layout_index` | Integer from the inspector output |
| `fields` | List of field definitions |

**Each field:**
| Key | Value |
|-----|-------|
| `name` | Snake_case identifier (must be unique within the slide type) |
| `placeholder_idx` | Integer `idx` from the inspector output |
| `kind` | `text`, `bullets`, or `image` |
| `required` | `true` or `false` |
| `max_chars` | (text fields only) Optional max character count |
| `max_items` | (bullets fields only) Optional max item count |

Field names become JSON keys in the content the LLM produces. Choose names that are self-explanatory: `title`, `heading`, `body`, `bullets`, `caption`, `contact`.

### 4. Verify indices match the template

The most common failure mode is a mismatch between the `layout_index` or `placeholder_idx` in the manifest and the actual template file. After writing the manifest, run:

```
python simplicitor/cli.py render --template <name> --spec test_spec.json --out test_out.pptx
```

A `ManipulationError` about "layout_index not found" or "placeholder idx N not found" means the manifest references an index that does not exist in the template. Re-run the inspector and cross-check.

### 5. Lint and commit

```python
from templates_engine.manifest import load_manifest, lint_manifest
m = load_manifest("simplicitor/templates_engine/builtin/<name>/manifest.yaml")
for w in lint_manifest(m): print(w)
```

If lint is clean, run the full test suite:
```
python -m pytest tests/ -q
```

Commit both `template.pptx` and `manifest.yaml` together. Add a comment at the top of the manifest noting how indices were verified (see the existing built-ins for the pattern).

---

## Manifest reference: field kinds and constraints

| kind | Content type | Relevant constraints |
|------|-------------|----------------------|
| `text` | Single string | `max_chars`: warn if exceeded (text still rendered in full) |
| `bullets` | List of strings | `max_items`: warn if exceeded (all bullets still rendered) |
| `image` | File path string | (none) -- missing or unreadable image is a warning, not an error |

Optional fields (required: false) are omitted from the LLM prompt example and skipped silently by the renderer if absent in the content JSON.

Required fields that are missing from the content will cause `validate_content` to return errors, triggering the repair loop.

---

## Troubleshooting

**"Template not found" when running CLI commands**
The template folder must contain both `template.pptx` and `manifest.yaml`. A folder with only one of those files is silently skipped by `list_templates`.

**"Manifest validation failed"**
The manifest YAML does not match the schema. Common causes: missing a required key, `kind` spelled wrong, a field name containing a space or hyphen (use snake_case). Read the error message carefully -- it names the failing field.

**"Placeholder idx N not found in template"**
The `placeholder_idx` in the manifest does not match any placeholder in the layout at `layout_index`. Re-run `simplicitor inspect` and verify the idx values.

**"Layout index N not found in template"**
The `layout_index` in the manifest exceeds the number of layouts in the template. The template may have been rebuilt or replaced without updating the manifest.

**NEEDS_LABEL fields in draft manifest**
Placeholders the auto-labeler could not name confidently are marked `NEEDS_LABEL_<idx>`. These load without error, but the LLM will see field names like `NEEDS_LABEL_2: text, required` in its prompt, which produces poor output. Replace every NEEDS_LABEL name with a meaningful snake_case identifier before the template goes into use.
