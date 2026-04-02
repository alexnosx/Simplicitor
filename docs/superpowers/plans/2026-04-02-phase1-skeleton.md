# Phase 1: Skeleton Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the complete Simplicitor UI skeleton — full two-panel window, settings dialog, config persistence, logging, and all stub modules — producing a runnable app where all UI is visible but generation/manipulation is disabled pending Phase 2.

**Architecture:** PySide6 `QMainWindow` hosts a `TopBar` (title, red/green dot, model dropdown, settings gear), a `CreatePanel` (left), and an `EditPanel` (right). A `Settings` class persists four directory paths as JSON. Workers, services, generators, and parsers are created as typed stubs. Phase 1 ends when `python simplicitor/main.py` opens a fully-laid-out, non-crashing window.

**Tech Stack:** Python 3.11+, PySide6 6.6+, pytest 7.4+, pytest-qt 4.2+

---

## File Map

| File | Responsibility |
|------|---------------|
| `requirements.txt` | All Python dependencies |
| `pytest.ini` | pytest config — adds `simplicitor/` to pythonpath |
| `tests/conftest.py` | Sets `QT_QPA_PLATFORM=offscreen` for headless widget tests |
| `tests/__init__.py` | Package marker |
| `tests/test_settings.py` | Settings load / save / reset tests |
| `tests/test_file_utils.py` | `sanitize_filename` and `ensure_dir` unit tests |
| `tests/test_widgets.py` | Widget instantiation smoke tests (pytest-qt) |
| `simplicitor/main.py` | Entry point — builds QApplication, Settings, MainWindow |
| `simplicitor/app/__init__.py` | Package marker |
| `simplicitor/app/main_window.py` | QMainWindow — assembles TopBar + CreatePanel + EditPanel |
| `simplicitor/app/config/__init__.py` | Package marker |
| `simplicitor/app/config/defaults.py` | ALL constants: colors, fonts, timeouts, limits, paths |
| `simplicitor/app/config/settings.py` | Settings class — JSON persistence, 4 dir paths |
| `simplicitor/app/widgets/__init__.py` | Package marker |
| `simplicitor/app/widgets/status_bar.py` | TopBar widget — title, dot, model combo, gear button |
| `simplicitor/app/widgets/create_panel.py` | Left panel — file type, save path, prompt, Generate btn |
| `simplicitor/app/widgets/edit_panel.py` | Right panel — drop zone, file list, prompt, Save btn |
| `simplicitor/app/widgets/drop_zone.py` | Drag-and-drop target with click-to-browse |
| `simplicitor/app/widgets/file_list.py` | Ordered uploaded-file list with selection |
| `simplicitor/app/widgets/settings_dialog.py` | Modal — 4 paths, View Logs, Reset to Defaults |
| `simplicitor/app/workers/__init__.py` | Package marker |
| `simplicitor/app/workers/ollama_worker.py` | Stub QThread — connection poller |
| `simplicitor/app/workers/generate_worker.py` | Stub QThread — file generation |
| `simplicitor/app/workers/manipulate_worker.py` | Stub QThread — file manipulation |
| `simplicitor/app/services/__init__.py` | Package marker |
| `simplicitor/app/services/ollama_client.py` | Stub — Ollama REST client |
| `simplicitor/app/services/file_generator.py` | Stub — orchestrates generation |
| `simplicitor/app/services/file_manipulator.py` | Stub — orchestrates manipulation |
| `simplicitor/app/services/backup_service.py` | Stub — backup logic |
| `simplicitor/app/generators/__init__.py` | Package marker |
| `simplicitor/app/generators/word_generator.py` | Stub — python-docx generator |
| `simplicitor/app/generators/excel_generator.py` | Stub — openpyxl generator |
| `simplicitor/app/generators/pptx_generator.py` | Stub — python-pptx generator |
| `simplicitor/app/parsers/__init__.py` | Package marker |
| `simplicitor/app/parsers/llm_response_parser.py` | Stub — LLM JSON parser |
| `simplicitor/app/utils/__init__.py` | Package marker |
| `simplicitor/app/utils/logging_setup.py` | Daily-rotating file logger |
| `simplicitor/app/utils/file_utils.py` | `sanitize_filename`, `ensure_dir` |
| `simplicitor/prompts/system_word.txt` | Word generation system prompt |
| `simplicitor/prompts/system_excel.txt` | Excel generation system prompt |
| `simplicitor/prompts/system_pptx.txt` | PowerPoint generation system prompt |
| `simplicitor/prompts/system_manipulate.txt` | File manipulation system prompt |

---

### Task 1: Project Scaffolding

**Files:**
- Create: all directories and `__init__.py` markers
- Create: `requirements.txt`
- Create: `pytest.ini`

- [ ] **Step 1: Create all package directories**

```bash
cd C:/Repos/Simplicitor
mkdir -p simplicitor/app/config
mkdir -p simplicitor/app/widgets
mkdir -p simplicitor/app/workers
mkdir -p simplicitor/app/services
mkdir -p simplicitor/app/generators
mkdir -p simplicitor/app/parsers
mkdir -p simplicitor/app/utils
mkdir -p simplicitor/prompts
mkdir -p tests
```

- [ ] **Step 2: Create all `__init__.py` markers**

```bash
touch simplicitor/__init__.py
touch simplicitor/app/__init__.py
touch simplicitor/app/config/__init__.py
touch simplicitor/app/widgets/__init__.py
touch simplicitor/app/workers/__init__.py
touch simplicitor/app/services/__init__.py
touch simplicitor/app/generators/__init__.py
touch simplicitor/app/parsers/__init__.py
touch simplicitor/app/utils/__init__.py
touch tests/__init__.py
```

- [ ] **Step 3: Write `requirements.txt`**

```
PySide6>=6.6.0
python-docx>=1.1.0
openpyxl>=3.1.2
python-pptx>=0.6.23
pypdf>=3.17.0
pdfplumber>=0.10.3
requests>=2.31.0
pytest>=7.4.0
pytest-qt>=4.2.0
```

- [ ] **Step 4: Write `pytest.ini`**

```ini
[pytest]
testpaths = tests
pythonpath = simplicitor
```

- [ ] **Step 5: Install dependencies**

```bash
pip install -r requirements.txt
```

Expected: all packages install without error.

- [ ] **Step 6: Commit**

```bash
git init
git add requirements.txt pytest.ini
git commit -m "chore: project scaffolding — dirs, requirements, pytest config"
```

---

### Task 2: Config Defaults

**Files:**
- Create: `simplicitor/app/config/defaults.py`

- [ ] **Step 1: Write `defaults.py`**

```python
# simplicitor/app/config/defaults.py

# ── Colors ───────────────────────────────────────────────────────────────────
BACKGROUND_COLOR = "#FAFAFA"
PANEL_BG_COLOR = "#F5F5F5"
PRIMARY_ACCENT_COLOR = "#2563EB"
BODY_TEXT_COLOR = "#1E1E1E"
SUCCESS_COLOR = "#16A34A"
ERROR_COLOR = "#DC2626"
DISABLED_COLOR = "#9CA3AF"
BORDER_COLOR = "#E5E7EB"
INFO_BANNER_BG_COLOR = "#EFF6FF"
WHITE = "#FFFFFF"

# ── Typography ────────────────────────────────────────────────────────────────
APP_FONT_FAMILY = "Segoe UI"
FONT_SIZE_BODY_PT = 10
FONT_SIZE_HEADING_PT = 11

# ── Ollama ────────────────────────────────────────────────────────────────────
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_TAGS_ENDPOINT = "/api/tags"
OLLAMA_PS_ENDPOINT = "/api/ps"
OLLAMA_SHOW_ENDPOINT = "/api/show"
OLLAMA_GENERATE_ENDPOINT = "/api/generate"
OLLAMA_CHAT_ENDPOINT = "/api/chat"
OLLAMA_POLL_INTERVAL_MS = 5000
OLLAMA_TIMEOUT_S = 60
SMALL_MODEL_PARAM_THRESHOLD = 7_000_000_000

# ── UI Limits ─────────────────────────────────────────────────────────────────
WINDOW_MIN_WIDTH = 1000
WINDOW_MIN_HEIGHT = 640
TOP_BAR_HEIGHT = 48
BORDER_RADIUS_PX = 4
MAX_PROMPT_CHARS = 2000
PROMPT_COMPLEXITY_THRESHOLD_CHARS = 500

# ── Styling keywords that trigger the small-model tip ────────────────────────
STYLING_KEYWORDS = [
    "color", "colour", "font", "bold", "italic", "blue", "red", "green",
    "highlight", "header", "footer", "align", "center", "centre", "table",
    "border", "background", "dark", "light",
]

# ── File Types ────────────────────────────────────────────────────────────────
GENERATE_FILE_TYPES = ["Word (.docx)", "Excel (.xlsx)", "PowerPoint (.pptx)"]
EDIT_EXTENSIONS = [".docx", ".xlsx", ".pptx", ".txt", ".pdf"]
EDIT_FILE_FILTER = "Supported Files (*.docx *.xlsx *.pptx *.txt *.pdf)"

# ── App Identity ──────────────────────────────────────────────────────────────
APP_NAME = "Simplicitor"
APP_DATA_SUBDIR = "Simplicitor"

# ── Default subdirectory names (under Documents/Simplicitor/) ─────────────────
DEFAULT_GENERATED_SUBDIR = "Generated"
DEFAULT_UPLOADS_SUBDIR = "Uploads"
DEFAULT_BACKUPS_SUBDIR = "Backups"
DEFAULT_LOGS_SUBDIR = "Logs"

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_FILE_PREFIX = "simplicitor_"
LOG_BACKUP_COUNT = 7

# ── Backup ────────────────────────────────────────────────────────────────────
BACKUP_SUFFIX = "_backup"

# ── Prompt placeholder text ───────────────────────────────────────────────────
PROMPT_PLACEHOLDERS = {
    "Word (.docx)": (
        "Describe the document you need, e.g.: Create a project status report "
        "with sections for timeline, risks, and next steps"
    ),
    "Excel (.xlsx)": (
        "Describe the spreadsheet you need, e.g.: Create a monthly budget tracker "
        "with columns for category, planned amount, actual amount, and difference"
    ),
    "PowerPoint (.pptx)": (
        "Describe the presentation you need, e.g.: Create a 5-slide pitch deck "
        "about our new product launch"
    ),
}
EDIT_PROMPT_PLACEHOLDERS = {
    ".docx": "What would you like to change? e.g.: Rewrite the executive summary to be more concise",
    ".xlsx": "What would you like to change? e.g.: Add a totals row and highlight cells where values exceed the budget",
    ".pptx": "What would you like to change? e.g.: Make the title slide dark blue with white text",
    ".txt": "What would you like to change? e.g.: Summarize this text into three bullet points",
    ".pdf": (
        "What would you like to extract? e.g.: Summarize the key findings from this report "
        "into bullet points (output will be saved as .docx or .txt)"
    ),
    "default": "Describe the change you want to make to this file",
}
```

