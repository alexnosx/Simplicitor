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

    Manages four directory paths: generated_dir, uploads_dir, backups_dir,
    and logs_dir. All default to subfolders under ~/Documents/Simplicitor/
    on first run.
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
