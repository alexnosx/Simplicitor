"""Contracts for the branch-only Mac source probe, without running hosted tools."""
from pathlib import Path

import pytest
import yaml


WORKFLOW = Path(__file__).parents[1] / ".github/workflows/macos-pilot.yml"


@pytest.fixture
def workflow():
    """Read event names literally, including YAML 1.1's special word `on`."""
    return yaml.load(WORKFLOW.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)


def test_only_pilot_pull_request_events_can_start_the_probe(workflow):
    assert set(workflow["on"]) == {"pull_request"}
    event = workflow["on"]["pull_request"]
    assert event["branches"] == ["main"]
    assert set(event["types"]) == {"opened", "reopened", "synchronize", "labeled"}


@pytest.mark.parametrize("guard", [
    "github.event.repository.private == false",
    "github.event.pull_request.head.repo.full_name == github.repository",
    "github.head_ref == 'codex/macos-apple-silicon-pilot'",
])
def test_probe_is_limited_to_the_public_same_repository_pilot_branch(workflow, guard):
    condition = " ".join(workflow["jobs"]["source-tests"]["if"].split())
    assert guard in condition
    assert condition.count("&&") == 2


def test_source_probe_is_bounded_and_uses_standard_arm64_python(workflow):
    job = workflow["jobs"]["source-tests"]
    assert job["runs-on"] == "macos-14"
    assert job["timeout-minutes"] == "15"
    assert job["env"]["QT_QPA_PLATFORM"] == "offscreen"
    setup = next(step for step in job["steps"] if step.get("uses") == "actions/setup-python@v5")
    assert setup["with"]["python-version"] == "3.11"
    assert setup["with"]["architecture"] == "arm64"


def test_platform_is_asserted_before_installing_existing_requirements(workflow):
    steps = workflow["jobs"]["source-tests"]["steps"]
    platform_index = next(i for i, s in enumerate(steps) if s.get("name") == "Verify Mac host")
    install_index = next(i for i, s in enumerate(steps) if s.get("name") == "Install dependencies")
    assert platform_index < install_index
    check = steps[platform_index]["run"]
    assert '"$(uname -s)" = "Darwin"' in check
    assert '"$(uname -m)" = "arm64"' in check
    assert steps[install_index]["run"].strip() == (
        "python -m pip install -r requirements-dev.txt -r requirements-build.txt")


def test_checkout_and_evidence_use_the_immutable_pull_request_head(workflow):
    assert workflow["permissions"] == {"contents": "read"}
    job = workflow["jobs"]["source-tests"]
    assert job["env"]["PILOT_HEAD_SHA"] == "${{ github.event.pull_request.head.sha }}"
    checkout = next(s for s in job["steps"] if s.get("uses") == "actions/checkout@v4")
    assert checkout["with"]["ref"] == "${{ github.event.pull_request.head.sha }}"
    assert checkout["with"]["persist-credentials"] == "false"
    metadata = next(s["run"] for s in job["steps"] if s.get("name") == "Record source environment")
    assert '"rev-parse", "HEAD"' in metadata
    assert 'assert source == os.environ["PILOT_HEAD_SHA"]' in metadata


def test_source_suite_has_isolated_profiles_and_freeze_diagnostics(workflow):
    steps = workflow["jobs"]["source-tests"]["steps"]
    command = next(s["run"] for s in steps if s.get("name") == "Run Mac source tests")
    for fragment in ('HOME="$test_home"', 'USERPROFILE="$test_home"',
                     'APPDATA="$test_home/AppData/Roaming"',
                     'LOCALAPPDATA="$test_home/AppData/Local"',
                     "python -m pytest -vv", "faulthandler_timeout=60",
                     '--basetemp "$RUNNER_TEMP/simplicitor-pytest"',
                     '--junitxml="$RUNNER_TEMP/macos-source-tests.xml"'):
        assert fragment in command


def test_probe_records_versions_and_python_license_availability(workflow):
    steps = workflow["jobs"]["source-tests"]["steps"]
    command = next(s["run"] for s in steps if s.get("name") == "Record source environment")
    for key in ("source_commit", "python", "macos", "architecture", "xcode", "clang",
                "qt", "nuitka", "python_license_available"):
        assert f'"{key}"' in command
    assert 'platform.system() == "Darwin"' in command
    assert 'platform.machine() == "arm64"' in command
    assert 'sys.version_info[:2] == (3, 11)' in command


def test_source_evidence_is_retained_without_an_application_artifact(workflow):
    steps = workflow["jobs"]["source-tests"]["steps"]
    upload = next(s for s in steps if s.get("uses") == "actions/upload-artifact@v4")
    assert upload["if"] == "always()"
    assert upload["with"]["retention-days"] == "14"
    assert upload["with"]["name"] == "macos-source-baseline"
    paths = upload["with"]["path"].splitlines()
    assert paths == ["${{ runner.temp }}/macos-source-environment.json",
                     "${{ runner.temp }}/macos-source-tests.xml"]


def test_task_zero_cannot_package_publish_or_use_secrets(workflow):
    assert set(workflow["jobs"]) == {"source-tests"}
    content = WORKFLOW.read_text(encoding="utf-8")
    assert "secrets." not in content
    for step in workflow["jobs"]["source-tests"]["steps"]:
        if "uses" in step:
            assert step["uses"] in {"actions/checkout@v4", "actions/setup-python@v5",
                                    "actions/upload-artifact@v4"}
        for forbidden in ("python build.py", "build_macos.py", "qualify_", "gh release",
                          "workflow_dispatch", "pull_request_target"):
            assert forbidden not in step.get("run", "")
