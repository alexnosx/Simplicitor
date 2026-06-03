# tests/test_template_worker.py
# Phase K: Tests for TemplateGenerateWorker.
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.parsers.llm_response_parser import ParseError
from app.services.ollama_client import (
    OllamaConnectionError, OllamaGenerationError, OllamaTimeoutError,
)
from app.workers.template_worker import TemplateGenerateWorker
from templates_engine.manifest import load_manifest

FIXTURE_MANIFEST = (
    Path(__file__).parent / "templates_engine" / "fixtures" / "render_manifest.yaml"
)
CONTENT = {"slides": [{"type": "title_slide", "fields": {"title": "My Title"}}]}


@pytest.fixture
def manifest():
    return load_manifest(FIXTURE_MANIFEST)


def make_worker(manifest, request="A deck", model="llama3", client=None):
    return TemplateGenerateWorker(manifest, request, model, client or MagicMock())


def test_worker_emits_started(qtbot, manifest):
    worker = make_worker(manifest)
    started = []
    worker.started.connect(lambda: started.append(True))
    with patch("templates_engine.pipeline.generate_content", return_value=CONTENT):
        with qtbot.waitSignal(worker.completed, timeout=5000):
            worker.run()
    assert started == [True]


def test_worker_completed_carries_content_and_happy_path_progress(qtbot, manifest):
    def fake(manifest_, messages, model, client=None, progress=None):
        if progress:
            progress("generating")
            progress("validating")
        return CONTENT

    worker = make_worker(manifest)
    phases = []
    worker.progress.connect(phases.append)
    with patch("templates_engine.pipeline.generate_content", side_effect=fake):
        with qtbot.waitSignal(worker.completed, timeout=5000) as blocker:
            worker.run()
    assert phases == ["generating", "validating"]
    assert blocker.args[0] == CONTENT


def test_worker_repair_path_progress_sequence(qtbot, manifest):
    def fake(manifest_, messages, model, client=None, progress=None):
        if progress:
            for label in ("generating", "validating", "repairing", "validating"):
                progress(label)
        return CONTENT

    worker = make_worker(manifest)
    phases = []
    worker.progress.connect(phases.append)
    with patch("templates_engine.pipeline.generate_content", side_effect=fake):
        with qtbot.waitSignal(worker.completed, timeout=5000):
            worker.run()
    assert phases == ["generating", "validating", "repairing", "validating"]


@pytest.mark.parametrize("exc, raw, expect_substr, forbid_substr", [
    (OllamaTimeoutError("read timeout after 60s"), "60s", "timed out", "stopped responding"),
    (OllamaConnectionError("HTTPConnectionPool refused"), "HTTPConnectionPool", "stopped responding", None),
    (OllamaGenerationError("status 500 Internal Server Error"), "500", "unexpected", None),
    (ParseError("Model returned invalid content after repair", details='{"slides": []}'),
     "after repair", "valid slide structure", "parse"),
    (RuntimeError("boom internal traceback detail"), "boom", "went wrong", None),
])
def test_worker_maps_exception_to_friendly_message(
    qtbot, manifest, exc, raw, expect_substr, forbid_substr
):
    worker = make_worker(manifest)
    with patch("templates_engine.pipeline.generate_content", side_effect=exc):
        with qtbot.waitSignal(worker.failed, timeout=5000) as blocker:
            worker.run()
    msg = blocker.args[0]
    assert expect_substr.lower() in msg.lower()
    assert raw not in msg                      # raw exception text / model content never leaks
    if forbid_substr is not None:
        assert forbid_substr.lower() not in msg.lower()
