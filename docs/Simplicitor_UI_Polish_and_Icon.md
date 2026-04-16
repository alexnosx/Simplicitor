# Simplicitor - UI Polish + Icon Integration

## Overview

This set of changes polishes the existing UI to match the design spec in `CLAUDE.md` more closely, and adds a proper application icon. No new features, no scope changes. All changes are visual/structural refinements to the existing Phase 5 build.

Work through the sections in order. Each section is independently testable.

---

## Section 1: Application Icon

### Files provided

A pre-built icon package is in `assets/icons/` at the repo root:

```
assets/
  icons/
    simplicitor.ico         # Multi-resolution Windows icon (16, 24, 32, 48, 64, 128, 256)
    simplicitor_16.png
    simplicitor_24.png
    simplicitor_32.png
    simplicitor_48.png
    simplicitor_64.png
    simplicitor_128.png
    simplicitor_256.png
    simplicitor_512.png     # For app branding / about dialog
```

If the `assets/icons/` folder does not exist in the repo, create it and copy the files from the download Alex will provide.

### Tasks

1. **Set the window icon in `app/main_window.py`:**
   - Import `QIcon` from `PySide6.QtGui` and `Path` from `pathlib`.
   - In `MainWindow.__init__`, after `setWindowTitle(...)`, resolve the path to `simplicitor.ico` relative to the application root (use a helper that works both in source and in a Nuitka-packaged build).
   - Call `self.setWindowIcon(QIcon(str(icon_path)))`.

2. **Set the application-level icon in `main.py`:**
   - After creating `QApplication(sys.argv)`, call `app.setWindowIcon(QIcon(str(icon_path)))` with the same icon. This ensures the taskbar icon is correct even on modal dialogs.

3. **Create a resource path helper in `app/utils/file_utils.py`:**

```python
import sys
from pathlib import Path

def resource_path(relative: str) -> Path:
    """Resolve a path to a bundled resource that works both in development
    and inside a Nuitka-packaged executable."""
    if getattr(sys, "frozen", False):
        # Nuitka onefile sets this; fall back to the exe directory
        base = Path(sys.executable).parent
    else:
        # In development, the repo root is two levels up from this file:
        # app/utils/file_utils.py -> app/utils -> app -> <repo>
        base = Path(__file__).resolve().parents[2]
    return base / relative
```

   Use `resource_path("assets/icons/simplicitor.ico")` everywhere the icon is loaded.

4. **Update the Nuitka build command** (in whatever build script or README you have):
   - Add `--windows-icon-from-ico=assets/icons/simplicitor.ico`
   - Add `--include-data-dir=assets=assets` so the icons are available at runtime

### Verification
- Run `python main.py`: window title bar shows the blue S icon instead of the generic Qt icon.
- Taskbar shows the blue S icon.
- Build with Nuitka: the .exe file itself shows the icon in File Explorer.

---

## Section 2: Panel Visual Separation

**Problem:** Left and right panels read as one flat surface because they share the same background. The two-panel concept needs visual reinforcement.

### Tasks

1. In `app/main_window.py`, set the central widget background to `#FAFAFA` (primary background from `defaults.py`).

2. Wrap each panel (create_panel and edit_panel) in a styled container:
   - Panel background: `#F5F5F5`
   - Border: `1px solid #E5E7EB`
   - Border radius: `4px`
   - Internal padding: `16px` on all sides

3. Add a small gap between the two panels: `12px` horizontal spacing in the splitter/layout.

4. In `create_panel.py` and `edit_panel.py`, ensure the root `QWidget` or `QFrame` uses the styled container above. Use `setStyleSheet` with a specific object name selector to avoid cascading to child widgets:

```python
self.setObjectName("panelContainer")
self.setStyleSheet("""
    #panelContainer {
        background-color: #F5F5F5;
        border: 1px solid #E5E7EB;
        border-radius: 4px;
    }
""")
```

### Verification
- Panels are visually distinct from the window background.
- There is a visible gap between the two panels.
- Child widgets inside the panels are not affected by the panel's border styling.

---

## Section 3: Input Field Styling

**Problem:** The "Save to" field, "Uploaded files" list, and prompt text areas blend into the panel background. They need more presence.