- [ ] **Step 2: Verify import works**

```bash
cd C:/Repos/Simplicitor
python -c "from app.config.defaults import APP_NAME, PRIMARY_ACCENT_COLOR; print(APP_NAME)"
```

Expected output: `Simplicitor`

- [ ] **Step 3: Commit**

```bash
git add simplicitor/app/config/defaults.py
git commit -m "feat: add config defaults — all constants, colors, limits"
```

---

### Task 3: Settings Service

**Files:**
- Create: `tests/test_settings.py`
- Create: `simplicitor/app/config/settings.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_settings.py
from pathlib import Path
import json
import pytest
from app.config.settings import Settings


def test_settings_default_paths_contain_simplicitor(tmp_path: Path) -> None:
    s = Settings(tmp_path)
    assert "Simplicitor" in s.generated_dir
    assert "Simplicitor" in s.uploads_dir
    assert "Simplicitor" in s.backups_dir
    assert "Simplicitor" in s.logs_dir


def test_settings_paths_are_strings(tmp_path: Path) -> None:
    s = Settings(tmp_path)
    assert isinstance(s.generated_dir, str)
    assert isinstance(s.uploads_dir, str)
    assert isinstance(s.backups_dir, str)
    assert isinstance(s.logs_dir, str)


def test_settings_save_and_reload(tmp_path: Path) -> None:
    s = Settings(tmp_path)
    s.set("generated_dir", "/custom/generated")
    s.save()
    s2 = Settings(tmp_path)
    assert s2.generated_dir == "/custom/generated"


def test_settings_reload_preserves_other_keys(tmp_path: Path) -> None:
    s = Settings(tmp_path)
    original_uploads = s.uploads_dir
    s.set("generated_dir", "/custom/generated")
    s.save()
    s2 = Settings(tmp_path)
    assert s2.uploads_dir == original_uploads


def test_settings_reset_to_defaults(tmp_path: Path) -> None:
    s = Settings(tmp_path)
    s.set("generated_dir", "/custom/generated")
    s.save()
    s.reset_to_defaults()
    assert "Simplicitor" in s.generated_dir
    assert s.generated_dir != "/custom/generated"


def test_settings_reset_persists_to_disk(tmp_path: Path) -> None:
    s = Settings(tmp_path)
    s.set("generated_dir", "/custom/generated")
    s.save()
    s.reset_to_defaults()
    s2 = Settings(tmp_path)
    assert s2.generated_dir != "/custom/generated"


def test_settings_handles_corrupt_json(tmp_path: Path) -> None:
    config_file = tmp_path / "settings.json"
    config_file.write_text("{invalid json}", encoding="utf-8")
    s = Settings(tmp_path)  # must not raise
    assert "Simplicitor" in s.generated_dir


def test_settings_get_unknown_key_returns_default(tmp_path: Path) -> None:
    s = Settings(tmp_path)
    assert s.get("nonexistent_key", "fallback") == "fallback"
```

- [ ] **Step 2: Run to confirm they fail**

```bash
cd C:/Repos/Simplicitor
python -m pytest tests/test_settings.py -v
```

Expected: `ImportError` or `ModuleNotFoundError` — `settings` module does not exist yet.

- [ ] **Step 3: Write `settings.py`**

```python
# simplicitor/app/config/settings.py
import json
import logging
from pathlib import Path
from typing import Any

from app.config.defaults import APP_DATA_SUBDIR

logger = logging.getLogger(__name__)

_SETTINGS_FILENAME = "settings.json"


class Settings:
    """Persists application configuration to a JSON file.

    Four directory paths are managed: generated_dir, uploads_dir,
    backups_dir, and logs_dir. All default to subfolders under
    ~/Documents/Simplicitor/ on first run.
    """

    def __init__(self, config_dir: Path) -> None:
        self._config_dir = config_dir
        self._config_file = config_dir / _SETTINGS_FILENAME
        self._data: dict[str, Any] = {}
        self._load()

    # ── Private ───────────────────────────────────────────────────────────────

    def _default_data(self) -> dict[str, Any]:
        base = Path.home() / "Documents" / APP_DATA_SUBDIR
        return {
            "generated_dir": str(base / "Generated"),
            "uploads_dir": str(base / "Uploads"),
            "backups_dir": str(base / "Backups"),
            "logs_dir": str(base / "Logs"),
        }

    def _load(self) -> None:
        defaults = self._default_data()
        if self._config_file.exists():
            try:
                with open(self._config_file, encoding="utf-8") as f:
                    loaded = json.load(f)
                self._data = {**defaults, **loaded}
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning("Settings load failed (%s) — using defaults", exc)
                self._data = defaults
        else:
            self._data = defaults

    # ── Public API ────────────────────────────────────────────────────────────

    def save(self) -> None:
        """Persist current settings to disk."""
        try:
            self._config_dir.mkdir(parents=True, exist_ok=True)
            with open(self._config_file, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2)
        except OSError as exc:
            logger.error("Settings save failed: %s", exc)

    def get(self, key: str, default: Any = None) -> Any:
        """Return setting value for key, or default if not found."""
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a setting value in memory. Call save() to persist."""
        self._data[key] = value

    def reset_to_defaults(self) -> None:
        """Reset all settings to defaults and save to disk."""
        self._data = self._default_data()
        self.save()

    # ── Directory properties ──────────────────────────────────────────────────

    @property
    def generated_dir(self) -> str:
        """Default save location for generated files."""
        return str(self._data.get("generated_dir", ""))

    @property
    def uploads_dir(self) -> str:
        """Working directory for uploaded files."""
        return str(self._data.get("uploads_dir", ""))

    @property
    def backups_dir(self) -> str:
        """Directory for file backups."""
        return str(self._data.get("backups_dir", ""))

    @property
    def logs_dir(self) -> str:
        """Directory for log files."""
        return str(self._data.get("logs_dir", ""))
```

- [ ] **Step 4: Run tests — confirm they pass**

```bash
python -m pytest tests/test_settings.py -v
```

Expected: 8 tests PASSED.

- [ ] **Step 5: Commit**

```bash
git add simplicitor/app/config/settings.py tests/test_settings.py
git commit -m "feat: Settings service — JSON persistence, 4 dir paths, reset to defaults"
```

---

### Task 4: Utils — Logging and File Utilities

**Files:**
- Create: `tests/test_file_utils.py`
- Create: `simplicitor/app/utils/logging_setup.py`
- Create: `simplicitor/app/utils/file_utils.py`

- [ ] **Step 1: Write failing tests for file_utils**

