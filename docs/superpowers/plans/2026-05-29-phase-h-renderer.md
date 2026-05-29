# Phase H: PPTX Renderer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement `render_pptx.py` so that validated content JSON is rendered into a `.pptx` deck using a chosen template, and wire it to a `render` CLI subcommand.

**Architecture:** A single public `render(manifest, content, out_path, template_dir)` function builds all slides in memory, then saves via a temp-file-and-rename sequence to guarantee no partial file at `out_path` on any failure. Degrade cases (overflow, missing images) are collected as warning strings and returned; genuine faults (bad layout index, bad placeholder idx, save failure) raise `ManipulationError` immediately.

**Tech Stack:** `python-pptx`, `pydantic`, `pytest`, existing `ManipulationError` / `ValueError` conventions per `NOTES.md`.

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `simplicitor/templates_engine/render_pptx.py` | Replace stub | `_open_template`, `_get_placeholder`, `_render_slide`, `render` |
| `simplicitor/cli.py` | Modify | Add `_cmd_render` and `render` subparser |
| `tests/templates_engine/fixtures/render_manifest.yaml` | Create | Manifest fixture with text/bullets/image slide types at real placeholder indices |
| `tests/templates_engine/conftest.py` | Modify | Add `tmp_template` and `tiny_png` fixtures |
| `tests/templates_engine/test_render_pptx.py` | Create | All Phase H tests |

---

## Task 1: Create test fixtures

**Files:**
- Create: `tests/templates_engine/fixtures/render_manifest.yaml`
- Modify: `tests/templates_engine/conftest.py`

- [ ] **Step 1: Write render_manifest.yaml**

Create `tests/templates_engine/fixtures/render_manifest.yaml`:

```yaml
name: render_test
type: pptx
template_file: template.pptx
description: Manifest for render_pptx tests
slide_types:
  title_slide:
    layout_index: 0
    fields:
      - name: title
        placeholder_idx: 0
        kind: text
        required: true
        max_chars: 20
      - name: subtitle
        placeholder_idx: 1
        kind: text
        required: false
  content_slide:
    layout_index: 1
    fields:
      - name: heading
        placeholder_idx: 0
        kind: text
        required: true
      - name: body
        placeholder_idx: 1
        kind: bullets
        required: false
        max_items: 2
  image_slide:
    layout_index: 1
    fields:
      - name: heading
        placeholder_idx: 0
        kind: text
        required: true
      - name: img
        placeholder_idx: 1
        kind: image
        required: false
```

*Note: `layout_index` 0 and 1 are "Title Slide" and "Title and Content" in the default python-pptx template. Both have real placeholders at idx=0 and idx=1. `image_slide` re-uses layout 1 with `kind: image` at idx=1 — the placeholder is a body type, but `_get_placeholder` only looks up by idx; `insert_picture` is tested via mocking.*

- [ ] **Step 2: Add fixtures to conftest.py**

`tests/templates_engine/conftest.py` currently only has `auto_show_widgets`. Add `tmp_template` and `tiny_png`:

```python
# tests/templates_engine/conftest.py
# Override the root conftest's autouse Qt fixture — templates_engine tests have no UI.
from pathlib import Path

import pytest
from pptx import Presentation


@pytest.fixture(autouse=True)
def auto_show_widgets():
    yield


@pytest.fixture
def tmp_template(tmp_path):
    """Temp dir with a default Presentation saved as template.pptx and render_manifest.yaml."""
    Presentation().save(str(tmp_path / "template.pptx"))
    src = Path(__file__).parent / "fixtures" / "render_manifest.yaml"
    (tmp_path / "manifest.yaml").write_bytes(src.read_bytes())
    return tmp_path


@pytest.fixture
def tiny_png(tmp_path):
    """A file at tmp_path/test_image.png. Content is not a valid image; tests mock insert_picture."""
    path = tmp_path / "test_image.png"
    path.write_bytes(b"PNG")
    return path
```

- [ ] **Step 3: Verify the fixtures load without error**

```
C:\Python314\python.exe -m pytest tests/templates_engine/ -v --collect-only 2>&1 | Select-String "render"
```

Expected: no collection errors. (No test_render_pptx.py yet, so nothing renders.)

---

## Task 2: Implement render_pptx.py

**Files:**
- Modify: `simplicitor/templates_engine/render_pptx.py`

- [ ] **Step 1: Write the full implementation**