### Tasks

Apply consistent styling to all input/display widgets across both panels. Add this to a shared stylesheet in `app/main_window.py` (applied at the app level so both panels inherit):

```python
INPUT_STYLES = """
QLineEdit, QPlainTextEdit, QListWidget, QComboBox {
    background-color: #FFFFFF;
    border: 1px solid #E5E7EB;
    border-radius: 4px;
    padding: 6px 8px;
    font-family: 'Segoe UI';
    font-size: 13px;
    color: #1E1E1E;
}

QLineEdit:focus, QPlainTextEdit:focus, QComboBox:focus {
    border: 1px solid #2563EB;
    outline: none;
}

QLineEdit:disabled, QPlainTextEdit:disabled, QComboBox:disabled {
    background-color: #F9FAFB;
    color: #9CA3AF;
}

QListWidget::item {
    padding: 6px 8px;
    border-radius: 2px;
}

QListWidget::item:selected {
    background-color: #2563EB;
    color: #FFFFFF;
}

QListWidget::item:hover:!selected {
    background-color: #EFF6FF;
}
"""
```

### Verification
- All input fields have a subtle border and white background.
- Focus state shows a blue border.
- Selected file in the list has the blue accent background.
- Disabled inputs are visually distinct (lighter background, muted text).

---

## Section 4: Button Styling

**Problem:** Buttons look flat and the disabled state looks dead. No hover feedback.

### Tasks

1. **Primary buttons (Generate, Save):** Create a reusable style in `app/widgets/` or apply it directly:

```python
PRIMARY_BUTTON_STYLE = """
QPushButton {
    background-color: #2563EB;
    color: #FFFFFF;
    border: none;
    border-radius: 4px;
    padding: 10px 16px;
    font-family: 'Segoe UI';
    font-size: 14px;
    font-weight: 600;
}

QPushButton:hover {
    background-color: #1D4ED8;
}

QPushButton:pressed {
    background-color: #1E40AF;
}

QPushButton:disabled {
    background-color: #E5E7EB;
    color: #9CA3AF;
}
"""
```

2. **Secondary buttons (Browse, Open file):** Use a lighter outlined style:

```python
SECONDARY_BUTTON_STYLE = """
QPushButton {
    background-color: #FFFFFF;
    color: #1E1E1E;
    border: 1px solid #E5E7EB;
    border-radius: 4px;
    padding: 8px 14px;
    font-family: 'Segoe UI';
    font-size: 13px;
    font-weight: 500;
}

QPushButton:hover {
    background-color: #F5F5F5;
    border-color: #9CA3AF;
}

QPushButton:pressed {
    background-color: #E5E7EB;
}

QPushButton:disabled {
    color: #9CA3AF;
    border-color: #E5E7EB;
}
"""
```

3. Apply `PRIMARY_BUTTON_STYLE` to the Generate button in `create_panel.py` and the Save button in `edit_panel.py`.

4. Apply `SECONDARY_BUTTON_STYLE` to the Browse button, Open file button, and any other secondary action buttons.