```python
# tests/test_file_utils.py
from pathlib import Path
import pytest
from app.utils.file_utils import sanitize_filename, ensure_dir


def test_sanitize_removes_special_chars() -> None:
    assert sanitize_filename("Hello, World!") == "Hello_World"


def test_sanitize_replaces_spaces_with_underscores() -> None:
    assert sanitize_filename("my document name") == "my_document_name"


def test_sanitize_truncates_to_max_length() -> None:
    long = "a" * 100
    result = sanitize_filename(long, max_length=40)
    assert len(result) <= 40


def test_sanitize_empty_string_returns_document() -> None:
    assert sanitize_filename("") == "document"


def test_sanitize_only_special_chars_returns_document() -> None:
    assert sanitize_filename("!@#$%") == "document"


def test_sanitize_preserves_hyphens_and_underscores() -> None:
    result = sanitize_filename("my-doc_name")
    assert "my" in result
    assert "doc" in result
    assert "name" in result


def test_ensure_dir_creates_nested_dirs(tmp_path: Path) -> None:
    target = tmp_path / "a" / "b" / "c"
    result = ensure_dir(target)
    assert result.is_dir()
    assert result == target


def test_ensure_dir_accepts_string(tmp_path: Path) -> None:
    target = str(tmp_path / "new_dir")
    result = ensure_dir(target)
    assert result.is_dir()


def test_ensure_dir_idempotent(tmp_path: Path) -> None:
    """Calling ensure_dir twice on the same path must not raise."""
    ensure_dir(tmp_path / "existing")
    ensure_dir(tmp_path / "existing")  # no error
```

- [ ] **Step 2: Run to confirm they fail**

```bash
python -m pytest tests/test_file_utils.py -v
```

Expected: `ImportError`.

- [ ] **Step 3: Write `file_utils.py`**

```python
# simplicitor/app/utils/file_utils.py
import re
from pathlib import Path


def sanitize_filename(text: str, max_length: int = 40) -> str:
    """Convert arbitrary text into a safe filename fragment.

    Strips non-alphanumeric characters (except hyphens), replaces
    whitespace runs with underscores, and truncates to max_length.
    Returns 'document' if the result is empty.
    """
    cleaned = re.sub(r"[^\w\s-]", "", text).strip()
    cleaned = re.sub(r"[\s-]+", "_", cleaned)
    cleaned = cleaned[:max_length]
    return cleaned if cleaned else "document"


def ensure_dir(path: str | Path) -> Path:
    """Create directory (and all parents) if it does not exist.

    Returns the Path object for the directory.
    """
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p
```

- [ ] **Step 4: Write `logging_setup.py`**

```python
# simplicitor/app/utils/logging_setup.py
import logging
import logging.handlers
from pathlib import Path

from app.config.defaults import LOG_FILE_PREFIX, LOG_BACKUP_COUNT


def setup_logging(log_dir: str) -> None:
    """Configure application-wide logging with daily file rotation.

    Writes to <log_dir>/simplicitor_app.log, rotated at midnight.
    Stack traces and error details go here — never to the UI.
    File content and user prompts are never logged (privacy).
    """
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    log_file = log_path / f"{LOG_FILE_PREFIX}app.log"

    file_handler = logging.handlers.TimedRotatingFileHandler(
        log_file,
        when="midnight",
        backupCount=LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.suffix = "%Y%m%d"

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.addHandler(file_handler)

    # Console — warnings and above only, so dev output isn't noisy
    console = logging.StreamHandler()
    console.setLevel(logging.WARNING)
    console.setFormatter(formatter)
    root.addHandler(console)
```

- [ ] **Step 5: Run file_utils tests — confirm they pass**

```bash
python -m pytest tests/test_file_utils.py -v
```

Expected: 9 tests PASSED.

- [ ] **Step 6: Commit**

```bash
git add simplicitor/app/utils/file_utils.py simplicitor/app/utils/logging_setup.py tests/test_file_utils.py
git commit -m "feat: add file_utils (sanitize_filename, ensure_dir) and logging setup"
```

---

### Task 5: conftest and Widget Test Infrastructure

**Files:**
- Create: `tests/conftest.py`

- [ ] **Step 1: Write `conftest.py`**

```python
# tests/conftest.py
import os

# Use offscreen rendering so widget tests run without a display (CI, headless)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
```

- [ ] **Step 2: Verify pytest-qt is available**

```bash
python -m pytest --co -q 2>&1 | head -5
```

Expected: no import errors.

- [ ] **Step 3: Commit**

```bash
git add tests/conftest.py
git commit -m "test: add conftest with offscreen Qt platform for headless tests"
```

---

### Task 6: TopBar Widget

**Files:**
- Create: `simplicitor/app/widgets/status_bar.py`
- Modify: `tests/test_widgets.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_widgets.py
import pytest
from app.config.settings import Settings
from app.widgets.status_bar import TopBar


def test_top_bar_instantiates(qtbot) -> None:
    bar = TopBar()
    qtbot.addWidget(bar)


def test_top_bar_starts_disconnected(qtbot) -> None:
    bar = TopBar()
    qtbot.addWidget(bar)
    assert bar.current_model() == ""


def test_top_bar_set_connected_populates_model_combo(qtbot) -> None:
    bar = TopBar()
    qtbot.addWidget(bar)
    bar.set_connected(["llama3:8b", "mistral:7b"], "llama3:8b")
    assert bar.current_model() == "llama3:8b"


def test_top_bar_set_disconnected_clears_model(qtbot) -> None:
    bar = TopBar()
    qtbot.addWidget(bar)
    bar.set_connected(["llama3:8b"], "llama3:8b")
    bar.set_disconnected()
    assert bar.current_model() == ""
```

- [ ] **Step 2: Run to confirm they fail**

```bash
python -m pytest tests/test_widgets.py -v
```

Expected: `ImportError`.

- [ ] **Step 3: Write `status_bar.py`**

```python
# simplicitor/app/widgets/status_bar.py
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QComboBox, QPushButton
from PySide6.QtCore import Signal
from PySide6.QtGui import QFont

from app.config.defaults import (
    APP_NAME, APP_FONT_FAMILY, FONT_SIZE_HEADING_PT, FONT_SIZE_BODY_PT,
    SUCCESS_COLOR, ERROR_COLOR, BORDER_COLOR, BODY_TEXT_COLOR, WHITE,
)


class TopBar(QWidget):
    """Top navigation bar.

    Shows app title, Ollama connectivity dot, currently connected model,
    a model-selector dropdown, and a settings gear button.
    Signals are emitted; the MainWindow wires them to handlers.
    """

    settings_requested = Signal()
    model_changed = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_ui()
        self._apply_styles()
        self.set_disconnected()

    # ── Build ─────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(10)

        heading_font = QFont(APP_FONT_FAMILY, FONT_SIZE_HEADING_PT)
        heading_font.setWeight(QFont.Weight.DemiBold)

        body_font = QFont(APP_FONT_FAMILY, FONT_SIZE_BODY_PT)

        self._title_label = QLabel(APP_NAME)
        self._title_label.setFont(heading_font)

        self._status_dot = QLabel("●")
        self._status_dot.setFixedWidth(18)
        self._status_dot.setFont(body_font)

        self._status_text = QLabel()
        self._status_text.setFont(body_font)

        self._model_combo = QComboBox()
        self._model_combo.setMinimumWidth(200)
        self._model_combo.setFont(body_font)
        self._model_combo.currentTextChanged.connect(self.model_changed)

        self._settings_btn = QPushButton("⚙")
        self._settings_btn.setFixedSize(32, 32)
        self._settings_btn.setFont(QFont(APP_FONT_FAMILY, FONT_SIZE_HEADING_PT))
        self._settings_btn.setToolTip("Settings")
        self._settings_btn.clicked.connect(self.settings_requested)

        layout.addWidget(self._title_label)
        layout.addSpacing(8)
        layout.addWidget(self._status_dot)
        layout.addWidget(self._status_text)
        layout.addStretch()
        layout.addWidget(self._model_combo)
        layout.addSpacing(4)
        layout.addWidget(self._settings_btn)

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            f"TopBar {{ background-color: {WHITE}; border-bottom: 1px solid {BORDER_COLOR}; }}"
            f"QComboBox {{ color: {BODY_TEXT_COLOR}; }}"
            f"QPushButton {{ border: none; background: transparent; color: {BODY_TEXT_COLOR}; }}"
            f"QPushButton:hover {{ background-color: {BORDER_COLOR}; border-radius: 4px; }}"
        )

    # ── Public API ────────────────────────────────────────────────────────────

    def set_connected(self, models: list[str], current_model: str = "") -> None:
        """Switch to connected state and populate the model dropdown."""
        self._status_dot.setStyleSheet(f"color: {SUCCESS_COLOR};")
        self._status_text.setText("Connected")
        self._model_combo.setEnabled(True)
        self._model_combo.blockSignals(True)
        self._model_combo.clear()
        self._model_combo.addItems(models)
        if current_model and current_model in models:
            self._model_combo.setCurrentText(current_model)
        self._model_combo.blockSignals(False)

    def set_disconnected(self) -> None:
        """Switch to disconnected state and clear the model dropdown."""
        self._status_dot.setStyleSheet(f"color: {ERROR_COLOR};")
        self._status_text.setText("AI engine not connected")
        self._model_combo.setEnabled(False)
        self._model_combo.blockSignals(True)
        self._model_combo.clear()
        self._model_combo.blockSignals(False)

    def current_model(self) -> str:
        """Return the currently selected model name, or empty string."""
        return self._model_combo.currentText()

    def show_model_banner(self, message: str) -> None:
        """Show an inline model capability hint (called from MainWindow)."""
        # TODO: ASSUMPTION - banner handled at MainWindow level for now
        pass
```