Replace the stub `simplicitor/templates_engine/render_pptx.py` with:

```python
# templates_engine/render_pptx.py
# Phase H: PPTX renderer.
import logging
import zipfile
from pathlib import Path

from templates_engine.manifest import Manifest, SlideTypeDef

logger = logging.getLogger(__name__)


def _open_template(path: Path):
    """Open a .pptx template, raising ValueError if missing, wrong type, or corrupt."""
    from pptx import Presentation
    from pptx.exceptions import InvalidXmlError, PackageNotFoundError

    if not path.exists():
        raise ValueError(f"Template file not found: '{path}'.")
    try:
        return Presentation(str(path))
    except (PackageNotFoundError, InvalidXmlError, KeyError, zipfile.BadZipFile) as exc:
        raise ValueError(
            f"Could not open template '{path.name}' as a PowerPoint file."
        ) from exc
    except Exception as exc:
        raise ValueError(
            f"Could not open template '{path.name}' as a PowerPoint file "
            f"({type(exc).__name__})."
        ) from exc


def _get_placeholder(slide, idx: int, field_name: str, slide_idx: int):
    """Return the slide placeholder at *idx*, raising ManipulationError if absent."""
    from app.services.file_manipulator import ManipulationError

    try:
        return slide.placeholders[idx]
    except KeyError:
        raise ManipulationError(
            f"Slide {slide_idx}: placeholder idx {idx} (field '{field_name}') "
            f"not found in template. Manifest and template are out of sync."
        )


def _render_slide(
    slide,
    slide_def: SlideTypeDef,
    fields: dict,
    slide_idx: int,
) -> list[str]:
    """Populate slide placeholders from fields. Returns degrade warning strings."""
    issues: list[str] = []

    for field in slide_def.fields:
        idx = field.placeholder_idx
        name = field.name
        value = fields.get(name)

        if value is None:
            continue  # optional field absent — skip silently
        if field.kind == "bullets" and not value:
            continue  # empty bullet list — skip silently

        ph = _get_placeholder(slide, idx, name, slide_idx)

        if field.kind == "text":
            ph.text = value
            if field.max_chars is not None and len(value) > field.max_chars:
                msg = (
                    f"Slide {slide_idx}, field '{name}': text length {len(value)} "
                    f"exceeds max_chars {field.max_chars}."
                )
                logger.warning(msg)
                issues.append(msg)

        elif field.kind == "bullets":
            tf = ph.text_frame
            tf.clear()
            for i, item in enumerate(value):
                if i == 0:
                    tf.paragraphs[0].text = item
                else:
                    tf.add_paragraph().text = item
            if field.max_items is not None and len(value) > field.max_items:
                msg = (
                    f"Slide {slide_idx}, field '{name}': {len(value)} bullets "
                    f"exceeds max_items {field.max_items}."
                )
                logger.warning(msg)
                issues.append(msg)

        elif field.kind == "image":
            img_path = Path(value)
            if not img_path.exists():
                msg = (
                    f"Slide {slide_idx}, field '{name}': image path '{img_path}' "
                    f"not found, field skipped."
                )
                logger.warning(msg)
                issues.append(msg)
                continue
            try:
                _ph = ph.insert_picture(str(img_path))  # noqa: F841 — capture; original ref invalidated
            except Exception as exc:
                msg = (
                    f"Slide {slide_idx}, field '{name}': could not insert image "
                    f"({type(exc).__name__}), field skipped."
                )
                logger.warning(msg)
                issues.append(msg)

    return issues


def render(
    manifest: Manifest,
    content: dict,
    out_path: str | Path,
    template_dir: str | Path,
) -> dict:
    """Render validated content into a PPTX deck using the named template.

    Content must already be validated via validate_content(). render() trusts
    the caller and does not re-validate.

    Args:
        manifest: Validated Manifest from load_manifest().
        content: Validated content dict {"slides": [{"type": str, "fields": dict}]}.
            Must be the parsed output of validate_content() — not raw JSON.
        out_path: Destination path. If suffix is empty, .pptx is appended silently.
        template_dir: Directory containing manifest.template_file.

    Returns:
        {"path": Path, "issues": list[str]} — path to the written file and
        any degrade warnings collected during rendering. Empty issues list
        means a clean render.

    Raises:
        ValueError: If the template .pptx is missing or corrupt.
        ManipulationError: If a layout_index or placeholder_idx from the
            manifest is absent in the template (manifest/template mismatch),
            or if the output file cannot be written. No partial file is left
            at out_path on failure.
    """
    from app.services.file_manipulator import ManipulationError

    out_path = Path(out_path)
    if not out_path.suffix:
        out_path = out_path.with_suffix(".pptx")
    template_dir = Path(template_dir)

    template_path = template_dir / manifest.template_file
    prs = _open_template(template_path)  # raises ValueError if missing/corrupt

    all_issues: list[str] = []

    for slide_idx, slide_data in enumerate(content["slides"]):
        slide_type = slide_data["type"]
        slide_def = manifest.slide_types[slide_type]
        layout_index = slide_def.layout_index

        if layout_index >= len(prs.slide_layouts):
            raise ManipulationError(
                f"Slide {slide_idx}: layout_index {layout_index} not found in template "
                f"(template has {len(prs.slide_layouts)} layout(s)). "
                f"Manifest and template are out of sync."
            )

        layout = prs.slide_layouts[layout_index]
        slide = prs.slides.add_slide(layout)

        slide_issues = _render_slide(slide, slide_def, slide_data["fields"], slide_idx)
        all_issues.extend(slide_issues)

    # Save via temp file → atomic rename: guarantees no partial file at out_path on failure.
    tmp_file = out_path.with_suffix(".pptx.tmp")
    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        prs.save(str(tmp_file))
        tmp_file.rename(out_path)
    except OSError as exc:
        try:
            tmp_file.unlink(missing_ok=True)
        except OSError:
            logger.warning("Could not clean up temp file '%s'.", tmp_file.name)
        logger.error("Failed to write rendered deck to '%s': %s", out_path, exc)
        raise ManipulationError(
            f"Could not write rendered deck to '{out_path.name}': {exc}"
        ) from exc

    logger.debug(
        "Rendered %d slide(s) to '%s' with %d issue(s).",
        len(content["slides"]),
        out_path.name,
        len(all_issues),
    )
    return {"path": out_path, "issues": all_issues}
```

