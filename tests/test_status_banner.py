# tests/test_status_banner.py
import pytest
from pytestqt.qtbot import QtBot

from app.widgets.status_banner import StatusBanner


def test_status_banner_hidden_by_default(qtbot: QtBot) -> None:
    banner = StatusBanner()
    qtbot.addWidget(banner)
    assert not banner.isVisible()


def test_status_banner_shows_message(qtbot: QtBot) -> None:
    banner = StatusBanner()
    qtbot.addWidget(banner)
    banner.show_message("Operation complete", is_error=False)
    assert banner.isVisible()
    assert "Operation complete" in banner.text()


def test_status_banner_shows_error_message(qtbot: QtBot) -> None:
    banner = StatusBanner()
    qtbot.addWidget(banner)
    banner.show_message("Something went wrong", is_error=True)
    assert banner.isVisible()
    assert "Something went wrong" in banner.text()


def test_status_banner_hide_message(qtbot: QtBot) -> None:
    banner = StatusBanner()
    qtbot.addWidget(banner)
    banner.show_message("visible", is_error=False)
    banner.hide_message()
    assert not banner.isVisible()


def test_status_banner_dismiss_button_hides(qtbot: QtBot) -> None:
    banner = StatusBanner()
    qtbot.addWidget(banner)
    banner.show_message("dismiss me", is_error=False)
    banner._dismiss_btn.click()
    assert not banner.isVisible()


def test_status_banner_text_resets_on_new_message(qtbot: QtBot) -> None:
    banner = StatusBanner()
    qtbot.addWidget(banner)
    banner.show_message("first message", is_error=False)
    banner.show_message("second message", is_error=True)
    assert "second message" in banner.text()
    assert "first" not in banner.text()
