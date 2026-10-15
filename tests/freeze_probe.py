"""Opt-in freeze investigation, loaded with ``-p tests.freeze_probe`` on Python 3.12.

Observe original code objects with sys.monitoring, preserving Qt's registered slots.
Only identifiers, lifetimes and test names are recorded, never document arguments.
"""
from collections import Counter
import ctypes
from ctypes import wintypes
import gc
import json
import os
from pathlib import Path
import sys
import threading
import time
import weakref

import pytest


_PROBE = None
_THREAD_NAMES = ("_ollama_thread", "_extraction_thread", "_edit_thread", "_generate_thread",
                 "_template_thread", "_manipulate_thread")
_KERNEL = None
_OPEN = open  # Failure-injection tests deliberately monkeypatch Path.write_text.


def write_json(path, value):
    """Keep observer output independent of application filesystem failure injection."""
    with _OPEN(path, "w", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")


class _ThreadEntry(ctypes.Structure):
    _fields_ = [("size", wintypes.DWORD), ("usage", wintypes.DWORD),
                ("tid", wintypes.DWORD), ("pid", wintypes.DWORD),
                ("base", wintypes.LONG), ("delta", wintypes.LONG),
                ("flags", wintypes.DWORD)]


def pytest_addoption(parser):
    """Keep both repetition and observation opt-in, with no new dependency."""
    group = parser.getgroup("freeze investigation")
    group.addoption("--freeze-repeat", type=int, default=1)
    group.addoption("--freeze-trace", action="store_true")
    group.addoption("--freeze-output", type=Path)


@pytest.fixture(autouse=True)
def _freeze_iteration(request):
    return getattr(request, "param", 0)


def pytest_generate_tests(metafunc):
    count = metafunc.config.getoption("--freeze-repeat")
    if count > 1:
        metafunc.parametrize("_freeze_iteration", range(count))


def pytest_collection_modifyitems(items):
    # Repeat whole selections in original order, rather than exhausting one test first.
    items.sort(key=lambda item: getattr(item, "callspec", None).params.get(
        "_freeze_iteration", 0) if hasattr(item, "callspec") else 0)


def native_threads():
    """Read this process's Windows thread IDs without suspending or altering any thread."""
    if sys.platform != "win32":
        return []

    global _KERNEL
    if _KERNEL is None:
        _KERNEL = ctypes.WinDLL("kernel32", use_last_error=True)
        _KERNEL.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
        _KERNEL.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
        _KERNEL.Thread32First.argtypes = _KERNEL.Thread32Next.argtypes = [
            wintypes.HANDLE, ctypes.POINTER(_ThreadEntry)]
        _KERNEL.Thread32First.restype = _KERNEL.Thread32Next.restype = wintypes.BOOL
        _KERNEL.CloseHandle.argtypes = [wintypes.HANDLE]
        _KERNEL.CloseHandle.restype = wintypes.BOOL
    kernel = _KERNEL
    handle = kernel.CreateToolhelp32Snapshot(4, 0)  # TH32CS_SNAPTHREAD
    if handle == ctypes.c_void_p(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    found = []
    try:
        entry = _ThreadEntry()
        entry.size = ctypes.sizeof(entry)
        valid = kernel.Thread32First(handle, ctypes.byref(entry))
        while valid:
            if entry.pid == os.getpid():
                found.append(entry.tid)
            valid = kernel.Thread32Next(handle, ctypes.byref(entry))
    finally:
        kernel.CloseHandle(handle)
    return sorted(found)


class Probe:
    """Observe thread affinity without replacing a result slot or connecting its signals."""

    def __init__(self, config):
        self.directory = config.getoption("--freeze-output")
        self.directory.mkdir(parents=True, exist_ok=True)
        self.trace = config.getoption("--freeze-trace")
        self.node = "<session>"
        self.started = time.monotonic()
        self.phase = "session"
        self.sequence = 0
        self.lock = threading.Lock()
        self.fd = os.open(self.directory / "events.jsonl", os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        self.counts = Counter()
        self.affinity = Counter()
        self.threads = {}
        self.codes = {}
        self.violations = []
        self.outcomes = Counter()
        self.tests = 0
        self.main_ident = threading.get_ident()
        self.tool = None
        self.original_init = None
        self.write("session", python=sys.version, platform=sys.platform,
                   trace=self.trace, repeat=config.getoption("--freeze-repeat"),
                   main_ident=self.main_ident, pid=os.getpid(),
                   qpa=os.environ.get("QT_QPA_PLATFORM"))

    def write(self, event, **data):
        payload = {"event": event, "time": time.monotonic(), "test": self.node, **data}
        raw = (json.dumps(payload, separators=(",", ":")) + "\n").encode("utf-8")
        # No Qt calls or application locks are made while holding the output lock.
        with self.lock:
            os.write(self.fd, raw)

    def state(self, active):
        write_json(self.directory / "state.json", {
            "active": active, "test": self.node, "phase": self.phase,
            "started": self.started, "completed": self.tests,
        })

    def enable(self):
        if not self.trace:
            return
        if not hasattr(sys, "monitoring"):
            raise pytest.UsageError("Thread observation requires the installed Python 3.12 venv.")
        from PySide6.QtCore import QThread
        from app.main_window import MainWindow
        from app.widgets.create_screen import CreateScreen
        from app.widgets.edit_screen import EditScreen
        from app.widgets.step_indicator import StepIndicator
        from app.workers.edit_worker import EditWorker
        from app.workers.extraction_worker import ExtractionWorker
        from app.workers.generate_worker import GenerateWorker
        from app.workers.manipulate_worker import ManipulateWorker
        from app.workers.ollama_worker import OllamaWorker
        from app.workers.template_worker import TemplateGenerateWorker

        for cls in (MainWindow, CreateScreen, EditScreen, StepIndicator,
                    EditWorker, ExtractionWorker, GenerateWorker, ManipulateWorker,
                    OllamaWorker, TemplateGenerateWorker):
            for name, function in vars(cls).items():
                if not hasattr(function, "__code__"):
                    continue
                gui = (cls is MainWindow and name in ("_on_candidate_ready", "_on_edit_opened"))
                gui = gui or (cls in (CreateScreen, EditScreen)
                              and (name.startswith("show_") or name == "_show"))
                gui = gui or (cls is StepIndicator and name == "set_current")
                worker = cls in (EditWorker, ExtractionWorker, GenerateWorker, ManipulateWorker,
                                 OllamaWorker, TemplateGenerateWorker)
                worker = worker and name in ("run", "setup", "stop", "_poll", "request_model_params")
                if gui or worker:
                    self.codes[function.__code__] = (function.__qualname__, gui)

        self.original_init = QThread.__init__
        probe = self

        def observed_init(thread, *args, **kwargs):
            probe.original_init(thread, *args, **kwargs)
            probe.register(thread)

        # Weak bookkeeping only: do not wrap start/run/slots or add signal connections.
        QThread.__init__ = observed_init
        mon = sys.monitoring
        self.tool = next((i for i in (3, 4, 2, 5, 1, 0) if mon.get_tool(i) is None), None)
        if self.tool is None:
            raise pytest.UsageError("No free sys.monitoring tool ID.")
        mon.use_tool_id(self.tool, "simplicitor-freeze-investigation")
        mon.register_callback(self.tool, mon.events.PY_START, self.enter)
        mon.register_callback(self.tool, mon.events.PY_RETURN, self.leave)
        for code in self.codes:
            mon.set_local_events(self.tool, code, mon.events.PY_START | mon.events.PY_RETURN)

    def register(self, thread):
        import shiboken6
        pointer = shiboken6.getCppPointer(thread)[0]
        self.sequence += 1
        item = {"serial": self.sequence, "cpp": pointer, "created_by": self.node,
                "ref": weakref.ref(thread), "native_ids": set(), "workers": set()}
        self.threads[pointer] = item
        self.write("qthread_created", serial=item["serial"], cpp=pointer)
        return item

    def qt_snapshot(self):
        import shiboken6
        rows = []
        for key, entry in list(self.threads.items()):
            thread = entry["ref"]()
            if thread is None or not shiboken6.isValid(thread):
                self.threads.pop(key, None)
                continue
            rows.append({k: v for k, v in entry.items() if k not in ("ref", "native_ids", "workers")}
                        | {"running": thread.isRunning(), "finished": thread.isFinished(),
                           "native_ids": sorted(entry["native_ids"]),
                           "workers": sorted(entry["workers"])})
        return rows

    def snapshot(self, event):
        if self.trace:
            self.write(event, qt=self.qt_snapshot(), native=native_threads(),
                       python=[{"ident": t.ident, "native_id": t.native_id,
                                "name": t.name, "dummy": type(t).__name__ == "_DummyThread"}
                               for t in threading.enumerate()], gc_enabled=gc.isenabled())

    def enter(self, code, _offset):
        from PySide6.QtCore import QCoreApplication, QThread
        import shiboken6
        label, gui = self.codes[code]
        frame = sys._getframe(1)
        owner = frame.f_locals.get("self")
        current = QThread.currentThread()
        qt_id = shiboken6.getCppPointer(current)[0]
        app = QCoreApplication.instance()
        gui_id = shiboken6.getCppPointer(app.thread())[0] if app is not None else None
        ident, native = threading.get_ident(), threading.get_native_id()
        self.counts[label] += 1
        data = {"method": label, "qt": qt_id, "gui_qt": gui_id, "ident": ident,
                "native": native, "gc_enabled": gc.isenabled()}
        if gui:
            ok = qt_id == gui_id and ident == self.main_ident
            self.affinity["gui" if ok else "wrong"] += 1
            if not ok:
                self.violations.append({"test": self.node, **data})
            # The caller reveals direct test setup without touching QObject.sender().
            caller = frame.f_back
            data["caller"] = caller.f_code.co_qualname if caller else None
            data["direct_test"] = bool(caller and "/tests/" in caller.f_code.co_filename.replace("\\", "/"))
            if label in ("MainWindow._on_candidate_ready", "MainWindow._on_edit_opened"):
                data["owned"] = {name: {"cpp": shiboken6.getCppPointer(thread)[0],
                                        "running": thread.isRunning()}
                                 for name in _THREAD_NAMES
                                 if (thread := getattr(owner, name, None)) is not None
                                 and shiboken6.isValid(thread)}
                data["native_threads"] = native_threads()
            self.write("gui_enter", **data)
            assert ok, f"{label} ran outside the GUI thread"
        else:
            if qt_id != gui_id:
                entry = self.threads.get(qt_id) or self.register(current)
                entry["native_ids"].add(native)
                entry["workers"].add(type(owner).__name__)
            self.write("worker_enter", **data)

    def leave(self, code, _offset, _result):
        label, gui = self.codes[code]
        self.write("gui_leave" if gui else "worker_leave", method=label,
                   ident=threading.get_ident(), native=threading.get_native_id())

    def finish(self, exitstatus):
        if self.tool is not None:
            from PySide6.QtCore import QThread
            mon = sys.monitoring
            for code in self.codes:
                mon.set_local_events(self.tool, code, 0)
            mon.register_callback(self.tool, mon.events.PY_START, None)
            mon.register_callback(self.tool, mon.events.PY_RETURN, None)
            mon.free_tool_id(self.tool)
            QThread.__init__ = self.original_init
        self.snapshot("session_threads_end")
        summary = {"python": sys.version, "trace": self.trace, "tests": self.tests,
                   "outcomes": dict(self.outcomes), "calls": dict(self.counts),
                   "affinity": dict(self.affinity), "violations": self.violations,
                   "exitstatus": int(exitstatus)}
        write_json(self.directory / "summary.json", summary)
        os.close(self.fd)


def pytest_sessionstart(session):
    global _PROBE
    if session.config.getoption("--freeze-output") is not None:
        _PROBE = Probe(session.config)
        _PROBE.enable()


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_protocol(item):
    if _PROBE is None:
        yield
        return
    probe = _PROBE
    probe.node, probe.started, probe.phase = item.nodeid, time.monotonic(), "setup"
    probe.state(True)
    probe.snapshot("test_start")
    yield
    probe.snapshot("test_end")
    probe.tests += 1
    probe.state(False)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    if _PROBE is not None:
        report = outcome.get_result()
        _PROBE.phase = report.when
        _PROBE.outcomes[f"{report.when}:{report.outcome}"] += 1
        if _PROBE.violations and report.when == "teardown":
            report.outcome = "failed"
            report.longrepr = "Freeze probe observed a GUI-thread affinity violation."


def pytest_runtest_call(item):
    if _PROBE is not None:
        _PROBE.phase = "call"
        _PROBE.state(True)


def pytest_runtest_teardown(item):
    if _PROBE is not None:
        _PROBE.phase = "teardown"
        _PROBE.state(True)


def pytest_sessionfinish(session, exitstatus):
    if _PROBE is not None:
        _PROBE.finish(exitstatus)
