"""Run bounded, isolated investigation batches with only the existing venv.

Examples: python tests/run_freeze_probe.py targets; then files; then full.
Stops the owned pytest child 75 seconds into an unfinished test, after pytest's
60-second faulthandler dump, and preserves every dump and the complete log.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
FILES = ["tests/test_main_window_extraction.py", "tests/test_main_window_edit.py"]
TARGETS = [
    FILES[0] + "::test_rerun_invalidates_old_candidate_and_late_cancel_cannot_restore_it",
    FILES[0] + "::test_complete_column_review_extract_save_and_confirmed_overwrite",
    FILES[1] + "::test_late_result_after_opening_another_document_is_ignored",
]


def run_batch(name, selectors, repeat, trace, output, extra=()):
    """Execute one new pytest process, retaining source output and a machine-readable result."""
    directory = output / name
    directory.mkdir(parents=True, exist_ok=False)
    command = [sys.executable, "-X", "faulthandler", "-m", "pytest", "-p", "tests.freeze_probe",
               "-vv", "--maxfail=1", "-o", "faulthandler_timeout=60", "--basetemp",
               ".venv/pytest-tmp", "--freeze-repeat", str(repeat), "--freeze-output",
               str(directory), *selectors, *extra]
    if trace:
        command.append("--freeze-trace")
    env = os.environ.copy()
    home = ROOT / ".venv/test-home"
    env.update(USERPROFILE=str(home), APPDATA=str(home / "AppData/Roaming"),
               LOCALAPPDATA=str(home / "AppData/Local"), PYTHONIOENCODING="utf-8")
    started = time.monotonic()
    timed_out = False
    native_capture = None
    last_state = None
    with (directory / "pytest.log").open("w", encoding="utf-8") as log:
        child = subprocess.Popen(command, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
        print(f"{name}: owned pytest PID {child.pid}, trace={trace}, repetitions={repeat}", flush=True)
        next_message = started + 20
        while child.poll() is None:
            now = time.monotonic()
            try:
                last_state = json.loads((directory / "state.json").read_text(encoding="utf-8"))
            except (FileNotFoundError, json.JSONDecodeError):
                pass  # A concurrent short state-file write is not test progress.
            expired = (last_state and last_state["active"]
                       and now - last_state["started"] > 75)
            if (native_capture is None and last_state and last_state["active"]
                    and now - last_state["started"] > 63):
                # Windows' venv launcher has a child Python process. The plugin
                # records the actual pytest PID; inspect that process, not the launcher.
                with (directory / "events.jsonl").open(encoding="utf-8") as events:
                    pytest_pid = json.loads(events.readline())["pid"]
                try:
                    captured = subprocess.run([
                        sys.executable, str(ROOT / "tests/freeze_native_stack.py"),
                        str(pytest_pid), str(directory / "native-stack.json"),
                    ], capture_output=True, text=True, timeout=10)
                    native_capture = {"pid": pytest_pid, "exit_code": captured.returncode,
                                      "stderr": captured.stderr}
                except subprocess.TimeoutExpired:
                    native_capture = {"pid": pytest_pid, "timeout": True}
            if expired or (last_state is None and now - started > 120):
                timed_out = True
                child.terminate()  # Only the pytest PID this runner just started.
                try:
                    child.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait(timeout=10)
                break
            if now >= next_message:
                print(f"{name}: {now - started:.0f}s; {last_state}", flush=True)
                next_message = now + 20
            time.sleep(0.25)
        exit_code = child.wait()
    log_path = directory / "pytest.log"
    text = log_path.read_text(encoding="utf-8")
    starts = list(re.finditer(r"Timeout \([^\n]+\)!", text))
    dumps = []
    for index, match in enumerate(starts):
        end = starts[index + 1].start() if index + 1 < len(starts) else len(text)
        dump_path = directory / f"dump-{index + 1:02}.txt"
        dump_path.write_text(text[match.start():end], encoding="utf-8")
        dumps.append(dump_path.name)
    summary_path = directory / "summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.exists() else None
    result = {"name": name, "command": command, "python": sys.version,
              "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"],
                                                         cwd=ROOT, text=True).strip(),
              "seconds": round(time.monotonic() - started, 2), "exit_code": exit_code,
              "timed_out": timed_out, "last_state": last_state, "dumps": dumps,
              "native_capture": native_capture,
              "log_sha256": hashlib.sha256(log_path.read_bytes()).hexdigest(),
              "summary": summary,
              "pytest_result": re.findall(r"^=+ .* (?:passed|failed|error)[^\n]*=+$", text, re.M)[-1:]}
    (directory / "result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: result[key] for key in ("name", "seconds", "exit_code", "timed_out",
                                                  "dumps", "pytest_result")}), flush=True)
    return exit_code == 0 and not timed_out and not dumps


def main():
    """Stop on the first failure or timeout; never silently rerun or change a test."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("smoke", "targets", "files", "full"))
    parser.add_argument("--iterations", type=int, default=200)
    parser.add_argument("--output", type=Path, default=ROOT / ".venv/freeze-investigation")
    args = parser.parse_args()
    stages = {
        "smoke": [("smoke", FILES, 1, True)],
        "targets": [(f"targets-{args.iterations}", TARGETS, args.iterations, False)],
        "files": [(f"files-{args.iterations}", FILES, args.iterations, True)],
        "full": [(f"full-{i}", [], 1, i in (2, 4, 5)) for i in range(1, 6)],
    }
    for name, selectors, repeat, trace in stages[args.stage]:
        if not run_batch(name, selectors, repeat, trace, args.output.resolve()):
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
