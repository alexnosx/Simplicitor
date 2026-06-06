# Templates Folder Setting with Always-Present Defaults

**Date:** 2026-06-06
**Status:** Approved

## Problem

Uploaded templates land in `%APPDATA%\Simplicitor\templates`, invisible to the user and
disconnected from the four directories Settings manages (Generated, Uploads, Backups,
Logs). There is no user-visible, configurable Templates folder. Separately, the two
curated built-in templates that ship in `templates_engine/builtin/` never appear in the
running app, so the user worked around it by uploading a generic deck twice as raw drafts.

## Goal

A visible, configurable "Templates" folder in Settings. The picker lists it, uploads save
into it, and the two curated defaults (`business_pitch`, `technical_overview`) are always
present in it.

## Behavior

1. Settings gains a "Templates" folder, default `Documents\Simplicitor\Templates`,
   alongside the existing four. Configurable and reset-to-defaults like the others.
2. On app startup the folder is ensured to exist and to contain the two curated defaults.
   For each of `business_pitch` and `technical_overview`, if its folder is missing from the
   Templates folder, it is copied from the bundled `templates_engine/builtin/<name>`. A
   default that already exists is left untouched (user edits are not clobbered); a deleted
   default is restored on the next launch ("always present").
3. The "From template..." picker lists the Templates folder only: the two seeded defaults
   plus any user uploads. Defaults are tagged `default`, uploads `user`.
4. Uploading a .pptx imports it into the Templates folder.
5. The separate read-only built-in root is no longer merged into the GUI listing; the
   defaults now physically live in the Templates folder, so merging would double-list them.

## Components

### Settings (`app/config/settings.py`)
Add `templates_dir` to `_default_data` (default `Documents\Simplicitor\Templates`) and a
`templates_dir` property. Reset-to-defaults and the load-time defaults merge pick it up
automatically, so existing `settings.json` files gain it.

### config (`templates_engine/config.py`)
- `DEFAULT_TEMPLATE_NAMES = ("business_pitch", "technical_overview")`.
- `ensure_default_templates(templates_root)`: create the root if absent; for each default
  name, if it is not already a valid template dir under the root, copy it from
  `get_builtin_root()/<name>`. If a source default is missing (e.g. not bundled), log a
  warning and skip rather than fail. Idempotent.
- `list_library(templates_root)`: list valid template dirs in the single root, tagging
  each `default` (name in `DEFAULT_TEMPLATE_NAMES`) or `user`. Same dict shape as
  `list_templates`.
- `list_templates` and `import_template` are unchanged (CLI still uses the two-root model
  and AppData default); the GUI passes its Templates folder explicitly.

### SettingsDialog (`app/widgets/settings_dialog.py`)
Add a "Templates" row (label + path field + browse button) following the existing rows.
Save persists `templates_dir`; Reset to Defaults restores it.

### TemplateDialog (`app/widgets/template_dialog.py`)
Add a `templates_dir` constructor argument. `_refresh_templates` lists via
`config.list_library(Path(templates_dir))`; `_do_import` imports via
`config.import_template(path, user_root=Path(templates_dir))`.

### MainWindow (`app/main_window.py`)
At startup, call `config.ensure_default_templates(Path(self._settings.templates_dir))`.
Construct the picker as `TemplateDialog(self._settings.templates_dir, parent=self)`.

## Data flow (open picker)

startup -> `ensure_default_templates(templates_dir)` seeds/restores defaults ->
user clicks "From template..." -> `TemplateDialog(templates_dir)` ->
`list_library(templates_dir)` shows defaults + uploads -> pick or upload (import into
templates_dir) -> Next emits the chosen template (unchanged picker behavior).

## Error handling

- A missing or unwritable Templates folder surfaces through the existing conventions:
  `import_template` already raises `ManipulationError` on write failure; `list_library` on
  an absent root returns an empty list. Seeding logs and skips a missing source default.
- No new exception types.

## Testing (TDD)

- Settings: `templates_dir` default value; property; included in reset-to-defaults; an old
  `settings.json` without the key still exposes the default after load.
- config: `ensure_default_templates` seeds both defaults into an empty root; restores a
  deleted default; leaves an existing (modified) default untouched; is idempotent;
  tolerates a missing source default. `list_library` tags defaults vs user and skips
  invalid dirs.
- SettingsDialog: row shows the current value; save persists it; reset restores it.
- TemplateDialog: lists from the passed Templates folder; upload imports into it.

## Out of scope

- Migrating the AppData drafts or `development_partner_presentation` (dropped by decision).
- CLI relocation (the CLI keeps its AppData/two-root default).
- The Nuitka build change to bundle `templates_engine/builtin/` as data files. The
  built-ins not appearing in the packaged app points to this gap; seeding reads from the
  same bundled source, so the build must include it. Flagged as a separate follow-up.
