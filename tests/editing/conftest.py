"""Fixtures for editing tests."""
from pathlib import Path

import pytest

from tests.editing.docx_builder import build_docx

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def make_docx(tmp_path):
    """Write build_docx(...) to a file and return its path."""
    counter = iter(range(1000))

    def make(*args, name: str | None = None, **kwargs) -> Path:
        path = tmp_path / (name or f"doc-{next(counter)}.docx")
        path.write_bytes(build_docx(*args, **kwargs))
        return path

    return make
