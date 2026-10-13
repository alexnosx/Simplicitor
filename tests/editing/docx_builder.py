"""Hand-written Word packages for editing tests, built on python-docx's default template."""
import io
from pathlib import Path
import re
import zipfile

from docx import Document

FIXTURES = Path(__file__).parent / "fixtures"


def _replace(data: bytes, name: str, content: bytes) -> bytes:
    source = zipfile.ZipFile(io.BytesIO(data))
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as target:
        for info in source.infolist():
            target.writestr(info, content if info.filename == name else source.read(info))
    return out.getvalue()


def build_docx(body: str = "", styles: str = "", settings: str = "", document: bytes | None = None,
               extra: dict[str, bytes] | None = None) -> bytes:
    """A .docx whose body is `body` (w: prefix) followed by the template's sectPr.

    `styles` and `settings` are appended inside w:styles and w:settings; `document`
    replaces word/document.xml entirely; `extra` adds or replaces other parts.
    """
    buffer = io.BytesIO()
    Document().save(buffer)
    data = buffer.getvalue()
    archive = zipfile.ZipFile(io.BytesIO(data))
    if document is None:
        xml = archive.read("word/document.xml")
        section = re.search(rb"<w:sectPr.*</w:sectPr>", xml).group(0)
        document = re.sub(rb"<w:body>.*</w:body>",
                          lambda _: b"<w:body>" + body.encode("utf-8") + section + b"</w:body>",
                          xml, flags=re.S)
    data = _replace(data, "word/document.xml", document)
    if styles:
        xml = archive.read("word/styles.xml").replace(b"</w:styles>", styles.encode() + b"</w:styles>")
        data = _replace(data, "word/styles.xml", xml)
    if settings:
        xml = archive.read("word/settings.xml").replace(b"</w:settings>",
                                                        settings.encode() + b"</w:settings>")
        data = _replace(data, "word/settings.xml", xml)
    for name, content in (extra or {}).items():
        if name in zipfile.ZipFile(io.BytesIO(data)).namelist():
            data = _replace(data, name, content)
        else:
            out = io.BytesIO(data)
            with zipfile.ZipFile(out, "a") as target:
                target.writestr(name, content)
            data = out.getvalue()
    return data


def p(text: str, ppr: str = "", rpr: str = "", attrs: str = "") -> str:
    """One paragraph with one run."""
    props = f"<w:pPr>{ppr}</w:pPr>" if ppr else ""
    run_props = f"<w:rPr>{rpr}</w:rPr>" if rpr else ""
    space = ' xml:space="preserve"' if text != text.strip() else ""
    return f"<w:p{attrs}>{props}<w:r>{run_props}<w:t{space}>{text}</w:t></w:r></w:p>"
