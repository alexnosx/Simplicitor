# Intermittent Qt test freeze investigation

Date: 2026-10-15. Baseline: `6f48dc8a38ff0d3c680f3a9636e9bafa1a888643`.
Branch: `investigate/test-freeze`. Application code, dependencies, LICENSE and
release records are unchanged. All inputs were synthetic and inference was mocked.

## Finding

**Reproduced. A native Qt/Python lock inversion was found. This is an
application-reachable lifetime race, not an established test-only defect.**
The actual freezes were measured in offscreen tests on CPython 3.12.14 with
PySide6/Qt 6.11.2. Normal interactive Windows operation was not exercised, so its
frequency, and whether the historical hosted freezes have exactly this cause,
are not established.

Two target loops with slot/thread tracing disabled froze with the main-thread
GC fixture present:

1. Cycle 36, after 143 completed cases: opening a new document, in
   `StepIndicator.set_current -> EditScreen._show -> show_opened ->
   MainWindow._on_edit_opened`. The test was waiting for the real open worker to
   finish. Its direct stale-result call on the next line had **not run**.
2. Cycle 43, after 168 completed cases: the extraction rerun test, in
   `StepIndicator.set_current -> CreateScreen.show_candidate ->
   MainWindow._on_candidate_ready`. The fixture disables discovery, so there was
   no Ollama worker in this test.

Each freeze produced pytest's built-in 60-second all-thread dump. The owning
runner stopped only its own pytest process after 75 seconds without test
completion. It did not change, retry or skip the failed test in that process.

## Native evidence and cause

The second freeze also has a native stack capture, obtained with the existing
Windows DbgHelp DLL through ctypes. No debugger, dependency or symbol package was
installed. Each thread was resumed after its stack was read. Only the owned
frozen pytest process was inspected.

| Thread | Python evidence | Native evidence |
|---|---|---|
| GUI, `0x3de0` / 15840 | Baseline session's main thread; blocked in `StepIndicator.set_current`, line 68, called from the queued candidate slot | `WaitOnAddress -> QBasicMutex::lockInternal -> QMetaObject::disconnect -> QObject::disconnect`, underneath the widget/style call |
| Worker, `0xa9e4` / 43492 | `<no Python frame>` | `WaitForSingleObjectEx -> PyEval_RestoreThread -> PyGILState_Ensure -> Sbk_GetPyOverride`, called during `QObject::~QObject` and deferred-event processing at QThread exit |

The GUI is inside a Python-to-Qt call and waiting for Qt's connection mutex. The
exiting worker is in QObject destruction, trying to enter Python to look up a
virtual override. This forms the GIL/Qt mutex lock cycle. The exact mutex address
was not captured, but the opposing waits, stack paths and matching Qt source
explain the freeze; this is not inferred just from the name `polish`.

