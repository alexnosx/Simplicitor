# Phase H: PPTX Renderer Design

**Date:** 2026-05-29
**Scope:** `simplicitor/templates_engine/render_pptx.py` + CLI command `render` in `simplicitor/cli.py`
**Depends on:** Phases A-G (manifest, validation, config, breakdown all committed)

---

## 1. Public API

```python
def render(
    manifest: Manifest,
    content: dict,
    out_path: str | Path,
    template_dir: str | Path,
) -> dict:
    ...
```

**Parameters:**
- `manifest` -- validated `Manifest` from `load_manifest()`.
- `content` -- validated content dict from `validate_content()`. Caller must pre-validate; `render()` trusts the input. Docstring states this explicitly.
- `out_path` -- destination path. Normalized inside `render()`: if suffix is empty, `.pptx` is appended silently. Otherwise accepted as-is. The CLI also applies this normalization before calling `render()`, but `render()` must do it internally too so Phase J callers don't need to.
- `template_dir` -- directory containing `manifest.template_file` (e.g. the folder returned by `list_templates()`).

**Returns:** `{"path": Path, "issues": list[str]}`
- `path` -- the resolved output path (with `.pptx` appended if needed).
- `issues` -- flat list of degrade warning strings (one per affected field). Empty list on a clean render.

---

## 2. Internal structure

### `_render_slide(slide, slide_def, fields, slide_idx) -> list[str]`

Private helper. Called once per slide after `prs.slides.add_slide()`. Returns a list of degrade warning strings for that slide.

**Field dispatch:**

| kind | placeholder found? | value present? | action |
|------|--------------------|---------------|--------|
| `text` | yes | yes | `ph.text = value`; if `len > max_chars`, warn + collect |
| `text` | yes | no (optional) | skip silently |
| `text` | no | any | `ManipulationError` (genuine fault) |
| `bullets` | yes | yes | `tf.clear()`; add one paragraph per item; if `len > max_items`, warn + collect (all bullets rendered, no cap) |
| `bullets` | yes | no (optional) | skip silently |
| `bullets` | no | any | `ManipulationError` |
| `image` | yes | yes (path exists) | `ph.insert_picture(img_path)` -- capture returned ph (original ref invalidated) |
| `image` | yes | yes (path missing or insert fails) | warn + collect + skip (degrade) |
| `image` | yes | no (optional) | skip silently |
| `image` | no | any | `ManipulationError` |

Placeholder is accessed via `slide.placeholders[idx]` (python-pptx `_SlidePlaceholders` supports idx lookup). If idx is not present, `ManipulationError` is raised.

---

## 3. Error handling

### Genuine faults (raise immediately, no partial file written)

| Condition | Exception | Notes |
|-----------|-----------|-------|
| Template .pptx missing or corrupt | `ValueError` | via `_open_presentation()` from `breakdown.py` |
| Layout index from manifest beyond template's layout count | `ManipulationError` | manifest-vs-template mismatch |
| Placeholder idx from manifest not found in the slide | `ManipulationError` | manifest-vs-template mismatch |
| `prs.save()` raises `OSError` | `ManipulationError` | temp file cleaned up before raise |
| `Path.rename()` raises `OSError` | `ManipulationError` | temp file cleaned up before raise |

### Degrade cases (warn, collect, continue)

| Condition | Action |
|-----------|--------|
| `text` field value longer than `max_chars` | `logger.warning(...)`, add to issues list |
| `bullets` list longer than `max_items` | `logger.warning(...)`, add to issues list; all bullets rendered, no cap |
| Image path does not exist | `logger.warning(...)`, add to issues list, field skipped |
| `insert_picture()` raises | `logger.warning(...)`, add to issues list, field skipped |
| Optional field absent in content | Silent skip, no issue added |

### No-partial-file discipline

Build the entire `Presentation` in memory first. Only write after all slides succeed.

Save sequence:
1. `prs.save(str(tmp_path))` where `tmp_path = out_path.with_suffix('.pptx.tmp')`
2. `tmp_path.rename(out_path)` (atomic on same filesystem)
3. Return result dict

Any `OSError` at step 1 or 2: `tmp_path.unlink(missing_ok=True)`, raise `ManipulationError`. This guarantees no file at `out_path` if anything in the save-and-rename sequence fails.

---

## 4. CLI command

```
simplicitor render --template <name> --spec <path.json> --out <deck.pptx>
```

**Steps in `_cmd_render()`:**

1. Call `list_templates()`. If `--template` name not in results, raise `ValueError("Template '{name}' not found.")`.
2. Load manifest via `load_manifest(entry["manifest_path"])`.
3. Load `--spec` JSON file:
   - File not found/unreadable → raise `ValueError(f"Spec file not found or not readable: {path}")`
   - Content not valid JSON → raise `ValueError(f"Invalid JSON in spec file: {path}")`
4. Validate content via `validate_content(manifest, raw_json)`. If invalid, print `format_validation_errors()` output to stderr, return 1.
5. Normalize `out_path`: `if not out_path.suffix: out_path = out_path.with_suffix('.pptx')`.
6. Call `render(manifest, parsed_content, out_path, template_dir=entry["path"])`.
7. On success: print `out_path` + any issues. On exception: the wrapping try/except catches `(ValueError, ManipulationError)`, prints `f"Error: {exc}"` to stderr, returns 1. This matches the existing `_cmd_inspect` / `_cmd_import` pattern exactly.

---

## 5. Test coverage

One fixture per failure mode. All tests live in `tests/templates_engine/test_render_pptx.py`.

| Test | What it verifies |
|------|-----------------|
| `test_render_valid_content_produces_correct_slides` | Text + bullets rendered; slide count matches content |
| `test_render_image_field_does_not_raise` | Image kind with a real small PNG; no exception; placeholder captured |
| `test_render_missing_optional_field_skipped` | Optional field absent; no issue, no crash |
| `test_render_text_overflow_warns_not_truncates` | Text longer than `max_chars`; warning in issues, full text rendered |
| `test_render_bullets_overflow_warns_not_caps` | More bullets than `max_items`; all bullets present in output, warning in issues |
| `test_render_missing_image_warns_not_raises` | Image path doesn't exist; warning collected, no crash, no exception |
| `test_render_bad_layout_index_raises_manipulation_error` | Layout index beyond template's layout count; `ManipulationError` before save |
| `test_render_bad_placeholder_idx_raises_manipulation_error` | Placeholder idx not in slide; `ManipulationError` |
| `test_render_save_failure_leaves_no_partial_file` | Patch `prs.save()` to raise `OSError`; no file at `out_path`, `ManipulationError` raised |
| `test_render_rename_failure_leaves_no_temp_file` | Patch `Path.rename()` to raise; no temp file left, `ManipulationError` raised |
| `test_render_template_missing_pptx_fails_cleanly` | Template entry exists but `.pptx` deleted; `ValueError` raised, no partial output |

---

## 6. Decisions recorded

- `render()` trusts that `content` is already validated. No re-validation inside render. Documented in docstring.
- `manifest.template_file` is resolved relative to `template_dir` (explicit 4th arg). `Manifest` model unchanged.
- `bullets` overflow: warn-only, no cap. Consistent with `text` overflow behavior. Silently capping content was ruled out.
- `--spec` accepts a JSON file path only. No inline JSON. File-not-found and invalid-JSON are distinct errors.
- CLI error surface: existing `except (ValueError, ManipulationError): print(f"Error: {exc}", stderr)` pattern, no new pattern introduced.