- [ ] **Step 4: Run tests — confirm they pass**

```bash
python -m pytest tests/test_widgets.py -v
```

Expected: 4 tests PASSED.

- [ ] **Step 5: Commit**

```bash
git add simplicitor/app/widgets/status_bar.py tests/test_widgets.py
git commit -m "feat: TopBar widget — title, connection dot, model dropdown, settings gear"
```

---

### Task 7: CreatePanel Widget

**Files:**
- Create: `simplicitor/app/widgets/create_panel.py`
- Modify: `tests/test_widgets.py`

- [ ] **Step 1: Add failing tests**

Append to `tests/test_widgets.py`:

```python
from app.widgets.create_panel import CreatePanel
from app.config.settings import Settings


def test_create_panel_instantiates(qtbot, tmp_path) -> None:
    settings = Settings(tmp_path)
    panel = CreatePanel(settings)
    qtbot.addWidget(panel)


def test_create_panel_generate_button_disabled_by_default(qtbot, tmp_path) -> None:
    settings = Settings(tmp_path)
    panel = CreatePanel(settings)
    qtbot.addWidget(panel)
    # Generate is disabled until Ollama is connected (Phase 2 enables it)
    assert not panel.generate_button_enabled()


def test_create_panel_prompt_empty_by_default(qtbot, tmp_path) -> None:
    settings = Settings(tmp_path)
    panel = CreatePanel(settings)
    qtbot.addWidget(panel)
    assert panel.prompt_text() == ""
```

- [ ] **Step 2: Run to confirm they fail**

```bash
python -m pytest tests/test_widgets.py::test_create_panel_instantiates -v
```

Expected: `ImportError`.

- [ ] **Step 3: Write `create_panel.py`**

```python
# simplicitor/app/widgets/create_panel.py
import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QLineEdit, QPushButton, QTextEdit, QFileDialog, QSizePolicy,
)
from PySide6.QtCore import Signal
from PySide6.QtGui import QFont

from app.config.defaults import (
    APP_FONT_FAMILY, FONT_SIZE_BODY_PT, FONT_SIZE_HEADING_PT,
    GENERATE_FILE_TYPES, PROMPT_PLACEHOLDERS, MAX_PROMPT_CHARS,
    PANEL_BG_COLOR, PRIMARY_ACCENT_COLOR, BORDER_COLOR, BODY_TEXT_COLOR,
    DISABLED_COLOR, WHITE, BACKGROUND_COLOR, BORDER_RADIUS_PX,
)
from app.config.settings import Settings


class CreatePanel(QWidget):
    """Left panel: generate a new Office document from a prompt.

    Emits generate_requested(file_type, save_path, prompt) when the
    Generate button is clicked. The MainWindow wires this to the worker.
    Stays disabled until set_ollama_connected(True) is called (Phase 2).
    """

    generate_requested = Signal(str, str, str)  # file_type, save_path, prompt

    def __init__(self, settings: Settings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._settings = settings
        self._build_ui()
        self._apply_styles()
        self._connect_signals()

    # ── Build ─────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        heading_font = QFont(APP_FONT_FAMILY, FONT_SIZE_HEADING_PT)
        heading_font.setWeight(QFont.Weight.DemiBold)
        body_font = QFont(APP_FONT_FAMILY, FONT_SIZE_BODY_PT)

        # Section heading
        heading = QLabel("Create")
        heading.setFont(heading_font)
        layout.addWidget(heading)

        # File type selector
        type_label = QLabel("File type")
        type_label.setFont(body_font)
        self._type_combo = QComboBox()
        self._type_combo.addItems(GENERATE_FILE_TYPES)
        self._type_combo.setFont(body_font)
        layout.addWidget(type_label)
        layout.addWidget(self._type_combo)

        # Save location
        save_label = QLabel("Save to")
        save_label.setFont(body_font)
        save_row = QHBoxLayout()
        self._save_path_edit = QLineEdit()
        self._save_path_edit.setFont(body_font)
        self._save_path_edit.setPlaceholderText(self._settings.generated_dir)
        self._save_path_edit.setText(self._settings.generated_dir)
        self._browse_btn = QPushButton("Browse…")
        self._browse_btn.setFont(body_font)
        self._browse_btn.setFixedHeight(32)
        save_row.addWidget(self._save_path_edit)
        save_row.addWidget(self._browse_btn)
        layout.addWidget(save_label)
        layout.addLayout(save_row)

        # Prompt
        prompt_label = QLabel("Describe what you need")
        prompt_label.setFont(body_font)
        self._prompt_edit = QTextEdit()
        self._prompt_edit.setFont(body_font)
        self._prompt_edit.setMinimumHeight(120)
        self._prompt_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._update_placeholder()

        # Character counter
        self._char_counter = QLabel(f"0 / {MAX_PROMPT_CHARS}")
        self._char_counter.setFont(QFont(APP_FONT_FAMILY, 8))
        self._char_counter.setAlignment(Qt.AlignmentFlag.AlignRight)  # type: ignore[attr-defined]

        layout.addWidget(prompt_label)
        layout.addWidget(self._prompt_edit)
        layout.addWidget(self._char_counter)

        # Generate button
        self._generate_btn = QPushButton("Generate")
        self._generate_btn.setFont(heading_font)
        self._generate_btn.setFixedHeight(40)
        self._generate_btn.setEnabled(False)  # enabled when Ollama connects (Phase 2)
        layout.addWidget(self._generate_btn)

        # Status area (hidden until needed)
        self._status_label = QLabel("")
        self._status_label.setFont(body_font)
        self._status_label.setVisible(False)
        layout.addWidget(self._status_label)

        layout.addStretch()

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            f"CreatePanel {{ background-color: {PANEL_BG_COLOR}; }}"
            f"QTextEdit {{ background-color: {WHITE}; border: 1px solid {BORDER_COLOR}; "
            f"border-radius: {BORDER_RADIUS_PX}px; padding: 6px; color: {BODY_TEXT_COLOR}; }}"
            f"QLineEdit {{ background-color: {WHITE}; border: 1px solid {BORDER_COLOR}; "
            f"border-radius: {BORDER_RADIUS_PX}px; padding: 4px 8px; color: {BODY_TEXT_COLOR}; }}"
            f"QPushButton#generate_btn {{ background-color: {PRIMARY_ACCENT_COLOR}; color: white; "
            f"border-radius: {BORDER_RADIUS_PX}px; font-weight: 600; }}"
            f"QPushButton#generate_btn:disabled {{ background-color: {DISABLED_COLOR}; }}"
            f"QPushButton#generate_btn:hover:enabled {{ background-color: #1D4ED8; }}"
        )
        self._generate_btn.setObjectName("generate_btn")

    def _connect_signals(self) -> None:
        self._type_combo.currentTextChanged.connect(self._update_placeholder)
        self._browse_btn.clicked.connect(self._browse_save_dir)
        self._prompt_edit.textChanged.connect(self._on_prompt_changed)
        self._generate_btn.clicked.connect(self._on_generate_clicked)

    # ── Private handlers ──────────────────────────────────────────────────────

    def _update_placeholder(self) -> None:
        file_type = self._type_combo.currentText()
        placeholder = PROMPT_PLACEHOLDERS.get(file_type, "Describe what you need…")
        self._prompt_edit.setPlaceholderText(placeholder)

    def _browse_save_dir(self) -> None:
        current = self._save_path_edit.text() or self._settings.generated_dir
        chosen = QFileDialog.getExistingDirectory(self, "Select Save Location", current)
        if chosen:
            self._save_path_edit.setText(chosen)

    def _on_prompt_changed(self) -> None:
        text = self._prompt_edit.toPlainText()
        if len(text) > MAX_PROMPT_CHARS:
            cursor = self._prompt_edit.textCursor()
            self._prompt_edit.setPlainText(text[:MAX_PROMPT_CHARS])
            self._prompt_edit.setTextCursor(cursor)
        self._char_counter.setText(f"{min(len(text), MAX_PROMPT_CHARS)} / {MAX_PROMPT_CHARS}")

    def _on_generate_clicked(self) -> None:
        self.generate_requested.emit(
            self._type_combo.currentText(),
            self._save_path_edit.text(),
            self._prompt_edit.toPlainText().strip(),
        )

    # ── Public API ────────────────────────────────────────────────────────────

    def set_ollama_connected(self, connected: bool) -> None:
        """Enable or disable the Generate button based on Ollama connectivity."""
        self._generate_btn.setEnabled(connected)

    def set_generating(self, in_progress: bool) -> None:
        """Show/hide generation in-progress state."""
        self._generate_btn.setEnabled(not in_progress)
        self._generate_btn.setText("Generating…" if in_progress else "Generate")

    def prompt_text(self) -> str:
        """Return current prompt text."""
        return self._prompt_edit.toPlainText()

    def generate_button_enabled(self) -> bool:
        """Return True if the Generate button is enabled."""
        return self._generate_btn.isEnabled()

    def show_status(self, message: str, is_error: bool = False) -> None:
        """Display a status message below the Generate button."""
        color = "#DC2626" if is_error else "#16A34A"
        self._status_label.setStyleSheet(f"color: {color};")
        self._status_label.setText(message)
        self._status_label.setVisible(True)

    def clear_status(self) -> None:
        """Hide the status message."""
        self._status_label.setVisible(False)
        self._status_label.setText("")
```

