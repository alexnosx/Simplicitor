"""Local desktop requests and caller failures, without launching other applications."""
import os
import subprocess
from pathlib import Path

import pytest

from app.config.settings import Settings


@pytest.mark.parametrize("directory", [False, True])
def test_open_local_path_round_trips_unicode_and_spaces(tmp_path, monkeypatch, directory):
    from app.utils import desktop
    path = tmp_path / "Pilot É 100%.docx"
    path.mkdir() if directory else path.write_bytes(b"synthetic")
    calls = []
    monkeypatch.setattr(desktop.QDesktopServices, "openUrl", lambda url: calls.append(url) or True)
    monkeypatch.chdir(tmp_path)
    assert desktop.open_local_path(Path(path.name))
    assert len(calls) == 1 and calls[0].isLocalFile()
    assert Path(calls[0].toLocalFile()) == path


def test_open_local_path_does_not_request_missing_or_unreadable_targets(tmp_path, monkeypatch):
    from app.utils import desktop
    calls = []
    monkeypatch.setattr(desktop.QDesktopServices, "openUrl", lambda url: calls.append(url) or True)
    assert not desktop.open_local_path(tmp_path / "missing")
    existing = tmp_path / "private.docx"
    existing.write_bytes(b"synthetic")
    monkeypatch.setattr(desktop.os, "access", lambda *args: False)
    assert not desktop.open_local_path(existing)
    assert calls == []


@pytest.mark.parametrize("raises", [False, True])
def test_open_local_path_reports_desktop_refusal_without_logging_path(tmp_path, monkeypatch, caplog, raises):
    from app.utils import desktop
    path = tmp_path / "Jane.docx"
    path.write_bytes(b"synthetic")

    def refuse(url):
        if raises:
            raise OSError("Jane")
        return False

    monkeypatch.setattr(desktop.QDesktopServices, "openUrl", refuse)
    assert not desktop.open_local_path(path)
    assert "Jane" not in caplog.text


@pytest.mark.parametrize("accepted", [True, False])
def test_create_open_action_uses_local_helper_and_retains_visible_failure(qtbot, tmp_path, monkeypatch, accepted):
    from app.widgets import create_screen
    # Block the old route as well, so the RED test cannot launch an application.
    monkeypatch.setattr(os, "startfile", lambda *args: None, raising=False)
    calls, messages = [], []
    monkeypatch.setattr(create_screen, "open_local_path", lambda path: calls.append(path) or accepted,
                        raising=False)
    screen = create_screen.CreateScreen(Settings(tmp_path))
    qtbot.addWidget(screen)
    monkeypatch.setattr(screen, "show_status", lambda *args: messages.append(args))
    saved = str(tmp_path / "saved.docx")
    screen.show_open_file_btn(saved)
    screen._on_open_file()
    assert calls == [saved]
    assert messages == ([] if accepted else [
        ("Could not open the saved file. Open it from its folder.", True)])


@pytest.mark.parametrize("accepted", [True, False])
def test_settings_open_logs_uses_local_helper_and_warns_on_refusal(qtbot, tmp_path, monkeypatch, accepted):
    from PySide6.QtWidgets import QMessageBox
    from app.widgets import settings_dialog
    monkeypatch.setattr(subprocess, "Popen", lambda *args, **kw: None)
    calls, warnings = [], []
    monkeypatch.setattr(settings_dialog, "open_local_path", lambda path: calls.append(path) or accepted,
                        raising=False)
    monkeypatch.setattr(QMessageBox, "warning", lambda parent, title, message:
                        warnings.append(message) or QMessageBox.StandardButton.Ok)
    dialog = settings_dialog.SettingsDialog(Settings(tmp_path))
    qtbot.addWidget(dialog)
    dialog._open_logs_folder()
    assert calls == [dialog._logs_edit.text()]
    assert warnings == ([] if accepted else [
        "Could not open the logs folder. Open it from the path shown in Settings."])
