# simplicitor/app/utils/file_utils.py
import re
import sys
from pathlib import Path


def resource_path(relative: str) -> Path:
    """Resolve a path to a bundled resource that works both in development
    and inside a Nuitka-packaged executable.

    Args:
        relative: Path string relative to the repository root (e.g. 'assets/icons/simplicitor.ico').

    Returns:
        Absolute Path to the resource.
    """
    if getattr(sys, "frozen", False):
        # Nuitka onefile sets this; fall back to the exe directory
        base = Path(sys.executable).parent
    else:
        # In development, the repo root is two levels up from this file:
        # app/utils/file_utils.py -> app/utils -> app -> simplicitor -> <repo>
        base = Path(__file__).resolve().parents[3]
    return base / relative


def truncate_path(path: str, max_chars: int = 60) -> str:
    """Shorten a path for display, keeping the start and end visible.

    Args:
        path: The full file path string to shorten.
        max_chars: Maximum character length of the returned string.

    Returns:
        Truncated path with ellipsis in the middle if it exceeds max_chars.
    """
    if len(path) <= max_chars:
        return path
    keep = (max_chars - 3) // 2
    return f"{path[:keep]}...{path[-keep:]}"


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