**Note:** Add `from PySide6.QtCore import Qt` at the top of the file (needed for `Qt.AlignmentFlag`).

- [ ] **Step 4: Fix the Qt import at the top of create_panel.py**

The import block should be:
```python
from PySide6.QtCore import Signal, Qt
```

- [ ] **Step 5: Run tests — confirm they pass**

```bash
python -m pytest tests/test_widgets.py -v
```

Expected: all tests PASSED.

- [ ] **Step 6: Commit**

```bash
git add simplicitor/app/widgets/create_panel.py tests/test_widgets.py
git commit -m "feat: CreatePanel widget — file type selector, save path, prompt, Generate button"
```

---

### Task 8: DropZone and FileList Widgets

**Files:**
- Create: `simplicitor/app/widgets/drop_zone.py`
- Create: `simplicitor/app/widgets/file_list.py`
- Modify: `tests/test_widgets.py`

- [ ] **Step 1: Add failing tests**

Append to `tests/test_widgets.py`:

```python
from app.widgets.drop_zone import DropZone
from app.widgets.file_list import FileList


def test_drop_zone_instantiates(qtbot) -> None:
    zone = DropZone()
    qtbot.addWidget(zone)


def test_file_list_instantiates(qtbot) -> None:
    file_list = FileList()
    qtbot.addWidget(file_list)


def test_file_list_add_file(qtbot) -> None:
    file_list = FileList()
    qtbot.addWidget(file_list)
    file_list.add_file("/tmp/report.docx")
    assert file_list.file_count() == 1


def test_file_list_selected_file_is_most_recent(qtbot) -> None:
    file_list = FileList()
    qtbot.addWidget(file_list)
    file_list.add_file("/tmp/first.docx")
    file_list.add_file("/tmp/second.docx")
    assert file_list.selected_file_path() == "/tmp/second.docx"


def test_file_list_clear(qtbot) -> None:
    file_list = FileList()
    qtbot.addWidget(file_list)
    file_list.add_file("/tmp/report.docx")
    file_list.clear_files()
    assert file_list.file_count() == 0
```

- [ ] **Step 2: Run to confirm they fail**

```bash
python -m pytest tests/test_widgets.py -k "drop_zone or file_list" -v
```

Expected: `ImportError`.

- [ ] **Step 3: Write `drop_zone.py`**

```python
# simplicitor/app/widgets/drop_zone.py
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFileDialog
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QFont, QDragEnterEvent, QDropEvent

from app.config.defaults import (
    APP_FONT_FAMILY, FONT_SIZE_BODY_PT, BORDER_COLOR, PANEL_BG_COLOR,
    BODY_TEXT_COLOR, PRIMARY_ACCENT_COLOR, EDIT_FILE_FILTER,
)


class DropZone(QWidget):
    """Drag-and-drop target for file upload.

    Emits files_dropped(list[str]) with a list of accepted file paths.
    Clicking the widget opens a file browser dialog.
    """

    files_dropped = Signal(list)  # list[str] of file paths

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self._hovering = False
        self._build_ui()
        self._apply_styles()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        body_font = QFont(APP_FONT_FAMILY, FONT_SIZE_BODY_PT)

        self._main_label = QLabel("Drop files here\nor click to browse")
        self._main_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._main_label.setFont(body_font)

        self._types_label = QLabel("Word, Excel, PowerPoint, Text, PDF")
        self._types_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        small_font = QFont(APP_FONT_FAMILY, 8)
        self._types_label.setFont(small_font)
        self._types_label.setStyleSheet(f"color: {BODY_TEXT_COLOR}; opacity: 0.6;")

        layout.addWidget(self._main_label)
        layout.addWidget(self._types_label)

    def _apply_styles(self) -> None:
        self._update_style(hovering=False)

    def _update_style(self, hovering: bool) -> None:
        border_color = PRIMARY_ACCENT_COLOR if hovering else BORDER_COLOR
        bg_color = "#EFF6FF" if hovering else PANEL_BG_COLOR
        self.setStyleSheet(
            f"DropZone {{ border: 2px dashed {border_color}; border-radius: 4px; "
            f"background-color: {bg_color}; }}"
        )

    # ── Event handlers ────────────────────────────────────────────────────────

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Select Files", "", EDIT_FILE_FILTER
        )
        if paths:
            self.files_dropped.emit(paths)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self._update_style(hovering=True)
        else:
            event.ignore()

    def dragLeaveEvent(self, event) -> None:  # type: ignore[override]
        self._update_style(hovering=False)

    def dropEvent(self, event: QDropEvent) -> None:
        self._update_style(hovering=False)
        paths = [url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()]
        if paths:
            self.files_dropped.emit(paths)
```

- [ ] **Step 4: Write `file_list.py`**

```python
# simplicitor/app/widgets/file_list.py
from pathlib import Path
from PySide6.QtWidgets import QWidget, QVBoxLayout, QListWidget, QListWidgetItem
from PySide6.QtCore import Signal
from PySide6.QtGui import QFont

from app.config.defaults import (
    APP_FONT_FAMILY, FONT_SIZE_BODY_PT, BORDER_COLOR, WHITE,
    PRIMARY_ACCENT_COLOR, BODY_TEXT_COLOR, BORDER_RADIUS_PX,
)


class FileList(QWidget):
    """Ordered list of uploaded files; most-recent first, auto-selects latest.

    Emits file_selected(str) with the full file path when selection changes.
    """

    file_selected = Signal(str)  # full file path

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._paths: list[str] = []  # ordered: index 0 = most recent
        self._build_ui()
        self._apply_styles()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._list_widget = QListWidget()
        self._list_widget.setFont(QFont(APP_FONT_FAMILY, FONT_SIZE_BODY_PT))
        self._list_widget.currentRowChanged.connect(self._on_selection_changed)
        layout.addWidget(self._list_widget)

    def _apply_styles(self) -> None:
        self._list_widget.setStyleSheet(
            f"QListWidget {{ background-color: {WHITE}; border: 1px solid {BORDER_COLOR}; "
            f"border-radius: {BORDER_RADIUS_PX}px; color: {BODY_TEXT_COLOR}; }}"
            f"QListWidget::item:selected {{ background-color: {PRIMARY_ACCENT_COLOR}; color: white; }}"
            f"QListWidget::item {{ padding: 6px 10px; }}"
        )

    def _on_selection_changed(self, row: int) -> None:
        if 0 <= row < len(self._paths):
            self.file_selected.emit(self._paths[row])

    # ── Public API ────────────────────────────────────────────────────────────

    def add_file(self, path: str) -> None:
        """Add a file to the top of the list and select it."""
        self._paths.insert(0, path)
        item = QListWidgetItem(Path(path).name)
        item.setToolTip(path)
        self._list_widget.insertItem(0, item)
        self._list_widget.setCurrentRow(0)

    def selected_file_path(self) -> str:
        """Return the path of the currently selected file, or empty string."""
        row = self._list_widget.currentRow()
        if 0 <= row < len(self._paths):
            return self._paths[row]
        return ""

    def file_count(self) -> int:
        """Return total number of files in the list."""
        return len(self._paths)

    def clear_files(self) -> None:
        """Remove all files from the list."""
        self._paths.clear()
        self._list_widget.clear()
```

- [ ] **Step 5: Run tests — confirm they pass**

```bash
python -m pytest tests/test_widgets.py -v
```

Expected: all tests PASSED.

- [ ] **Step 6: Commit**

```bash
git add simplicitor/app/widgets/drop_zone.py simplicitor/app/widgets/file_list.py tests/test_widgets.py
git commit -m "feat: DropZone (drag-and-drop) and FileList (ordered upload list) widgets"
```

