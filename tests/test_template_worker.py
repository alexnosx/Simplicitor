# tests/test_template_worker.py
# Tests for TemplateGenerateWorker (runs the full generate + render pipeline off-thread).
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.parsers.llm_response_parser import ParseError
from app.services.file_manipulator import ManipulationError
from app.services.ollama_client import (
    OllamaConnectionError, OllamaGenerationError, OllamaTimeoutError,
)
from app.workers.template_worker import TemplateGenerateWorker
from templates_engine.manifest import load_manifest

FIXTURE_MANIFEST = (
    Path(__file__).parent / "templates_engine" / "fixtures" / "render_manifest.yaml"
)


@pytest.fixture
def manifest():
    return load_manifest(FIXTURE_MANIFEST)


def make_worker(manifest, tmp_path, request="A deck", model="llama3", client=None):
    return TemplateGenerateWorker(
        manifest,
        str(tmp_path),
        request,
        str(tmp_path / "out.pptx"),
        model,
        client or MagicMock(),
    )


def test_worker_emits_started(qtbot, manifest, tmp_path):
    worker = make_worker(manifest, tmp_path)
    started = []
    worker.started.connect(lambda: started.append(True))
    result = {"path": tmp_path / "out.pptx", "issues": []}
    with patch("templates_engine.pipeline.run", return_value=result):
        with qtbot.waitSignal(worker.completed, timeout=5000):
            worker.run()
    assert started == [True]


def test_worker_completed_carries_path_and_issues(qtbot, manifest, tmp_path):
    out = tmp_path / "out.pptx"
    result = {"path": out, "issues": ["Slide 0, field 'title': text too long."]}
    worker = make_worker(manifest, tmp_path)
    with patch("templates_engine.pipeline.run", return_value=result) as run_mock:
        with qtbot.waitSignal(worker.completed, timeout=5000) as blocker:
            worker.run()
    # pipeline.run is the boundary the worker drives (generate + render in one call).
    assert run_mock.called
    assert blocker.args[0] == str(out)
    assert blocker.args[1] == ["Slide 0, field 'title': text too long."]


@pytest.mark.parametrize("exc, raw, expect_substr, forbid_substr", [
    (OllamaTimeoutError("read timeout after 60s"), "60s", "timed out", "stopped responding"),
    (OllamaConnectionError("HTTPConnectionPool refused"), "HTTPConnectionPool", "stopped responding", None),
    (OllamaGenerationError("status 500 Internal Server Error"), "500", "unexpected", None),
    (ParseError("Model returned invalid content after repair", details='{"slides": []}'),
     "after repair", "valid slide structure", "parse"),
    (ManipulationError("placeholder idx 7 not found /secret/path"),
     "secret", "out of sync", None),
    (ValueError("not a pptx /secret/path"), "secret", "PowerPoint file", None),
    (RuntimeError("boom internal traceback detail"), "boom", "went wrong", None),
])
def test_worker_maps_exception_to_friendly_message(
    qtbot, manifest, tmp_path, exc, raw, expect_substr, forbid_substr
):
    worker = make_worker(manifest, tmp_path)
    with patch("templates_engine.pipeline.run", side_effect=exc):
        with qtbot.waitSignal(worker.failed, timeout=5000) as blocker:
            worker.run()
    msg = blocker.args[0]
    assert expect_substr.lower() in msg.lower()
    assert raw not in msg                      # raw exception text / model content never leaks
    if forbid_substr is not None:
        assert forbid_substr.lower() not in msg.lower()
