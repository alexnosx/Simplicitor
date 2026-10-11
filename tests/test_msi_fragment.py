# tests/test_msi_fragment.py
import xml.etree.ElementTree as ET

import build

NS = {"w": "http://wixtoolset.org/schemas/v4/wxs"}


def _payload(root):
    for relative in ("Simplicitor.exe", "LICENSE", "prompts/system_word.txt",
                     "third_party/qt/LICENSES/LGPL-3.0-only.txt", "empty_parent/child/data.bin"):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"x")
    return root


def test_every_folder_has_one_component_with_hkcu_key_path_and_cleanup(tmp_path):
    payload = _payload(tmp_path / "main.dist")
    tree = ET.fromstring(build.payload_fragment(payload))
    folders = {"."} | {p.relative_to(payload).as_posix() for p in payload.rglob("*") if p.is_dir()}
    components = tree.findall(".//w:ComponentGroup[@Id='Payload']/w:Component", NS)
    assert len(components) == len(folders)
    for component in components:
        keys = component.findall("w:RegistryValue", NS)
        assert len(keys) == 1 and keys[0].get("Root") == "HKCU" and keys[0].get("KeyPath") == "yes"
        assert len(component.findall("w:RemoveFolder", NS)) == 1
        assert all(f.get("KeyPath") in (None, "no") for f in component.findall("w:File", NS))


def test_every_file_appears_once_and_ids_are_unique(tmp_path):
    payload = _payload(tmp_path / "main.dist")
    tree = ET.fromstring(build.payload_fragment(payload))
    sources = [f.get("Source") for f in tree.iter("{%s}File" % NS["w"])]
    expected = sorted("!(bindpath.payload)\\" + p.relative_to(payload).as_posix().replace("/", "\\")
                      for p in payload.rglob("*") if p.is_file())
    assert sorted(sources) == expected
    ids = [e.get("Id") for e in tree.iter() if e.get("Id")]
    assert len(ids) == len(set(ids))
    assert all(len(i) <= 72 for i in ids)


def test_fragment_is_deterministic(tmp_path):
    payload = _payload(tmp_path / "main.dist")
    assert build.payload_fragment(payload) == build.payload_fragment(payload)
