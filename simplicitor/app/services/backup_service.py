# simplicitor/app/services/backup_service.py
import logging
import shutil
from pathlib import Path

from app.config.defaults import BACKUP_SUFFIX

logger = logging.getLogger(__name__)


class BackupService:
    """Creates one-time backups of files before manipulation.

    Enforces the one-backup-per-file rule: if a backup already exists
    at the target path it is returned unchanged.
    """

    def backup_if_needed(self, file_path: Path, backup_dir: Path) -> Path:
        """Copy *file_path* to *backup_dir* if no backup exists yet.

        Backup filename: ``{stem}{BACKUP_SUFFIX}{suffix}``
        (e.g. ``report_backup.docx``).

        Args:
            file_path: Source file to back up.
            backup_dir: Directory in which to store the backup.

        Returns:
            Path to the backup file (newly created or pre-existing).

        Raises:
            OSError: If the directory cannot be created or the file cannot
                be copied.
        """
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup_name = f"{file_path.stem}{BACKUP_SUFFIX}{file_path.suffix}"
        backup_path = backup_dir / backup_name

        if not backup_path.exists():
            shutil.copy2(file_path, backup_path)
            logger.info("Created backup: %s → %s", file_path, backup_path)
        else:
            logger.debug("Backup already exists, skipping: %s", backup_path)

        return backup_path
