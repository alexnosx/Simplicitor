# simplicitor/app/services/backup_service.py
# Phase 4: Backup service
from pathlib import Path


class BackupService:
    """Creates one backup per file on first manipulation (Phase 4).

    Rule: backup is created only on the FIRST manipulation of a file.
    Subsequent manipulations do not overwrite the backup.
    """

    def backup_if_needed(self, file_path: Path, backup_dir: Path) -> Path | None:
        """Create backup if one doesn't exist. Return backup path."""
        return None  # Phase 4