- [ ] **Step 2: Verify the module imports cleanly**

```
C:\Python314\python.exe -c "from templates_engine.render_pptx import render; print('ok')"
```

Run from `C:\Repos\simplicitor`. Expected: `ok`

---

## Task 3: Happy path tests

**Files:**
- Create: `tests/templates_engine/test_render_pptx.py`

- [ ] **Step 1: Write happy-path tests**

Create `tests/templates_engine/test_render_pptx.py`:

```python
# tests/templates_engine/test_render_pptx.py
# Phase H: Tests for the PPTX renderer.
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from pptx import Presentation

from app.services.file_manipulator import ManipulationError
from templates_engine.manifest import FieldDef, Manifest, SlideTypeDef, load_manifest
from templates_engine.render_pptx import render


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

def test_render_returns_result_dict(tmp_path, tmp_template):
    manifest = load_manifest(tmp_template / "manifest.yaml")
    content = {"slides": [{"type": "title_slide", "fields": {"title": "Hello"}}]}
    result = render(manifest, content, tmp_path / "out.pptx", tmp_template)
    assert isinstance(result, dict)
    assert "path" in result
    assert "issues" in result


def test_render_output_file_exists(tmp_path, tmp_template):
    manifest = load_manifest(tmp_template / "manifest.yaml")
    content = {"slides": [{"type": "title_slide", "fields": {"title": "Hello"}}]}
    result = render(manifest, content, tmp_path / "out.pptx", tmp_template)
    assert result["path"].is_file()


def test_render_slide_count_matches_content(tmp_path, tmp_template):
    manifest = load_manifest(tmp_template / "manifest.yaml")
    content = {
        "slides": [
            {"type": "title_slide", "fields": {"title": "T1"}},
            {"type": "content_slide", "fields": {"heading": "H1", "body": ["A", "B"]}},
        ]
    }
    result = render(manifest, content, tmp_path / "out.pptx", tmp_template)
    prs = Presentation(str(result["path"]))
    assert len(prs.slides) == 2


def test_render_text_field_written_to_slide(tmp_path, tmp_template):
    manifest = load_manifest(tmp_template / "manifest.yaml")
    content = {"slides": [{"type": "title_slide", "fields": {"title": "My Title"}}]}
    result = render(manifest, content, tmp_path / "out.pptx", tmp_template)
    prs = Presentation(str(result["path"]))
    assert prs.slides[0].placeholders[0].text == "My Title"


def test_render_bullets_written_to_slide(tmp_path, tmp_template):
    manifest = load_manifest(tmp_template / "manifest.yaml")
    content = {
        "slides": [{"type": "content_slide", "fields": {"heading": "H", "body": ["X", "Y"]}}]
    }
    result = render(manifest, content, tmp_path / "out.pptx", tmp_template)
    prs = Presentation(str(result["path"]))
    texts = [p.text for p in prs.slides[0].placeholders[1].text_frame.paragraphs if p.text]
    assert "X" in texts
    assert "Y" in texts


def test_render_no_issues_on_clean_content(tmp_path, tmp_template):
    manifest = load_manifest(tmp_template / "manifest.yaml")
    content = {"slides": [{"type": "title_slide", "fields": {"title": "Hi"}}]}
    result = render(manifest, content, tmp_path / "out.pptx", tmp_template)
    assert result["issues"] == []


def test_render_appends_pptx_extension_when_absent(tmp_path, tmp_template):
    manifest = load_manifest(tmp_template / "manifest.yaml")
    content = {"slides": [{"type": "title_slide", "fields": {"title": "Hi"}}]}
    # Pass a path with no extension
    result = render(manifest, content, tmp_path / "out", tmp_template)
    assert result["path"].suffix == ".pptx"
    assert result["path"].is_file()


def test_render_creates_output_directory_if_needed(tmp_path, tmp_template):
    manifest = load_manifest(tmp_template / "manifest.yaml")
    content = {"slides": [{"type": "title_slide", "fields": {"title": "Hi"}}]}
    nested = tmp_path / "sub" / "dir" / "out.pptx"
    result = render(manifest, content, nested, tmp_template)
    assert result["path"].is_file()
```