---

### Task 9: EditPanel Widget

**Files:**
- Create: `simplicitor/app/widgets/edit_panel.py`
- Modify: `tests/test_widgets.py`

- [ ] **Step 1: Add failing tests**

Append to `tests/test_widgets.py`:

```python
from app.widgets.edit_panel import EditPanel


def test_edit_panel_instantiates(qtbot, tmp_path) -> None:
    settings = Settings(tmp_path)
    panel = EditPanel(settings)
    qtbot.addWidget(panel)


def test_edit_panel_save_button_disabled_by_default(qtbot, tmp_path) -> None:
    settings = Settings(tmp_path)
    panel = EditPanel(settings)
    qtbot.addWidget(panel)
    assert not panel.save_button_enabled()


def test_edit_panel_prompt_empty_by_default(qtbot, tmp_path) -> None:
    settings = Settings(tmp_path)
    panel = EditPanel(settings)
    qtbot.addWidget(panel)
    assert panel.prompt_text() == ""
```

- [ ] **Step 2: Write `edit_panel.py`**

```python
# simplicitor/app/widgets/edit_panel.py
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTextEdit, QPushButton, QSizePolicy,
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QFont

from app.config.defaults import (
    APP_FONT_FAMILY, FONT_SIZE_BODY_PT, FONT_SIZE_HEADING_PT,
    MAX_PROMPT_CHARS, PANEL_BG_COLOR, PRIMARY_ACCENT_COLOR, BORDER_COLOR,
    BODY_TEXT_COLOR, DISABLED_COLOR, WHITE, BORDER_RADIUS_PX,
    EDIT_PROMPT_PLACEHOLDERS,
)
from app.config.settings import Settings
from app.widgets.drop_zone import DropZone
from app.widgets.file_list import FileList


class EditPanel(QWidget):
    """Right panel: upload a file, describe changes, save the result.

    Emits save_requested(file_path, prompt) when Save is clicked.
    Disabled until Ollama connects (set_ollama_connected) and a file
    is selected (handled internally via file_list.file_selected).
    """

    save_requested = Signal(str, str)  # file_path, prompt

    def __init__(self, settings: Settings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._settings = settings
        self._selected_file = ""
        self._ollama_connected = False
        self._build_ui()
        self._apply_styles()
        self._connect_signals()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        heading_font = QFont(APP_FONT_FAMILY, FONT_SIZE_HEADING_PT)
        heading_font.setWeight(QFont.Weight.DemiBold)
        body_font = QFont(APP_FONT_FAMILY, FONT_SIZE_BODY_PT)

        heading = QLabel("Edit")
        heading.setFont(heading_font)
        layout.addWidget(heading)

        # Drop zone
        self._drop_zone = DropZone()
        self._drop_zone.setFixedHeight(90)
        layout.addWidget(self._drop_zone)

        # File list
        file_list_label = QLabel("Uploaded files")
        file_list_label.setFont(body_font)
        self._file_list = FileList()
        self._file_list.setMinimumHeight(100)
        layout.addWidget(file_list_label)
        layout.addWidget(self._file_list)

        # Prompt
        prompt_label = QLabel("Describe the change")
        prompt_label.setFont(body_font)
        self._prompt_edit = QTextEdit()
        self._prompt_edit.setFont(body_font)
        self._prompt_edit.setMinimumHeight(100)
        self._prompt_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._prompt_edit.setPlaceholderText(EDIT_PROMPT_PLACEHOLDERS["default"])

        self._char_counter = QLabel(f"0 / {MAX_PROMPT_CHARS}")
        self._char_counter.setFont(QFont(APP_FONT_FAMILY, 8))
        self._char_counter.setAlignment(Qt.AlignmentFlag.AlignRight)

        layout.addWidget(prompt_label)
        layout.addWidget(self._prompt_edit)
        layout.addWidget(self._char_counter)

        # Save button
        self._save_btn = QPushButton("Save")
        self._save_btn.setFont(heading_font)
        self._save_btn.setFixedHeight(40)
        self._save_btn.setEnabled(False)
        layout.addWidget(self._save_btn)

        # Status label
        self._status_label = QLabel("")
        self._status_label.setFont(body_font)
        self._status_label.setVisible(False)
        layout.addWidget(self._status_label)

        layout.addStretch()

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            f"EditPanel {{ background-color: {PANEL_BG_COLOR}; }}"
            f"QTextEdit {{ background-color: {WHITE}; border: 1px solid {BORDER_COLOR}; "
            f"border-radius: {BORDER_RADIUS_PX}px; padding: 6px; color: {BODY_TEXT_COLOR}; }}"
            f"QPushButton#save_btn {{ background-color: {PRIMARY_ACCENT_COLOR}; color: white; "
            f"border-radius: {BORDER_RADIUS_PX}px; font-weight: 600; }}"
            f"QPushButton#save_btn:disabled {{ background-color: {DISABLED_COLOR}; }}"
            f"QPushButton#save_btn:hover:enabled {{ background-color: #1D4ED8; }}"
        )
        self._save_btn.setObjectName("save_btn")

    def _connect_signals(self) -> None:
        self._drop_zone.files_dropped.connect(self._on_files_dropped)
        self._file_list.file_selected.connect(self._on_file_selected)
        self._prompt_edit.textChanged.connect(self._on_prompt_changed)
        self._save_btn.clicked.connect(self._on_save_clicked)

    def _update_save_button_state(self) -> None:
        self._save_btn.setEnabled(bool(self._selected_file) and self._ollama_connected)

    def _on_files_dropped(self, paths: list) -> None:
        for path in paths:
            self._file_list.add_file(path)

    def _on_file_selected(self, path: str) -> None:
        self._selected_file = path
        ext = Path(path).suffix.lower()
        placeholder = EDIT_PROMPT_PLACEHOLDERS.get(ext, EDIT_PROMPT_PLACEHOLDERS["default"])
        self._prompt_edit.setPlaceholderText(placeholder)
        self._update_save_button_state()

    def _on_prompt_changed(self) -> None:
        text = self._prompt_edit.toPlainText()
        if len(text) > MAX_PROMPT_CHARS:
            cursor = self._prompt_edit.textCursor()
            self._prompt_edit.setPlainText(text[:MAX_PROMPT_CHARS])
            self._prompt_edit.setTextCursor(cursor)
        self._char_counter.setText(f"{min(len(text), MAX_PROMPT_CHARS)} / {MAX_PROMPT_CHARS}")

    def _on_save_clicked(self) -> None:
        self.save_requested.emit(self._selected_file, self._prompt_edit.toPlainText().strip())

    # ── Public API ────────────────────────────────────────────────────────────

    def set_ollama_connected(self, connected: bool) -> None:
        self._ollama_connected = connected
        self._update_save_button_state()

    def save_button_enabled(self) -> bool:
        return self._save_btn.isEnabled()

    def prompt_text(self) -> str:
        return self._prompt_edit.toPlainText()

    def show_status(self, message: str, is_error: bool = False) -> None:
        color = "#DC2626" if is_error else "#16A34A"
        self._status_label.setStyleSheet(f"color: {color};")
        self._status_label.setText(message)
        self._status_label.setVisible(True)

    def clear_status(self) -> None:
        self._status_label.setVisible(False)
        self._status_label.setText("")
```

- [ ] **Step 3: Run tests**

```bash
python -m pytest tests/test_widgets.py -v
```

Expected: all tests PASSED.

- [ ] **Step 4: Commit**

```bash
git add simplicitor/app/widgets/edit_panel.py tests/test_widgets.py
git commit -m "feat: EditPanel widget — drop zone, file list, prompt, Save button"
```

---

### Task 10: SettingsDialog Widget

**Files:**
- Create: `simplicitor/app/widgets/settings_dialog.py`
- Modify: `tests/test_widgets.py`

- [ ] **Step 1: Add failing tests**

Append to `tests/test_widgets.py`:

```python
from app.widgets.settings_dialog import SettingsDialog


def test_settings_dialog_instantiates(qtbot, tmp_path) -> None:
    settings = Settings(tmp_path)
    dialog = SettingsDialog(settings)
    qtbot.addWidget(dialog)


def test_settings_dialog_shows_current_paths(qtbot, tmp_path) -> None:
    settings = Settings(tmp_path)
    settings.set("generated_dir", "/my/generated")
    dialog = SettingsDialog(settings)
    qtbot.addWidget(dialog)
    assert dialog.generated_dir_value() == "/my/generated"
```

- [ ] **Step 2: Write `settings_dialog.py`**

