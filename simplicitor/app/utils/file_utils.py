# simplicitor/app/utils/file_utils.py
import re
from pathlib import Path


def sanitize_filename(text: str, max_length: int = 40) -> str:
    """Convert arbitrary text into a safe filename fragment.

    Strips non-alphanumeric characters (except hyphens), collapses
    whitespace/hyphens to underscores, and truncates to max_length.
    Returns 'document' if the result would be empty.
    """
    cleaned = re.sub(r"[^\w\s-]", "", text).strip()
    cleaned = re.sub(r"[\s-]+", "_", cleaned)
    cleaned = cleaned[:max_length]
    return cleaned if cleaned else "document"


def ensure_dir(path: str | Path) -> Path:
    """Create directory and all parents if they don't exist.

    Returns the Path object for the directory.
    """
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p