- [ ] **Step 2: Run happy-path tests**

```
C:\Python314\python.exe -m pytest tests/templates_engine/test_render_pptx.py -v -k "happy or returns or exists or count or written or issues or extension or directory"
```

Run from `C:\Repos`. Expected: all 8 pass.

---

## Task 4: Degrade-case tests (text overflow, bullets overflow, missing optional)

**Files:**
- Modify: `tests/templates_engine/test_render_pptx.py`

- [ ] **Step 1: Add degrade tests**

Append to `tests/templates_engine/test_render_pptx.py`:

```python
# ---------------------------------------------------------------------------
# Degrade cases — warn + collect, never raise
# ---------------------------------------------------------------------------

def test_render_missing_optional_field_skipped(tmp_path, tmp_template):
    manifest = load_manifest(tmp_template / "manifest.yaml")
    # subtitle is optional; body is optional — omit both
    content = {"slides": [{"type": "title_slide", "fields": {"title": "Hi"}}]}
    result = render(manifest, content, tmp_path / "out.pptx", tmp_template)
    assert result["path"].is_file()
    assert result["issues"] == []


def test_render_text_overflow_warns_not_truncates(tmp_path, tmp_template):
    manifest = load_manifest(tmp_template / "manifest.yaml")
    long_title = "X" * 100  # render_manifest has max_chars=20 for title
    content = {"slides": [{"type": "title_slide", "fields": {"title": long_title}}]}

    result = render(manifest, content, tmp_path / "out.pptx", tmp_template)

    assert len(result["issues"]) == 1
    assert "max_chars" in result["issues"][0]
    # Full text must be in the output (no truncation)
    prs = Presentation(str(result["path"]))
    assert prs.slides[0].placeholders[0].text == long_title


def test_render_bullets_overflow_warns_not_caps(tmp_path, tmp_template):
    manifest = load_manifest(tmp_template / "manifest.yaml")
    bullets = ["A", "B", "C", "D"]  # render_manifest has max_items=2
    content = {
        "slides": [{"type": "content_slide", "fields": {"heading": "H", "body": bullets}}]
    }

    result = render(manifest, content, tmp_path / "out.pptx", tmp_template)

    assert len(result["issues"]) == 1
    assert "max_items" in result["issues"][0]
    # All 4 bullets must be present (no cap)
    prs = Presentation(str(result["path"]))
    texts = [p.text for p in prs.slides[0].placeholders[1].text_frame.paragraphs if p.text]
    assert len(texts) == 4


def test_render_multiple_degrade_warnings_collected(tmp_path, tmp_template):
    manifest = load_manifest(tmp_template / "manifest.yaml")
    content = {
        "slides": [
            {"type": "title_slide", "fields": {"title": "X" * 100}},
            {"type": "content_slide", "fields": {"heading": "H", "body": ["A", "B", "C", "D"]}},
        ]
    }
    result = render(manifest, content, tmp_path / "out.pptx", tmp_template)
    assert len(result["issues"]) == 2
```