```python
# simplicitor/app/widgets/settings_dialog.py
import subprocess
import sys
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QPushButton, QDialogButtonBox, QFileDialog,
)
from PySide6.QtGui import QFont

from app.config.defaults import (
    APP_FONT_FAMILY, FONT_SIZE_BODY_PT, FONT_SIZE_HEADING_PT,
    BORDER_COLOR, WHITE, BORDER_RADIUS_PX, PRIMARY_ACCENT_COLOR,
    BODY_TEXT_COLOR, BACKGROUND_COLOR,
)
from app.config.settings import Settings


class SettingsDialog(QDialog):
    """Modal settings dialog.

    Presents four editable directory paths. Changes are applied on Save
    and written back to the Settings object; the caller must call
    settings.save() if it wants them persisted beyond this session
    (here we call it immediately on accept).
    """

    def __init__(self, settings: Settings, parent=None) -> None:
        super().__init__(parent)
        self._settings = settings
        self.setWindowTitle("Settings")
        self.setMinimumWidth(520)
        self._build_ui()
        self._apply_styles()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)

        heading_font = QFont(APP_FONT_FAMILY, FONT_SIZE_HEADING_PT)
        heading_font.setWeight(QFont.Weight.DemiBold)
        body_font = QFont(APP_FONT_FAMILY, FONT_SIZE_BODY_PT)

        heading = QLabel("Settings")
        heading.setFont(heading_font)
        layout.addWidget(heading)

        form = QFormLayout()
        form.setSpacing(10)

        self._generated_edit = self._make_path_row(
            self._settings.generated_dir, "Select Generated Files Location"
        )
        self._uploads_edit = self._make_path_row(
            self._settings.uploads_dir, "Select Uploads Location"
        )
        self._backups_edit = self._make_path_row(
            self._settings.backups_dir, "Select Backups Location"
        )
        self._logs_edit = self._make_path_row(
            self._settings.logs_dir, "Select Logs Location"
        )

        def add_row(label: str, row_widget: QHBoxLayout) -> None:
            lbl = QLabel(label)
            lbl.setFont(body_font)
            form.addRow(lbl, row_widget)

        add_row("Generated files:", self._generated_edit["layout"])
        add_row("Uploaded files:", self._uploads_edit["layout"])
        add_row("Backups:", self._backups_edit["layout"])
        add_row("Logs:", self._logs_edit["layout"])

        layout.addLayout(form)

        # View logs + Reset buttons row
        extra_row = QHBoxLayout()
        self._view_logs_btn = QPushButton("View Logs Folder")
        self._view_logs_btn.setFont(body_font)
        self._view_logs_btn.clicked.connect(self._open_logs_folder)
        self._reset_btn = QPushButton("Reset to Defaults")
        self._reset_btn.setFont(body_font)
        self._reset_btn.clicked.connect(self._reset_to_defaults)
        extra_row.addWidget(self._view_logs_btn)
        extra_row.addStretch()
        extra_row.addWidget(self._reset_btn)
        layout.addLayout(extra_row)

        # OK / Cancel
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _make_path_row(self, current_value: str, dialog_title: str) -> dict:
        """Return a dict with 'layout' (QHBoxLayout) and 'edit' (QLineEdit)."""
        h = QHBoxLayout()
        h.setSpacing(6)
        edit = QLineEdit(current_value)
        edit.setFont(QFont(APP_FONT_FAMILY, FONT_SIZE_BODY_PT))
        browse_btn = QPushButton("…")
        browse_btn.setFixedSize(28, 28)
        browse_btn.clicked.connect(lambda: self._browse(edit, dialog_title))
        h.addWidget(edit)
        h.addWidget(browse_btn)
        return {"layout": h, "edit": edit}

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            f"QDialog {{ background-color: {BACKGROUND_COLOR}; }}"
            f"QLineEdit {{ background-color: {WHITE}; border: 1px solid {BORDER_COLOR}; "
            f"border-radius: {BORDER_RADIUS_PX}px; padding: 4px 8px; color: {BODY_TEXT_COLOR}; }}"
        )

    def _browse(self, edit: QLineEdit, title: str) -> None:
        chosen = QFileDialog.getExistingDirectory(self, title, edit.text())
        if chosen:
            edit.setText(chosen)

    def _open_logs_folder(self) -> None:
        logs_dir = self._logs_edit["edit"].text()
        if sys.platform == "win32":
            subprocess.Popen(["explorer", logs_dir])

    def _reset_to_defaults(self) -> None:
        self._settings.reset_to_defaults()
        self._generated_edit["edit"].setText(self._settings.generated_dir)
        self._uploads_edit["edit"].setText(self._settings.uploads_dir)
        self._backups_edit["edit"].setText(self._settings.backups_dir)
        self._logs_edit["edit"].setText(self._settings.logs_dir)

    def _on_save(self) -> None:
        self._settings.set("generated_dir", self._generated_edit["edit"].text())
        self._settings.set("uploads_dir", self._uploads_edit["edit"].text())
        self._settings.set("backups_dir", self._backups_edit["edit"].text())
        self._settings.set("logs_dir", self._logs_edit["edit"].text())
        self._settings.save()
        self.accept()

    # ── Public API ────────────────────────────────────────────────────────────

    def generated_dir_value(self) -> str:
        return self._generated_edit["edit"].text()
```

- [ ] **Step 3: Run tests**

```bash
python -m pytest tests/test_widgets.py -v
```

Expected: all tests PASSED.

- [ ] **Step 4: Commit**

```bash
git add simplicitor/app/widgets/settings_dialog.py tests/test_widgets.py
git commit -m "feat: SettingsDialog — 4 path fields, View Logs, Reset to Defaults, Save/Cancel"
```

---

### Task 11: MainWindow

**Files:**
- Create: `simplicitor/app/main_window.py`
- Modify: `tests/test_widgets.py`

- [ ] **Step 1: Add failing tests**

Append to `tests/test_widgets.py`:

```python
from app.main_window import MainWindow


def test_main_window_instantiates(qtbot, tmp_path) -> None:
    settings = Settings(tmp_path)
    window = MainWindow(settings)
    qtbot.addWidget(window)


def test_main_window_has_minimum_size(qtbot, tmp_path) -> None:
    settings = Settings(tmp_path)
    window = MainWindow(settings)
    qtbot.addWidget(window)
    assert window.minimumWidth() >= 1000
    assert window.minimumHeight() >= 640
```

- [ ] **Step 2: Write `main_window.py`**

```python
# simplicitor/app/main_window.py
import logging
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
)
from PySide6.QtCore import Qt

from app.config.defaults import (
    WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT, APP_NAME, BACKGROUND_COLOR,
)
from app.config.settings import Settings
from app.widgets.status_bar import TopBar
from app.widgets.create_panel import CreatePanel
from app.widgets.edit_panel import EditPanel
from app.widgets.settings_dialog import SettingsDialog

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Root application window.

    Hosts the TopBar, CreatePanel (left), and EditPanel (right).
    Wires signals between widgets. Ollama connectivity logic added Phase 2.
    """

    def __init__(self, settings: Settings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._settings = settings
        self._build_ui()
        self._connect_signals()
        self._apply_styles()

    def _build_ui(self) -> None:
        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)

        central = QWidget()
        self.setCentralWidget(central)

        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Top bar
        self._top_bar = TopBar()
        self._top_bar.setFixedHeight(48)
        root_layout.addWidget(self._top_bar)

        # Two-panel splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)
        splitter.setChildrenCollapsible(False)

        self._create_panel = CreatePanel(self._settings)
        self._edit_panel = EditPanel(self._settings)

        splitter.addWidget(self._create_panel)
        splitter.addWidget(self._edit_panel)
        splitter.setSizes([500, 500])

        root_layout.addWidget(splitter)

    def _connect_signals(self) -> None:
        self._top_bar.settings_requested.connect(self._open_settings)
        # TODO: Phase 2 — wire top_bar.model_changed, Ollama worker signals
        # TODO: Phase 3 — wire create_panel.generate_requested to generate worker
        # TODO: Phase 4 — wire edit_panel.save_requested to manipulate worker

    def _apply_styles(self) -> None:
        self.setStyleSheet(f"QMainWindow {{ background-color: {BACKGROUND_COLOR}; }}")

    def _open_settings(self) -> None:
        dialog = SettingsDialog(self._settings, parent=self)
        dialog.exec()
        logger.info("Settings dialog closed")
```

- [ ] **Step 3: Run tests**

```bash
python -m pytest tests/test_widgets.py -v
```

Expected: all tests PASSED.

- [ ] **Step 4: Commit**

```bash
git add simplicitor/app/main_window.py tests/test_widgets.py
git commit -m "feat: MainWindow — assembles TopBar, CreatePanel, EditPanel with splitter"
```

---

### Task 12: Entry Point, Stub Modules, and System Prompts

**Files:**
- Create: `simplicitor/main.py`
- Create: all stub worker/service/generator/parser modules
- Create: all four system prompt `.txt` files

- [ ] **Step 1: Write `main.py`**

