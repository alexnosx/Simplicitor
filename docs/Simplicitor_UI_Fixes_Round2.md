# Simplicitor - UI Polish Fixes (Round 2)

After the Round 1 polish, three issues remain visible. Fix them in this order.

---

## Fix 1: Title Bar Icon Too Light

**Problem:** The window icon at 16x16 in the title bar shows as a nearly blank blue square. The white S is not visible enough at small sizes.

**Root cause:** The provided 16px and 24px icons have the inner white frame removed (correct) but the S glyph is drawn at the same stroke weight as the larger sizes, which anti-aliases away at that resolution.

**Fix:** Replace the existing icon files with the new ones Alex will provide. No code changes needed, just file replacement.

### Tasks

1. Alex will deliver updated icon files with a heavier S at 16px and 24px.
2. Replace the files in `assets/icons/`:
   - `simplicitor_16.png`
   - `simplicitor_24.png`
   - `simplicitor_32.png`
   - `simplicitor.ico` (contains all sizes bundled)
3. Keep all other sizes (48+) unchanged.
4. Restart the app and verify the title bar icon now shows a clear blue square with a visible white S.

---

## Fix 2: Panel Containers Not Rendering Correctly

**Problem:** The left (Create) panel has no visible border or background distinction from the main window. The right (Edit) panel shows border fragments (a partial top border, stray elements near the right edge). The two panels do not feel like proper distinct containers.

**Root cause:** Likely one of these:
- The `setObjectName("panelContainer")` + stylesheet approach from Round 1 is not matching because the object name is being overwritten or the stylesheet is applied at the wrong level.
- The panel widgets are nested inside layouts that do not respect their styled borders (QVBoxLayout/QHBoxLayout do not paint the parent's border on child widget bounds).
- The main window's central widget is bleeding through.

### Tasks

1. **Use QFrame, not QWidget, for panel containers.** `QFrame` has built-in frame-painting support that is more reliable than stylesheet-only borders on `QWidget`.

   In both `create_panel.py` and `edit_panel.py`:

```python
from PySide6.QtWidgets import QFrame, QVBoxLayout

class CreatePanel(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("createPanel")
        self.setFrameShape(QFrame.StyledPanel)
        self.setStyleSheet("""
            QFrame#createPanel {
                background-color: #F5F5F5;
                border: 1px solid #E5E7EB;
                border-radius: 4px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        # ... rest of panel setup
```

   Use a unique object name per panel (`createPanel`, `editPanel`) so the stylesheet only applies to that specific frame, not its children.

2. **Verify the stylesheet only targets the root frame.** The `QFrame#createPanel { ... }` selector is intentionally specific. If you use `QFrame { ... }` without the object name, it will cascade to any QFrame children and break their rendering.

3. **In `main_window.py`, ensure the central widget does not interfere.** Set the central widget background explicitly:

```python
central = QWidget()
central.setStyleSheet("background-color: #FAFAFA;")
self.setCentralWidget(central)
```

   Then put a horizontal layout inside this central widget, and add the two QFrame panels to that layout with appropriate spacing:

```python
main_layout = QHBoxLayout(central)
main_layout.setContentsMargins(16, 16, 16, 16)
main_layout.setSpacing(12)
main_layout.addWidget(self.create_panel, stretch=1)
main_layout.addWidget(self.edit_panel, stretch=1)
```

4. **Remove any leftover stylesheet rules from Round 1 that may conflict.** Search the codebase for any `background-color: #F5F5F5` or `border: 1px solid #E5E7EB` applied at widget levels other than the root panel QFrames and remove them. Only the panel QFrames themselves should have these.

5. **Check child widgets are not inheriting the panel border.** If any child QWidget inside a panel shows an unexpected border, add an explicit reset:

```python
child_widget.setStyleSheet("border: none; background: transparent;")
```

### Verification

Run the app and confirm:
- Left panel (Create) has a visible light-gray background with a 1px border and 4px rounded corners.
- Right panel (Edit) has the same treatment.
- Both panels look identical in their container styling.
- There is a clean 12px gap between them.
- No stray border fragments, no bleed-through from the main window background.
- Child widgets (QLineEdit, QPlainTextEdit, QListWidget, etc.) inside the panels have their own white background and do not pick up the panel's gray background.

---

## Fix 3: Stray Text Near Right Edge of Edit Panel

**Problem:** In the current screenshot, there is visible "ro" text fragment near the right edge of the Edit panel, between the drop zone and the uploaded files area. This should not be there.

**Root cause:** Most likely a clipped label or widget that was not fully hidden, or a placeholder that is bleeding through from outside the panel. Could also be a scrollbar artifact or a widget positioned outside the panel's clip region.

### Tasks

1. Inspect `edit_panel.py` for any QLabel, QWidget, or other element that could contain "ro" or a partial string. Common candidates:
   - A label for "Drop zone" or similar that got partially positioned off-screen
   - A leftover debug/placeholder label from earlier development
   - A tooltip label that is incorrectly visible
   - A widget with text that got clipped by its parent

2. Check if the panel's horizontal layout is sized wider than the panel itself, causing children to render past the visible edge.

3. Ensure the edit panel's layout uses `setContentsMargins(16, 16, 16, 16)` and all child widgets are added via `addWidget()` without fixed positioning.

4. If you find a label with placeholder text (e.g., "Drop zone" or similar), remove it. The `drop_zone.py` widget should be self-contained with no external labels.

5. If the text is from a QLabel that was meant to be the panel title "Edit", verify it is positioned at the top of the panel, not off to the right.

### Verification

After the fix:
- The Edit panel shows only its intended widgets: drop zone, supported files label, uploaded files list, "Describe the change" label, prompt area, character counter, Save button.
- No partial text fragments visible anywhere.
- Right edge of the panel shows only the panel border, nothing beyond it.

---

## Execution Order

1. **Fix 2 first** (panel containers). This is the biggest visible issue and a structural fix.
2. **Fix 3 second** (stray text). Likely resolved as a side effect of Fix 2 if it was a layout issue, but verify explicitly.
3. **Fix 1 last** (icon replacement). Just a file swap, zero risk.

After all three fixes, take a fresh screenshot and send it to Alex for review.
