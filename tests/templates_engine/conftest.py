# tests/templates_engine/conftest.py
# Override the root conftest's autouse Qt fixture — templates_engine tests have no UI.
from pathlib import Path

import pytest
from pptx import Presentation


@pytest.fixture(autouse=True)
def auto_show_widgets():
    yield


@pytest.fixture
def tmp_template(tmp_path):
    """Temp dir with a default Presentation saved as template.pptx and render_manifest.yaml."""
    Presentation().save(str(tmp_path / "template.pptx"))
    src = Path(__file__).parent / "fixtures" / "render_manifest.yaml"
    (tmp_path / "manifest.yaml").write_bytes(src.read_bytes())
    return tmp_path


@pytest.fixture
def tiny_png(tmp_path):
    """A file at tmp_path/test_image.png. Content is not a valid image; tests mock insert_picture."""
    path = tmp_path / "test_image.png"
    path.write_bytes(b"PNG")
    return path