```python
# simplicitor/main.py
import sys
from pathlib import Path

# Make the simplicitor/ directory importable as the package root
sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont

from app.config.defaults import APP_NAME, APP_FONT_FAMILY, FONT_SIZE_BODY_PT
from app.config.settings import Settings
from app.utils.logging_setup import setup_logging
from app.main_window import MainWindow


def _app_config_dir() -> Path:
    """Return the per-user config directory for Simplicitor settings."""
    # Windows: %APPDATA%\Simplicitor
    appdata = Path.home() / "AppData" / "Roaming" / "Simplicitor"
    appdata.mkdir(parents=True, exist_ok=True)
    return appdata


def main() -> None:
    settings = Settings(_app_config_dir())
    setup_logging(settings.logs_dir)

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setFont(QFont(APP_FONT_FAMILY, FONT_SIZE_BODY_PT))

    window = MainWindow(settings)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Write stub workers**

`simplicitor/app/workers/ollama_worker.py`:
```python
# simplicitor/app/workers/ollama_worker.py
# TODO: Phase 2 — implement Ollama connection polling
from PySide6.QtCore import QThread, Signal


class OllamaWorker(QThread):
    """Polls Ollama connectivity every 5 seconds.

    Signals wired in Phase 2.
    """

    connection_established = Signal(list, str)  # models, current_model
    connection_lost = Signal()

    def run(self) -> None:  # noqa: D102
        pass  # Phase 2
```

`simplicitor/app/workers/generate_worker.py`:
```python
# simplicitor/app/workers/generate_worker.py
# TODO: Phase 3 — implement file generation worker
from PySide6.QtCore import QThread, Signal


class GenerateWorker(QThread):
    """Runs LLM generation and file writing on a background thread."""

    generation_complete = Signal(str)  # output file path
    generation_failed = Signal(str)    # user-friendly error message

    def __init__(self, file_type: str, save_path: str, prompt: str, model: str) -> None:
        super().__init__()
        self.file_type = file_type
        self.save_path = save_path
        self.prompt = prompt
        self.model = model

    def run(self) -> None:  # noqa: D102
        pass  # Phase 3
```

`simplicitor/app/workers/manipulate_worker.py`:
```python
# simplicitor/app/workers/manipulate_worker.py
# TODO: Phase 4 — implement file manipulation worker
from PySide6.QtCore import QThread, Signal


class ManipulateWorker(QThread):
    """Runs LLM manipulation and file write-back on a background thread."""

    manipulation_complete = Signal(str, str)  # saved_path, backup_path
    manipulation_failed = Signal(str)          # user-friendly error message

    def __init__(self, file_path: str, prompt: str, model: str) -> None:
        super().__init__()
        self.file_path = file_path
        self.prompt = prompt
        self.model = model

    def run(self) -> None:  # noqa: D102
        pass  # Phase 4
```

- [ ] **Step 3: Write stub services**

`simplicitor/app/services/ollama_client.py`:
```python
# simplicitor/app/services/ollama_client.py
# TODO: Phase 2 — implement REST calls
from dataclasses import dataclass, field


@dataclass
class OllamaStatus:
    connected: bool = False
    models: list[str] = field(default_factory=list)
    current_model: str = ""


class OllamaClient:
    """HTTP client for the Ollama local API."""

    def __init__(self, base_url: str) -> None:
        self._base_url = base_url

    def get_status(self) -> OllamaStatus:
        """Return connectivity status and installed models."""
        return OllamaStatus()  # Phase 2
```

`simplicitor/app/services/file_generator.py`:
```python
# simplicitor/app/services/file_generator.py
# TODO: Phase 3
class FileGenerator:
    """Orchestrates prompt → LLM → parse → file write pipeline."""
    pass
```

`simplicitor/app/services/file_manipulator.py`:
```python
# simplicitor/app/services/file_manipulator.py
# TODO: Phase 4
class FileManipulator:
    """Orchestrates file read → LLM → parse → write-back pipeline."""
    pass
```

`simplicitor/app/services/backup_service.py`:
```python
# simplicitor/app/services/backup_service.py
# TODO: Phase 4
class BackupService:
    """Creates one backup per file on first manipulation."""
    pass
```

- [ ] **Step 4: Write stub generators and parser**

`simplicitor/app/generators/word_generator.py`:
```python
# TODO: Phase 3
class WordGenerator:
    pass
```

`simplicitor/app/generators/excel_generator.py`:
```python
# TODO: Phase 3
class ExcelGenerator:
    pass
```

`simplicitor/app/generators/pptx_generator.py`:
```python
# TODO: Phase 3
class PptxGenerator:
    pass
```

`simplicitor/app/parsers/llm_response_parser.py`:
```python
# TODO: Phase 3
class LlmResponseParser:
    pass
```

- [ ] **Step 5: Write system prompt files**

`simplicitor/prompts/system_word.txt`:
```
You are a document generation assistant. The user will describe a Word document they need.

Return ONLY valid JSON matching this exact schema — no explanation, no markdown fences:
{
  "title": "string",
  "sections": [
    {
      "heading": "string",
      "content": "string — paragraphs separated by \\n\\n",
      "type": "text|table|list"
    }
  ]
}

Rules:
- heading may be empty string for sections without a heading
- type must be exactly one of: text, table, list
- Do not include styling or formatting instructions in the JSON values
- The user may request styling (colors, fonts); acknowledge by using descriptive heading text where relevant, but keep JSON values as plain text
```

`simplicitor/prompts/system_excel.txt`:
```
You are a spreadsheet generation assistant. The user will describe an Excel spreadsheet they need.

Return ONLY valid JSON matching this exact schema — no explanation, no markdown fences:
{
  "sheet_name": "string",
  "headers": ["string"],
  "rows": [["cell_value"]],
  "formulas": [{"cell": "B10", "formula": "=SUM(B2:B9)"}]
}

Rules:
- headers is an array of column header strings
- rows is an array of arrays; each inner array must have the same length as headers
- formulas is optional; use empty array [] if no formulas are needed
- All cell values should be strings (numbers will be converted by the app)
```

`simplicitor/prompts/system_pptx.txt`:
```
You are a presentation generation assistant. The user will describe a PowerPoint presentation they need.

Return ONLY valid JSON matching this exact schema — no explanation, no markdown fences:
{
  "title": "string",
  "slides": [
    {
      "title": "string",
      "bullets": ["string"],
      "type": "title|content|section"
    }
  ]
}

Rules:
- First slide must be type "title"
- Section divider slides use type "section" with empty bullets array
- Content slides use type "content"
- bullets may be empty array for title and section slides
- Keep bullet points concise (one line each)
```

`simplicitor/prompts/system_manipulate.txt`:
```
You are a document editing assistant. You will receive the current text content of a file and an instruction from the user.

Apply the requested changes and return the modified content.

Rules:
- Return ONLY the modified file content — no explanation, no preamble
- Preserve the overall structure of the document
- Apply only the changes the user requested; leave everything else unchanged
- If asked to summarize or extract information, return the result as clean plain text
- If the instruction is unclear, make a reasonable interpretation and apply it
```

- [ ] **Step 6: Commit**

```bash
git add simplicitor/main.py
git add simplicitor/app/workers/ simplicitor/app/services/
git add simplicitor/app/generators/ simplicitor/app/parsers/
git add simplicitor/prompts/
git commit -m "feat: entry point, stub workers/services/generators/parser, system prompts"
```

---

### Task 13: Smoke Test — App Launches

**Files:**
- Modify: `tests/test_widgets.py`

- [ ] **Step 1: Add the launch smoke test**

Append to `tests/test_widgets.py`:

```python
def test_app_opens_main_window(qtbot, tmp_path) -> None:
    """Verify the full MainWindow can be constructed and shown without error."""
    settings = Settings(tmp_path)
    window = MainWindow(settings)
    qtbot.addWidget(window)
    window.show()
    assert window.isVisible()
    assert window.windowTitle() == "Simplicitor"
```

- [ ] **Step 2: Run the full test suite**

```bash
cd C:/Repos/Simplicitor
python -m pytest tests/ -v
```

Expected: all tests PASSED, zero failures.

- [ ] **Step 3: Manual smoke test — launch the app**

```bash
python simplicitor/main.py
```

Expected: Simplicitor window appears with two panels (Create left, Edit right), red dot in top bar showing "AI engine not connected", settings gear opens a dialog.

- [ ] **Step 4: Final commit**

```bash
git add tests/test_widgets.py
git commit -m "test: smoke test — MainWindow opens, title correct, window visible"
```

---

## Phase 1 Complete

**Checklist before calling Phase 1 done:**
- [ ] `python -m pytest tests/ -v` — all tests pass
- [ ] `python simplicitor/main.py` — window opens without errors
- [ ] Settings gear opens the dialog and saves paths
- [ ] Both panels visible with all UI controls present
- [ ] Generate and Save buttons are disabled (correct — Ollama not connected)
- [ ] No import errors in any module

**Next phase:** Phase 2 — Ollama integration (connection polling, model selector, auto-reconnect).