- [ ] **Step 2: Run degrade tests**

```
C:\Python314\python.exe -m pytest tests/templates_engine/test_render_pptx.py -v -k "optional or overflow or warns or caps or degrade or multiple"
```

Expected: all 4 pass.

---

## Task 5: Image field tests

**Files:**
- Modify: `tests/templates_engine/test_render_pptx.py`

- [ ] **Step 1: Add image tests**

Append to `tests/templates_engine/test_render_pptx.py`:

```python
# ---------------------------------------------------------------------------
# Image field — degrade cases and happy path
# ---------------------------------------------------------------------------

def test_render_missing_image_warns_not_raises(tmp_path, tmp_template):
    """Image path does not exist — warn + skip, no exception."""
    manifest = load_manifest(tmp_template / "manifest.yaml")
    content = {
        "slides": [
            {"type": "image_slide", "fields": {"heading": "Hi", "img": "/nonexistent/image.png"}}
        ]
    }
    result = render(manifest, content, tmp_path / "out.pptx", tmp_template)
    assert result["path"].is_file()
    assert len(result["issues"]) == 1
    assert "not found" in result["issues"][0]


def test_render_image_insert_failure_warns_not_raises(tmp_path, tmp_template, tiny_png):
    """insert_picture raises — warn + skip, no exception, file still written."""
    manifest = load_manifest(tmp_template / "manifest.yaml")
    content = {
        "slides": [{"type": "image_slide", "fields": {"heading": "Hi", "img": str(tiny_png)}}]
    }
    mock_ph = MagicMock()
    mock_ph.insert_picture.side_effect = Exception("not a picture placeholder")

    with patch("templates_engine.render_pptx._get_placeholder", return_value=mock_ph):
        result = render(manifest, content, tmp_path / "out.pptx", tmp_template)

    assert result["path"].is_file()
    assert len(result["issues"]) >= 1
    assert any("insert" in i.lower() or "image" in i.lower() for i in result["issues"])


def test_render_image_field_does_not_raise(tmp_path, tmp_template, tiny_png):
    """insert_picture succeeds — no issues, returned placeholder captured."""
    manifest = load_manifest(tmp_template / "manifest.yaml")
    content = {
        "slides": [{"type": "image_slide", "fields": {"heading": "Hi", "img": str(tiny_png)}}]
    }
    mock_ph = MagicMock()
    mock_ph.insert_picture.return_value = MagicMock()

    with patch("templates_engine.render_pptx._get_placeholder", return_value=mock_ph):
        result = render(manifest, content, tmp_path / "out.pptx", tmp_template)

    assert result["issues"] == []
    mock_ph.insert_picture.assert_called_with(str(tiny_png))
```

- [ ] **Step 2: Run image tests**

```
C:\Python314\python.exe -m pytest tests/templates_engine/test_render_pptx.py -v -k "image"
```

Expected: all 3 pass.

---

## Task 6: Genuine fault tests

**Files:**
- Modify: `tests/templates_engine/test_render_pptx.py`

- [ ] **Step 1: Add genuine fault tests**

Append to `tests/templates_engine/test_render_pptx.py`:

