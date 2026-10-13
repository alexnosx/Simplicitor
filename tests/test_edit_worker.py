"""EditWorker runs the real open/propose/save route and emits one terminal signal."""
import json

import pytest

from app.workers.edit_worker import EditSetup, EditWorker
from editing.package import open_document
from tests.editing.docx_builder import build_docx, p


class Client:
    def __init__(self, text="Pay in 45 days.", on_call=None):
        self.text, self.on_call, self.calls = text, on_call, []

    def generate(self, model, prompt, system, **kwargs):
        self.calls.append((model, prompt, kwargs))
        if self.on_call:
            self.on_call()
        return json.dumps({"paragraphs": [self.text]})


@pytest.fixture
def source(tmp_path):
    path = tmp_path / "terms.docx"
    path.write_bytes(build_docx(p("Pay in 30 days.") + p("Keep this.")))
    return path


def _run(qtbot, worker, signal):
    with qtbot.waitSignal(signal) as caught, qtbot.waitSignal(worker.finished):
        worker.run()
    return caught.args


def test_open_emits_document_and_view(qtbot, source):
    worker = EditWorker("open", EditSetup(path=source))
    opened, view = _run(qtbot, worker, worker.opened)
    assert [b.text for b in opened.paragraphs] == ["Pay in 30 days.", "Keep this."]
    assert [b.text for b in view if b.kind == "paragraph"] == ["Pay in 30 days.", "Keep this."]


def test_open_failure_is_plain(qtbot, tmp_path):
    bad = tmp_path / "bad.docx"
    bad.write_bytes(b"nope")
    worker = EditWorker("open", EditSetup(path=bad))
    message, outcome = _run(qtbot, worker, worker.failed)
    assert message == "This Word file could not be read." and outcome == "failed"


def test_propose_then_save(qtbot, source, tmp_path):
    opened = open_document(source)
    client = Client()
    worker = EditWorker("propose", EditSetup(opened=opened, first=0, last=0,
                                             instruction="Use 45 days.", model="m:8b", attempt=1), client)
    candidate, before, after = _run(qtbot, worker, worker.proposed)
    assert [b.text for b in before] == ["Pay in 30 days."] and [b.text for b in after] == ["Pay in 45 days."]
    assert client.calls[0][2]["options"]["seed"] == 1
    target = tmp_path / "terms (edited).docx"
    saver = EditWorker("save", EditSetup(candidate=candidate, destination=target))
    (path,) = _run(qtbot, saver, saver.saved)
    assert path == str(target) and target.read_bytes() == candidate.data
    saver.cancel()
    assert not saver._cancel.is_set()


@pytest.mark.parametrize("setup_change, message", [
    ({"model": ""}, "Open Settings and select an installed local model."),
    ({"instruction": "  "}, "Describe the change in up to 2,000 characters."),
    ({"instruction": "x" * 2001}, "Describe the change in up to 2,000 characters."),
    ({"last": 5}, "Select one or more paragraphs."),
])
def test_propose_refusals_make_no_model_call(qtbot, source, setup_change, message):
    opened = open_document(source)
    values = {"opened": opened, "first": 0, "last": 0, "instruction": "Change.", "model": "m"}
    values.update(setup_change)
    client = Client()
    worker = EditWorker("propose", EditSetup(**values), client)
    assert _run(qtbot, worker, worker.failed)[0] == message
    assert client.calls == []


def test_long_selection_is_refused(qtbot, tmp_path):
    path = tmp_path / "long.docx"
    path.write_bytes(build_docx(p("x" * 6001)))
    worker = EditWorker("propose", EditSetup(opened=open_document(path), instruction="Shorten.", model="m"),
                        Client())
    assert _run(qtbot, worker, worker.failed)[0].startswith("Select a shorter part")


def test_cancel_during_request_discards_the_reply(qtbot, source):
    opened = open_document(source)
    worker = EditWorker("propose", EditSetup(opened=opened, instruction="Change.", model="m"))
    worker._client = Client(on_call=worker.cancel)
    _run(qtbot, worker, worker.cancelled)


def test_unreadable_destination_reaches_the_save_outcome(qtbot, source, tmp_path, monkeypatch):
    from editing import save
    opened = open_document(source)
    worker = EditWorker("propose", EditSetup(opened=opened, instruction="Use 45 days.", model="m"), Client())
    candidate = _run(qtbot, worker, worker.proposed)[0]
    monkeypatch.setattr(save, "destination_state", lambda d: (_ for _ in ()).throw(PermissionError()))
    saver = EditWorker("save", EditSetup(candidate=candidate, destination=tmp_path / "x.docx"))
    message, outcome = _run(qtbot, saver, saver.failed)
    assert outcome == "destination" and message.startswith("The file you chose cannot be read")
