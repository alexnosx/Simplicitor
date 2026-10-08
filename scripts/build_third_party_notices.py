"""Assemble installed runtime license texts and validate the bundled notice payload."""
import hashlib
from importlib import metadata
import json
from pathlib import Path
import re
import shutil
import ssl
import sys


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _runtime_distributions(root: Path) -> list:
    """Collect installed non-extra dependencies, conservatively including platform markers."""
    pending = [(line.strip(), True) for line in (root / "requirements.txt").read_text().splitlines()
               if line.strip() and not line.lstrip().startswith("#")]
    found = {}
    while pending:
        requirement, required = pending.pop()
        match = re.match(r"[\w.-]+", requirement)
        if not match:
            raise ValueError("Unsupported runtime requirement for notices")
        name = re.sub(r"[-_.]+", "-", match[0]).lower()
        if name in found:
            continue
        try:
            dist = metadata.distribution(name)
        except metadata.PackageNotFoundError:
            if required:
                raise ValueError(f"Missing runtime distribution for notices: {name}") from None
            continue
        found[name] = dist
        for dependency in dist.requires or ():
            marker = dependency.partition(";")[2]
            if not re.search(r"\bextra\b", marker):
                pending.append((dependency, not bool(marker)))
    return [found[name] for name in sorted(found)]


def _copy_licenses(dist, destination: Path) -> list[str]:
    files = []
    for entry in dist.files or ():
        # Include licenses held in a licenses/ directory and separately named notices.
        if not any(re.search(r"licen[cs]e|copying|copyright|notice", part, re.I)
                   for part in entry.parts):
            continue
        source = Path(dist.locate_file(entry))
        if not source.is_file() or source.suffix.lower() in (".py", ".pyc", ".pyd", ".dll"):
            continue
        if ".." in entry.parts:
            raise ValueError("Unexpected runtime notice path")
        target = destination / entry
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        files.append(target.as_posix())
    if not files:
        raise ValueError(f"Missing license texts for notices: {dist.metadata['Name']}")
    return files


def build_notices(root: Path, output: Path) -> None:
    """Copy original license bytes for this build without deleting existing files."""
    source = root / "resources/third_party"
    snapshot = json.loads((source / "qt/sources.json").read_text(encoding="utf-8"))
    if metadata.version("PySide6") != snapshot["qt_version"]:
        raise ValueError("Qt notice snapshot version differs from PySide6; refresh upstream notices")
    for entry in snapshot["files"]:
        if _digest(source / "qt" / entry["file"]) != entry["sha256"]:
            raise ValueError("Upstream Qt notice checksum mismatch")
    shutil.copytree(source, output, dirs_exist_ok=True)
    packages = []
    for dist in _runtime_distributions(root):
        name = re.sub(r"[-_.]+", "-", dist.metadata["Name"]).lower()
        files = _copy_licenses(dist, output / "python" / name)
        packages.append({"name": dist.metadata["Name"], "version": dist.version,
                         "license_files": [Path(p).relative_to(output).as_posix() for p in files]})
    python_license = Path(sys.base_prefix) / "LICENSE.txt"
    (output / "python-runtime").mkdir(exist_ok=True)
    shutil.copyfile(python_license, output / "python-runtime/LICENSE.txt")
    nuitka = metadata.distribution("Nuitka")
    nuitka_files = _copy_licenses(nuitka, output / "nuitka-runtime")
    # Put the runtime terms at a stable, discoverable location as well as preserving metadata paths.
    for path in nuitka_files:
        if Path(path).name in ("LICENSE.txt", "LICENSE-RUNTIME.txt", "NOTICE.txt"):
            shutil.copyfile(path, output / "nuitka-runtime" / Path(path).name)
    inventory = {"python": sys.version.split()[0], "openssl": ssl.OPENSSL_VERSION,
                 "nuitka": nuitka.version, "qt": snapshot["qt_version"], "packages": packages,
                 "files": {p.relative_to(output).as_posix(): _digest(p)
                           for p in sorted(output.rglob("*"))
                           if p.is_file() and p != output / "inventory.json"}}
    (output / "inventory.json").write_text(json.dumps(inventory, indent=2) + "\n", encoding="utf-8")
    validate_notices(output)


def validate_notices(bundle: Path) -> None:
    """Fail packaging when license notices are absent, empty, or changed in transit."""
    required = ("THIRD_PARTY_NOTICES.txt", "inventory.json", "qt/sources.json",
                "qt/qtbase/LICENSES/LGPL-3.0-only.txt", "qt/qtbase/LICENSES/GPL-3.0-only.txt",
                "python-runtime/LICENSE.txt", "nuitka-runtime/LICENSE-RUNTIME.txt",
                "nuitka-runtime/LICENSE.txt", "nuitka-runtime/NOTICE.txt")
    if any(not (bundle / name).is_file() or not (bundle / name).stat().st_size for name in required):
        raise ValueError("Missing or empty third-party notice payload")
    inventory = json.loads((bundle / "inventory.json").read_text(encoding="utf-8"))
    for name, digest in inventory["files"].items():
        path = bundle / name
        if not path.is_file() or _digest(path) != digest:
            raise ValueError("Third-party notice payload checksum mismatch")
    if not inventory["packages"] or any(
        not p["version"] or not p["license_files"] or
        any(name not in inventory["files"] for name in p["license_files"])
        for p in inventory["packages"]
    ):
        raise ValueError("Incomplete third-party notice inventory")