```python
# ---------------------------------------------------------------------------
# Genuine faults — raise ManipulationError or ValueError, no partial file
# ---------------------------------------------------------------------------

def test_render_bad_layout_index_raises_manipulation_error(tmp_path, tmp_template):
    """layout_index beyond template's layout count → ManipulationError before save."""
    bad_manifest = Manifest(
        name="bad",
        type="pptx",
        template_file="template.pptx",
        description="test",
        slide_types={
            "bad": SlideTypeDef(layout_index=99, fields=[])
        },
    )
    content = {"slides": [{"type": "bad", "fields": {}}]}

    with pytest.raises(ManipulationError, match=r"layout_index 99"):
        render(bad_manifest, content, tmp_path / "out.pptx", tmp_template)

    assert not (tmp_path / "out.pptx").exists()


def test_render_bad_placeholder_idx_raises_manipulation_error(tmp_path, tmp_template):
    """Placeholder idx absent in slide → ManipulationError before save."""
    bad_manifest = Manifest(
        name="bad",
        type="pptx",
        template_file="template.pptx",
        description="test",
        slide_types={
            "bad": SlideTypeDef(
                layout_index=0,
                fields=[FieldDef(name="title", placeholder_idx=99, kind="text", required=True)],
            )
        },
    )
    content = {"slides": [{"type": "bad", "fields": {"title": "Hi"}}]}

    with pytest.raises(ManipulationError, match=r"placeholder idx 99"):
        render(bad_manifest, content, tmp_path / "out.pptx", tmp_template)

    assert not (tmp_path / "out.pptx").exists()


def test_render_template_missing_pptx_fails_cleanly(tmp_path, tmp_template):
    """Template .pptx deleted after import → ValueError, no partial output."""
    (tmp_template / "template.pptx").unlink()
    manifest = load_manifest(tmp_template / "manifest.yaml")
    content = {"slides": [{"type": "title_slide", "fields": {"title": "Hi"}}]}

    with pytest.raises(ValueError, match=r"Template file not found"):
        render(manifest, content, tmp_path / "out.pptx", tmp_template)

    assert not (tmp_path / "out.pptx").exists()


def test_render_save_failure_leaves_no_partial_file(tmp_path, tmp_template):
    """prs.save() raises OSError → ManipulationError, no file at out_path or tmp_file."""
    manifest = load_manifest(tmp_template / "manifest.yaml")
    content = {"slides": [{"type": "title_slide", "fields": {"title": "Hi"}}]}
    out_path = tmp_path / "out.pptx"

    mock_prs = MagicMock()
    mock_prs.slide_layouts = [MagicMock()] * 5
    mock_prs.slides.add_slide.return_value = MagicMock()
    mock_prs.save.side_effect = OSError("disk full")

    with patch("templates_engine.render_pptx._open_template", return_value=mock_prs):
        with pytest.raises(ManipulationError, match=r"disk full"):
            render(manifest, content, out_path, tmp_template)

    assert not out_path.exists()
    assert not out_path.with_suffix(".pptx.tmp").exists()


def test_render_rename_failure_leaves_no_temp_file(tmp_path, tmp_template):
    """Path.rename() raises OSError → ManipulationError, tmp_file cleaned up."""
    manifest = load_manifest(tmp_template / "manifest.yaml")
    content = {"slides": [{"type": "title_slide", "fields": {"title": "Hi"}}]}
    out_path = tmp_path / "out.pptx"

    with patch("pathlib.Path.rename", side_effect=OSError("rename failed")):
        with pytest.raises(ManipulationError, match=r"rename failed"):
            render(manifest, content, out_path, tmp_template)

    assert not out_path.exists()
    assert not out_path.with_suffix(".pptx.tmp").exists()
```

- [ ] **Step 2: Run fault tests**

```
C:\Python314\python.exe -m pytest tests/templates_engine/test_render_pptx.py -v -k "bad or missing or save or rename or fault or clean"
```

Expected: all 5 pass.

- [ ] **Step 3: Run the full test file**

```
C:\Python314\python.exe -m pytest tests/templates_engine/test_render_pptx.py -v
```

Expected: all tests pass. Note count for the commit message.

---

## Task 7: CLI render command

**Files:**
- Modify: `simplicitor/cli.py`

- [ ] **Step 1: Add `_cmd_render` and wire it into the parser**

`simplicitor/cli.py` currently ends with `_build_parser` and `main`. Make the following additions:

**Add `_cmd_render` after `_cmd_import`** (before `_build_parser`):

```python
def _cmd_render(args: argparse.Namespace) -> int:
    import json
    from templates_engine.config import list_templates
    from templates_engine.manifest import load_manifest
    from templates_engine.validation import format_validation_errors, validate_content
    from templates_engine.render_pptx import render
    from app.services.file_manipulator import ManipulationError

    try:
        templates = list_templates()
        match = next((t for t in templates if t["name"] == args.template), None)
        if match is None:
            raise ValueError(f"Template '{args.template}' not found.")

        manifest = load_manifest(match["manifest_path"])

        spec_path = Path(args.spec)
        if not spec_path.exists():
            raise ValueError(f"Spec file not found or not readable: {spec_path}")
        try:
            raw_json = json.loads(spec_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            raise ValueError(f"Invalid JSON in spec file: {spec_path}") from exc

        ok, result_or_errors = validate_content(manifest, raw_json)
        if not ok:
            print(format_validation_errors(result_or_errors), file=sys.stderr)
            return 1

        out_path = Path(args.out)
        if not out_path.suffix:
            out_path = out_path.with_suffix(".pptx")

        result = render(manifest, result_or_errors, out_path, template_dir=match["path"])

        print(f"Rendered: {result['path']}")
        if result["issues"]:
            print(f"\n{len(result['issues'])} warning(s):")
            for issue in result["issues"]:
                print(f"  - {issue}")
        return 0

    except (ValueError, ManipulationError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
```

