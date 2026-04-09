# tests/test_build_script.py
"""Smoke tests for the Nuitka build script — verify required flags are present."""
from pathlib import Path


BUILD_PY = Path(__file__).parent.parent / "build.py"


def _content() -> str:
    return BUILD_PY.read_text(encoding="utf-8")


def test_build_script_exists() -> None:
    assert BUILD_PY.exists(), "build.py not found at repo root"


def test_build_script_uses_onefile() -> None:
    assert "--onefile" in _content()


def test_build_script_disables_console() -> None:
    # Nuitka 2.x flag
    assert "--windows-console-mode=disable" in _content()


def test_build_script_enables_pyside6_plugin() -> None:
    assert "--enable-plugin=pyside6" in _content()


def test_build_script_includes_prompts_dir() -> None:
    assert "prompts=prompts" in _content()


def test_build_script_references_icon() -> None:
    assert "icon.ico" in _content()


def test_build_script_sets_product_name() -> None:
    assert "Simplicitor" in _content()


def test_build_bat_exists() -> None:
    bat = Path(__file__).parent.parent / "build.bat"
    assert bat.exists(), "build.bat not found at repo root"