Qt 6.11.2's destructor holds the receiver's connection lock while calling the
sender's `disconnectNotify`. Its connection locks come from a shared mutex pool.
That explains why apparently unrelated widget operations can meet a worker's
teardown lock. See the [pinned Qt source](https://github.com/qt/qtbase/blob/v6.11.2/src/corelib/kernel/qobject.cpp#L999-L1028)
and [QObject's warning about disconnectNotify](https://doc.qt.io/qtforpython-6/PySide6/QtCore/QObject.html#PySide6.QtCore.QObject.disconnectNotify).

Native exports are not private debug symbols. Labels such as
`QPlainTextEdit::tr + 0x65d` and `PyInit_QtWidgets + ...` in the raw capture are
nearest exports, **not** claims that those named functions caused the problem.
The exported mutex, disconnect, GIL and destructor frames are retained with their
offsets. The stack walker was first calibrated on an owned sleeping Python process.

The GC fixture controls cyclic collection. It does not stop Qt's deferred
deletion or reference-count destruction. No `gc.collect` frame appears in these
freezes. Moving collection to the main thread therefore does not remove this
particular native teardown race.
The existing worker deletion follows Qt's usual ownership pattern and runs on
the worker's owning thread. This is a binding/locking interaction, not evidence
that a worker illegally updates widgets or deletes an object from a foreign thread.

## Measurement method

- Local interpreter only: CPython **3.12.14**, 64-bit Windows; pytest **9.1.1**;
  PySide6 and Qt **6.11.2**. No Python 3.11 or 3.13 environment was installed or
  substituted. The historical CI environment is 3.11; Claude's 3.13 results are
  supplied evidence, not new measurements here.
- Every pytest batch used `-o faulthandler_timeout=60`, `.venv/pytest-tmp`, and
  USERPROFILE/APPDATA/LOCALAPPDATA under `.venv/test-home`.
- The three named test functions comprise **four cases per cycle**, because the
  rerun test has two parameter values. The two complete files comprise **38
  cases per cycle**. Cycles preserve collection order and use separate pytest
  items and fixture instances.
- `tests/run_freeze_probe.py` starts a fresh process per batch and preserves its
  command, source SHA, Python version, exit status, duration, last test, log hash
  and every timeout dump. An interrupted repetition is never described as 200
  completed cycles or as a passing suite.
- `tests/freeze_probe.py` is an opt-in plugin. Its observed mode uses Python
  3.12's [sys.monitoring](https://docs.python.org/3.12/library/sys.monitoring.html)
  on the original code objects. It does not replace result slots, change their
  Qt metadata or add result-signal connections. It asserts both QThread identity
  and Python thread identity against the GUI thread at entry.
- QThread construction is weakly registered. Test-start and test-end snapshots
  record registered QThreads, `isRunning`, creator test and worker/native IDs;
  Python threads and a Windows native-thread census are recorded separately.
  An explicit calibration proves that monitoring sees a native QThread's Python
  method and the queued GUI receiver without replacing that receiver.
- Observing Qt and writing events changes timing. Controls without slot/thread tracing are
  separate from instrumented measurements; a passing traced run does not cancel
  a freeze with tracing disabled. Repetition/state hooks remain loaded in both.

## Run results

| Batch | Slot/thread tracing | Result |
|---|---|---|
| Three named tests, 200 cycles requested | Off | 143 completed cases, then document-open freeze in cycle 36; 113.11 s including timeout |
| Both files, 200 cycles requested | On | Intentionally stopped after 1,361 completed cases, no freeze; 447.19 s |
| Three named tests, second 200-cycle request | Off | 168 completed cases, then extraction freeze in cycle 43; native capture; 117.55 s including timeout |
| Full suite 1 (`full-2`) | Off | 1,297 passed in 94.75 s |
| Full suite 2 (`full-3`) | On | 1,297 passed in 258.80 s |
| Full suite 3 (`full-4`) | Off | 1,297 passed in 106.24 s |
| Full suite 4 (`full-5`) | On | 1,297 passed in 278.52 s |
| Full suite 5 (`full-6`) | On | 1,297 passed in 292.32 s |

All five valid full suites passed, **6,485 cases total**. None produced a timeout
dump. The existing pytest cache-permission warning remains. The repeat batches
stopped at their first freeze, so neither is 800 passing cases. The file loop was
shortened after reproduction to investigate the native wait; 200 completed file
cycles are **not** claimed. The no-reproduction stopping rule did not apply once
the first target loop froze.

The first traced two-file loop was intentionally stopped after **1,361 completed
cases**, with the next case in progress, to obtain a native
capture. It had requested 200 cycles but did not complete them. There was no
timeout dump or test assertion failure before the intentional stop.

One initial full-suite attempt is invalid as a suite measurement: the observer
used `Path.write_text` during a test that deliberately patches that method to
write `partial` and raise `OSError("disk full")`. The observer now writes through
a saved built-in `open`. This was a harness error, not a product freeze. Its log
is retained separately; it does not count as a passing full suite.

## Affinity, thread lifetime and direct calls

In the interrupted traced file loop, **19,237** monitored GUI entries all ran on
the GUI QThread and Python main thread. They include 324 candidate-result slots,
71 document-open result slots, 432 candidate displays, 534 opened-document
displays and 7,701 step changes. There were **zero affinity violations**.

At all **1,362 test starts** in that run, no registered QThread was still running
and `threading.enumerate()` contained only MainThread. Thus no preceding-test
worker or Python thread was found contaminating these starts. Native process
threads are a separate population: the frozen extraction process had 29, but
only the GUI and worker above had the relevant Python thread states. A native
thread count alone is not a count of leaked application workers. In the native
capture, 23 other stacks contain the OpenBLAS DLL in their wait chain; Windows
and XML-library wait stacks account for the remaining native helper threads.

The three traced full suites add **3,891 test-start snapshots**, **4,854 GUI
entries**, zero affinity violations, zero retained registered QThread objects at
test start, and no additional Python threads at test start. This includes 36
candidate-result slots and six document-open result slots. These counts exclude
the workaround experiment below.

There are deliberate direct calls in these tests. The Edit fixture calls
`show_opened` while its offline discovery thread can be alive. The late-result
test subsequently calls `_on_edit_opened` directly with a stale epoch while
discovery can still be alive; 35 such direct calls were observed in the traced
file run. That call follows the wait for the real open worker. The first freeze
was **inside that wait**, before the direct stale result. Extraction helpers
wait for inspection to finish before directly staging inspection/columns.
Other cancellation/closing tests intentionally pause a current worker with
bounded events; this is distinct from a worker left over from a preceding test.

## Application relevance

The frozen result is emitted by a real worker and delivered to a real GUI slot;
it is not a model mock calling a widget from a background thread. The production
application uses the same worker signals, `thread.finished -> worker.deleteLater`
connections and widget code. The native destructor/GIL dependency does not
require a pytest assertion, direct stale-result call, or cyclic collection.
The document-open reproduction uses the real DOCX package reader and reading
view builder. Its new-document result is not injected by the test. The extraction
reproduction mocks the model but uses the actual extraction worker and writer.

**Classification: application-reachable race, reproduced only in offscreen tests
so far.** A normal Windows-platform freeze has not been measured, and the lack
of Python 3.13 reproductions does not prove that platform or interpreter is
immune. Historical Python-only dumps are consistent with this mechanism, but
cannot identify their blank-frame threads retrospectively.

## Proposed correction and remaining boundary

The test-only causal experiment returns a completed, childless EditWorker or
ExtractionWorker to the GUI thread before its native thread exits. The existing
deferred deletion then occurs on the GUI thread rather than concurrently with
GUI styling. Result slots, parsing, extraction, cancellation, epochs and saving
are not replaced by the experiment.

For an approved application fix, put that return in each one-shot worker's
completion path before emitting `finished`, retain the existing asynchronous
thread cleanup, and add destruction-affinity regressions. Do not introduce a
blocking GUI `wait()`, move an object from a foreign thread, remove teardown, or
change model/extraction behavior. The experiment wraps the unchanged `run` and
moves the object immediately after it returns; a production placement inside
`finally` needs its own approved implementation and verification.
This proposal is scoped to the two reproduced, childless one-shot workers; it
does not qualify the lifetimes of the other worker types, including discovery's
timer-owning worker.

`tests/freeze_retirement_check.py` explicitly checks the destruction thread for
both workers. It is excluded from normal discovery and is intended to fail
without the opt-in causal plugin. It checks the proposed lifetime contract, not
an existing requirement that all QObjects must be destroyed on the GUI thread.

| Causal/regression batch | Result |
|---|---|
| Destruction checks, original code | Both assertions fail: EditWorker and ExtractionWorker are destroyed on a background thread; 1.10 s |
| Identical checks with opt-in lifetime prototype | Both pass: destruction is on the GUI thread; 0.98 s |
| Both original files, smoke check with prototype | 38 passed in 12.73 s |
| Same named-target loop, prototype, tracing off | All 200 cycles / 800 cases passed in 204.87 s; 2,400 actual one-shot workers retired; no dump |
| Both complete files, prototype, tracing on | All 36 cycles / 1,368 cases passed in 444.86 s; 1,296 workers retired; no dump |
| Original full suite with prototype | 1,297 passed in 94.17 s; no dump |

The 36-cycle run covers slightly more than the interrupted 1,361-case control.
Its 19,330 GUI entries had zero affinity violations, and its 1,368 test starts
had no running QThread or additional Python thread left over. That traced
control had already been passing, so the file-loop passes are behavioral
regression coverage rather than standalone proof of causality.

The stronger combination is the captured native lock cycle, the fail-before /
pass-after destruction check, and completion of the untraced 800-case workload
that froze twice on the original lifetime. This supports the proposed workaround;
it is finite evidence, not proof that every possible native Qt wait is eliminated.

An initial version of the two-worker check omitted ExtractionWorker's required
client argument, so its extraction case failed during setup. Those initial
`retirement-before` / `retirement-after` batches are invalid as a two-worker
comparison and retained as such. After supplying the unused inspection client
as `None`, the identical corrected test was run before and after the prototype.

The additional full suite with the prototype passed all 1,297 original tests.
The two explicit lifetime checks remain separate from that count. No application
fix has been applied.

## Evidence and reproduction commands

The [measurement summary](test-freeze-2026-10-15/measurements.json) and timeout/native
dumps accompany this review.
The local [document-open dump](test-freeze-2026-10-15/targets-200--dump-01.txt),
[extraction dump](test-freeze-2026-10-15/native-targets--targets-200--dump-01.txt)
and [native capture](test-freeze-2026-10-15/native-targets--targets-200--native-stack.json)
are preserved in full. Both historical hosted dumps are also included, with their
trailing cancellation log lines, and distinguished from this investigation's runs.
The evidence folder disables Git text conversion for its JSON and text files so
the recorded SHA-256 hashes survive commit and checkout unchanged.
Complete verbose logs and JSONL event streams remain under
`.venv/freeze-investigation`; their SHA-256 hashes allow local comparison without
committing tens of thousands of repetitive events. Only test identities, thread
identities and synthetic diagnostics are captured, never document/model arguments.

```powershell
.venv/Scripts/python.exe -X utf8 tests/run_freeze_probe.py targets
.venv/Scripts/python.exe -X utf8 tests/run_freeze_probe.py files
.venv/Scripts/python.exe -X utf8 tests/run_freeze_probe.py full
```

The runner refuses to overwrite an existing batch directory; use a new `--output`
path for a separately authorized reproduction. Native captures use only the
[documented Windows StackWalk64 API](https://learn.microsoft.com/en-us/windows/win32/api/dbghelp/nf-dbghelp-stackwalk64)
and already installed DLLs. No application, release or installed-software state
is changed by these test batches.