**In `_build_parser`, add after the `import_p` block:**

```python
    render_p = sub.add_parser("render", help="Render a content spec using a template.")
    render_p.add_argument("--template", required=True, help="Template name.")
    render_p.add_argument("--spec", required=True, help="Path to content JSON file.")
    render_p.add_argument("--out", required=True, help="Output .pptx path.")
```

**In `main`, add after the `import` command block:**

```python
    if args.command == "render":
        return _cmd_render(args)
```

- [ ] **Step 2: Verify the CLI renders help without error**

```
C:\Python314\python.exe simplicitor/cli.py render --help
```

Run from `C:\Repos\simplicitor`. Expected output includes `--template`, `--spec`, `--out`.

- [ ] **Step 3: Smoke-test the render command against a built-in template**

The built-in template directory (`simplicitor/templates_engine/builtin/`) is empty until Phase L. If at least one user template exists from a previous `simplicitor import` run, test it. Otherwise, write a minimal spec JSON and test with a user-imported template:

Write `C:\Repos\simplicitor\test_spec.json`:
```json
{
  "slides": [
    {"type": "title_slide", "fields": {"title": "Hello Phase H"}}
  ]
}
```

Then (replace `<template_name>` with a name from `simplicitor list-templates`):
```
C:\Python314\python.exe simplicitor/cli.py render --template <template_name> --spec test_spec.json --out C:\Temp\phase_h_test.pptx
```

If no templates exist yet, this step is deferred to Phase L. Confirm the CLI help works and move on.

- [ ] **Step 4: Run the full templates_engine test suite to check for regressions**

```
C:\Python314\python.exe -m pytest tests/templates_engine/ -v
```

Run from `C:\Repos`. Expected: all 139 existing tests plus the new render tests pass.

---

## Task 8: Commit

- [ ] **Step 1: Stage and commit**

```
git add simplicitor/templates_engine/render_pptx.py simplicitor/cli.py tests/templates_engine/test_render_pptx.py tests/templates_engine/conftest.py tests/templates_engine/fixtures/render_manifest.yaml
git commit -m "feat: pptx renderer with degrade/fail error policy"
```

Run from `C:\Repos`.

- [ ] **Step 2: Confirm clean state**

```
git status
git log --oneline -3
```

Expected: working tree clean, new commit at HEAD.

---

## Self-review checklist

- [x] **Spec coverage:** All Phase H requirements covered:
  - `render()` ✓ (Task 2)
  - Degrade policy (text/bullets overflow, missing/failing image) ✓ (Tasks 4, 5)
  - Genuine faults (bad layout, bad placeholder, save failure) ✓ (Task 6)
  - No-partial-file (temp+rename) ✓ (Task 2, tested in Task 6)
  - CLI `simplicitor render` ✓ (Task 7)
  - All 11 tests from spec ✓ (Tasks 3–6)
- [x] **No placeholders:** All code blocks are complete. No TBD sections.
- [x] **Type consistency:** `render()` returns `dict`, `_render_slide()` returns `list[str]`, `_get_placeholder()` returns the placeholder or raises `ManipulationError`. Names consistent across all tasks.
- [x] **`tmp_template` fixture:** Returns `tmp_path` directly — tests that request both `tmp_path` and `tmp_template` receive the same directory, which is expected (template.pptx and manifest.yaml live at the root of that dir).
- [x] **`tiny_png`:** File exists (path-existence check passes) but content is not a valid PNG (tests that reach `insert_picture` always mock it, so validity is irrelevant).
- [x] **`test_render_template_missing_pptx_fails_cleanly`:** Deletes `tmp_template / "template.pptx"` — only valid if `tmp_template` is a distinct fixture instance per test (it is, since `tmp_path` is function-scoped).
