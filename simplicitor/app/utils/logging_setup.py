# simplicitor/app/utils/logging_setup.py
import logging
import logging.handlers
from pathlib import Path

from app.config.defaults import LOG_FILE_PREFIX, LOG_BACKUP_COUNT


def setup_logging(log_dir: str) -> None:
    """Configure application-wide logging with daily file rotation.

    Writes to <log_dir>/simplicitor_app.log, rotated at midnight,
    keeping LOG_BACKUP_COUNT days of history.

    Privacy rule: file content and user prompts are NEVER logged.
    Only metadata (timestamps, operation type, status, error details) is logged.
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

    # Console handler: warnings and above only (keeps dev output clean)
    console = logging.StreamHandler()
    console.setLevel(logging.WARNING)
    console.setFormatter(formatter)
    root.addHandler(console)
