"""Build command and real archive/inventory contracts, without recompiling in pytest."""
import hashlib
import importlib.util
import json
import shutil
from pathlib import Path
from types import SimpleNamespace
from zipfile import ZipFile

import pytest

SPEC = importlib.util.spec_from_file_location("simplicitor_build", Path(__file__).parents[1] / "build.py")
build = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(build)


@pytest.fixture
def payload(tmp_path, monkeypatch):
    monkeypatch.setattr(build, "DIST_DIR", tmp_path / "dist")
    monkeypatch.setattr(build, "ICON", tmp_path / "icon.ico")
    build.ICON.write_bytes(b"test icon")
    monkeypatch.setenv("NUITKA_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setattr(shutil, "which", lambda name: str(tmp_path / "makensis.exe"))
    return tmp_path / "dist" / "standalone" / "main.dist"


def make_payload(payload):
    files = {
        "Simplicitor.exe": b"compiled application",
        "prompts/system_word.txt": b"word prompt",
        "prompts/system_excel.txt": b"excel prompt",
        "prompts/system_pptx.txt": b"pptx prompt",
        "templates/pptx_default.pptx": b"default template",
        "templates_engine/builtin/business_pitch/manifest.yaml": b"pitch",
        "templates_engine/builtin/business_pitch/template.pptx": b"pitch pptx",
        "templates_engine/builtin/technical_overview/manifest.yaml": b"technical",
        "templates_engine/builtin/technical_overview/template.pptx": b"technical pptx",
        "assets/icons/simplicitor.ico": b"icon",
        "PySide6/Qt6Core.dll": b"runtime",
    }
    for name, data in files.items():
        path = payload / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    return files


NSIS_SCRIPT = ('Section "Uninstall"\n  Delete "$INSTDIR\\uninstall.exe"\n'
               '  RMDir /r "$INSTDIR"\nSectionEnd\n')


def make_script(payload):
    script = payload.parent / "main.installer-build" / "installer.nsi"
    script.parent.mkdir(parents=True, exist_ok=True)
    script.write_text(NSIS_SCRIPT)
    return script


def test_corrected_uninstall_removes_only_packaged_files_and_empty_directories(tmp_path):
    payload = tmp_path / "payload"
    (payload / "prompts").mkdir(parents=True)
    (payload / "Simplicitor.exe").write_bytes(b"exe")
    (payload / "prompts" / "word.txt").write_text("prompt")
    corrected = build.correct_uninstall(NSIS_SCRIPT, payload)
    assert corrected.splitlines() == [
        'Section "Uninstall"', '  Delete "$INSTDIR\\uninstall.exe"',
        '  Delete "$INSTDIR\\Simplicitor.exe"',
        '  Delete "$INSTDIR\\prompts\\word.txt"',
        '  RMDir "$INSTDIR\\prompts"', '  RMDir "$INSTDIR"', 'SectionEnd',
    ]
    assert "/r" not in corrected and "*" not in corrected
    assert "Documents" not in corrected and "settings.json" not in corrected


@pytest.mark.parametrize("script", [NSIS_SCRIPT.replace('RMDir /r', 'RMDir /R'),
                                    NSIS_SCRIPT.replace('  RMDir /r "$INSTDIR"\n', ''),
                                    NSIS_SCRIPT + NSIS_SCRIPT])
def test_unexpected_nuitka_uninstall_script_fails_closed(tmp_path, script):
    with pytest.raises(ValueError, match="uninstall"):
        build.correct_uninstall(script, tmp_path)


def test_build_produces_matching_portable_payload_and_installer(payload, monkeypatch):
    captured = []

    def compile_app(command, *, cwd):
        captured.append((command, cwd))
        make_payload(payload)
        if command[-1] == "main.py":
            make_script(payload)
        (build.DIST_DIR / "Simplicitor-setup.exe").write_bytes(b"NSIS installer")
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(build.subprocess, "run", compile_app)
    assert build.main() == 0
    command, cwd = captured[0]
    assert len(captured) == 2
    assert captured[1][0][1] == "/V2"
    assert 'RMDir /r' not in Path(captured[1][0][-1]).read_text()
    assert "--mode=standalone" in command and "--onefile" not in command
    assert "--windows-create-installer" in command
    assert "--windows-installer-mode=user" in command
    assert "--windows-installer-shortcuts=desktop,start-menu" in command
    assert "--windows-installer-no-user-change-install-dir" in command
    assert "--enable-plugin=pyside6" in command and "--windows-console-mode=disable" in command
    assert "--include-data-dir=prompts=prompts" in command
    assert "--include-data-dir=templates_engine/builtin=templates_engine/builtin" in command
    assert command[-1] == "main.py" and cwd == build.SIMPLICITOR_DIR
    with ZipFile(build.DIST_DIR / "Simplicitor-portable.zip") as archive:
        contents = {name.removeprefix("Simplicitor/"): archive.read(name)
                    for name in archive.namelist()}
    assert contents == {p.relative_to(payload).as_posix(): p.read_bytes()
                        for p in payload.rglob("*") if p.is_file()}
    manifest = json.loads((build.DIST_DIR / "SHA256SUMS.json").read_text())
    assert manifest["payload"]["Simplicitor.exe"] == hashlib.sha256(b"compiled application").hexdigest()
    for name in ("Simplicitor-setup.exe", "Simplicitor-portable.zip"):
        assert manifest["artifacts"][name] == hashlib.sha256((build.DIST_DIR / name).read_bytes()).hexdigest()


@pytest.mark.parametrize("missing", ["Simplicitor.exe", "prompts/system_word.txt",
                                    "templates/pptx_default.pptx",
                                    "templates_engine/builtin/business_pitch/template.pptx",
                                    "assets/icons/simplicitor.ico", "installer"])
def test_incomplete_build_fails_without_a_portable_archive(payload, monkeypatch, missing):
    def incomplete(*args, **kwargs):
        make_payload(payload)
        make_script(payload)
        if missing != "installer":
            (payload / missing).unlink()
            (build.DIST_DIR / "Simplicitor-setup.exe").write_bytes(b"installer")
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(build.subprocess, "run", incomplete)
    assert build.main() != 0
    assert not (build.DIST_DIR / "Simplicitor-portable.zip").exists()


def test_compiler_failure_is_propagated(payload, monkeypatch):
    monkeypatch.setattr(build.subprocess, "run", lambda *a, **k: SimpleNamespace(returncode=7))
    assert build.main() == 7
    assert not (build.DIST_DIR / "Simplicitor-portable.zip").exists()


def test_missing_icon_fails_before_compilation(payload, monkeypatch):
    build.ICON.unlink()
    monkeypatch.setattr(build.subprocess, "run", lambda *a, **k: pytest.fail("must not compile"))
    assert build.main() != 0


def test_unsafe_installer_is_removed_if_correction_cannot_be_applied(payload, monkeypatch):
    def changed_template(*args, **kwargs):
        make_payload(payload)
        make_script(payload).write_text(NSIS_SCRIPT.replace('RMDir /r', 'RMDir /R'))
        (build.DIST_DIR / "Simplicitor-setup.exe").write_bytes(b"unsafe installer")
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(build.subprocess, "run", changed_template)
    assert build.main() != 0
    assert not (build.DIST_DIR / "Simplicitor-setup.exe").exists()
    assert not (build.DIST_DIR / "Simplicitor-portable.zip").exists()


def test_cached_nsis_selects_nuitkas_root_entry_not_duplicate_bin(payload, monkeypatch):
    import os
    monkeypatch.setattr(shutil, "which", lambda name: None)
    root = Path(os.environ["NUITKA_CACHE_DIR"]) / "downloads/makensis/3.11/nsis-3.11"
    (root / "Bin").mkdir(parents=True)
    (root / "makensis.exe").write_bytes(b"NSIS entry")
    (root / "Bin/makensis.exe").write_bytes(b"NSIS binary")
    make_payload(payload)
    make_script(payload)
    installer = build.DIST_DIR / "Simplicitor-setup.exe"
    installer.write_bytes(b"original")
    captured = []

    def compile_corrected(command, **kwargs):
        captured.append(command)
        installer.write_bytes(b"corrected")
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(build.subprocess, "run", compile_corrected)
    build.rebuild_installer(payload, installer)
    assert captured[0][0] == str(root / "makensis.exe")
    assert installer.read_bytes() == b"corrected"