### Verification
- Enabled Generate/Save buttons are bold blue. Hover turns slightly darker. Press turns even darker.
- Disabled buttons are light gray (#E5E7EB) with muted text.
- Secondary buttons look clearly secondary but still have hover states.

---

## Section 5: Drop Zone Polish

**Problem:** The drop zone border is too subtle. Non-tech users need a more inviting visual target.

### Tasks

In `app/widgets/drop_zone.py`:

1. Set the drop zone styling:
```python
DROP_ZONE_IDLE = """
QLabel {
    background-color: #FFFFFF;
    border: 2px dashed #9CA3AF;
    border-radius: 6px;
    padding: 24px;
    color: #1E1E1E;
    font-family: 'Segoe UI';
    font-size: 14px;
}
"""

DROP_ZONE_HOVER = """
QLabel {
    background-color: #EFF6FF;
    border: 2px dashed #2563EB;
    border-radius: 6px;
    padding: 24px;
    color: #1E40AF;
    font-family: 'Segoe UI';
    font-size: 14px;
    font-weight: 600;
}
"""
```

2. Apply `DROP_ZONE_IDLE` by default, swap to `DROP_ZONE_HOVER` on drag-enter, swap back on drag-leave.

3. Update the drop zone text to use richer wording with the key action semibold:
   - "**Drop a file here** or click to browse"
   - Make this a rich text QLabel (`setTextFormat(Qt.RichText)`) so the HTML bolding works.

4. Ensure the drop zone has a minimum height of 80px and stretches to fill available width.

### Verification
- Drop zone is visibly defined with a 2px dashed border.
- Dragging a file over the zone changes it to a blue-tinted hover state.
- The "Drop a file here" text is bold; "or click to browse" is regular weight.

---

## Section 6: Success Message Refactor

**Problem:** After generation/save, the full file path is dumped as primary text, which is unreadable for non-tech users. The PRD requires a clean human-readable message with the path as secondary info.

### Tasks

1. Replace the current success label with a two-line layout:
   - **Line 1 (primary):** A short status phrase in `#16A34A` (success green), semibold, 14px.
     - Generate: "File created successfully"
     - Manipulate: "File saved. Backup created."
   - **Line 2 (secondary):** The file path in `#6B7280` (muted gray), regular weight, 12px. Truncate from the middle if the path is too long to fit on one line, using an ellipsis. Full path still shown on hover via a tooltip.

2. Keep the dismiss (X) button aligned to the right.

3. The "Open file" button remains below the success block.

4. For manipulation, show BOTH paths stacked in the secondary line:
   - `Saved: C:\...\Uploads\filename.docx`
   - `Backup: C:\...\Backups\filename_backup.docx`
   Both in the muted secondary style.

5. Helper for path truncation in `app/utils/file_utils.py`:

```python
def truncate_path(path: str, max_chars: int = 60) -> str:
    """Shorten a path for display, keeping the start and end visible."""
    if len(path) <= max_chars:
        return path
    keep = (max_chars - 3) // 2
    return f"{path[:keep]}...{path[-keep:]}"
```

### Verification
- After generation: green "File created successfully" with the truncated path below.
- After manipulation: green "File saved. Backup created." with both paths shown below.
- Hovering on the truncated path shows the full path in a tooltip.

---

## Section 7: Header Polish

**Problem:** The "Simplicitor" title and status row are functional but lack brand presence.

### Tasks

In `app/main_window.py` top bar / status bar area:

1. Increase the "Simplicitor" title weight: semibold (600), 16px, color `#1E1E1E`.

2. Add 4px of extra vertical padding above and below the top bar.

3. Add a 1px bottom border (`#E5E7EB`) to visually separate the top bar from the panels.

4. Optionally, place the app icon (16x16 version from `assets/icons/simplicitor_16.png`) to the left of the "Simplicitor" title text, with 8px gap.

### Verification
- Top bar feels like a proper app header, not just a row of text.
- Visual line separates the top bar from the main content area.

---

## Section 8: Spacing and Rhythm

**Problem:** Various spacing issues: character counter too close to the Generate button, inconsistent padding between sections, cramped prompt areas.

### Tasks

1. Add `12px` vertical spacing between the character counter line and the primary action button below it.

2. Ensure consistent `12px` vertical spacing between sibling labeled sections within each panel (e.g., between "File type" selector and "Save to" field, between "Save to" and "Describe what you need").

3. Set the prompt text area minimum height to `120px` so it feels like a proper input, not a single-line field.

4. Add `8px` padding between the panel edge and its inner content (on top of the 16px panel padding from Section 2).

### Verification
- No cramped or touching elements.
- Visual rhythm is consistent across both panels.
- Prompt text areas are comfortably sized.

---

## Execution Order

Work in this order. Each section produces a visible improvement. Run the app after each section to visually confirm.

1. **Section 1** - Icon (quickest win, immediately visible)
2. **Section 2** - Panel separation (biggest perceived impact)
3. **Section 4** - Button styling (high visibility)
4. **Section 3** - Input field styling
5. **Section 5** - Drop zone
6. **Section 6** - Success messages (UX improvement)
7. **Section 7** - Header
8. **Section 8** - Spacing cleanup

All changes are styling-level. No business logic changes. If a section conflicts with existing code structure, flag it to Alex before improvising — do not refactor component hierarchies for styling.
