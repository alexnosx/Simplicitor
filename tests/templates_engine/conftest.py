# tests/templates_engine/conftest.py
# Override the root conftest's autouse Qt fixture — templates_engine tests have no UI.
import pytest


@pytest.fixture(autouse=True)
def auto_show_widgets():
    yield
