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
                     "${{ runner.temp }}/macos-source-tests.xml",
                     "${{ runner.temp }}/macos-captures/"]


def test_mac_source_captures_run_only_after_the_environment_preflight(workflow):
    steps = workflow["jobs"]["source-tests"]["steps"]
    preflight = next(s for s in steps if s.get("name") == "Record source environment")
    capture = next(s for s in steps if s.get("name") == "Capture Mac source screens")
    assert preflight["id"] == "environment"
    assert capture["if"] == "!cancelled() && steps.environment.outcome == 'success'"
    assert steps.index(capture) > next(i for i, s in enumerate(steps) if s.get("name") == "Run Mac source tests")
    for value in ("1280x800", "1024x640", "1-create-describe", "2-create-with-files",
                  "3-choose-columns", "4-review-and-save", "5c-edit-review"):
        assert value in capture["run"]
    assert "scripts/capture_screens.py" in capture["run"]


def test_mac_evidence_inspects_installed_qt_notices_without_downloading_text(workflow):
    command = next(s["run"] for s in workflow["jobs"]["source-tests"]["steps"]
                   if s.get("name") == "Record source environment")
    for name in ("PySide6", "PySide6_Essentials", "PySide6_Addons", "shiboken6", "qt_notice_probe"):
        assert name in command
    assert 'dist.metadata.get_all("License-File")' in command
    assert 'dist.locate_file("")' in command
    assert "https://" not in command


def test_qt_probe_checks_registered_files_beyond_package_and_dist_info_roots(workflow):
    command = next(s["run"] for s in workflow["jobs"]["source-tests"]["steps"]
                   if s.get("id") == "environment")
    assert "for entry in dist.files or ()" in command
    assert "dist.locate_file(entry)" in command
    assert '"registered_text_candidates"' in command
    assert 'dist.metadata.get("License")' in command


def test_source_probe_cannot_package_publish_or_use_secrets(workflow):
    assert set(workflow["jobs"]) == {"source-tests", "build"}
    content = WORKFLOW.read_text(encoding="utf-8")
    assert "secrets." not in content
    for step in workflow["jobs"]["source-tests"]["steps"]:
        if "uses" in step:
            assert step["uses"] in {"actions/checkout@v4", "actions/setup-python@v5",
                                    "actions/upload-artifact@v4"}
        for forbidden in ("python build.py", "build_macos.py", "qualify_", "gh release",
                          "workflow_dispatch", "pull_request_target"):
            assert forbidden not in step.get("run", "")


def test_package_job_is_read_only_bounded_and_pinned_after_source_tests(workflow):
    job = workflow["jobs"]["build"]
    assert job["needs"] == "source-tests"
    assert job["runs-on"] == "macos-14" and job["timeout-minutes"] == "120"
    assert workflow["permissions"] == {"contents": "read"}
    assert job["env"]["PILOT_HEAD_SHA"] == "${{ github.event.pull_request.head.sha }}"
    checkout = next(s for s in job["steps"] if s.get("uses") == "actions/checkout@v4")
    assert checkout["with"] == {"ref": "${{ github.event.pull_request.head.sha }}",
                                "persist-credentials": "false"}
    setup = next(s for s in job["steps"] if s.get("uses") == "actions/setup-python@v5")
    assert setup["with"] == {"python-version": "3.11", "architecture": "arm64"}


@pytest.mark.parametrize("action,label,actor,private,repo,branch,allowed", [
    ("labeled", "mac-package", "alexnosx", False, True, True, True),
    ("synchronize", "mac-package", "alexnosx", False, True, True, False),
    ("opened", "mac-package", "alexnosx", False, True, True, False),
    ("labeled", "other", "alexnosx", False, True, True, False),
    ("labeled", "mac-package", "other", False, True, True, False),
    ("labeled", "mac-package", "alexnosx", True, True, True, False),
    ("labeled", "mac-package", "alexnosx", False, False, True, False),
    ("labeled", "mac-package", "alexnosx", False, True, False, False),
])
def test_only_alex_adding_the_package_label_authorizes_a_package(
        workflow, action, label, actor, private, repo, branch, allowed):
    condition = " ".join(workflow["jobs"]["build"]["if"].split())
    terms = condition.split(" && ")
    expected = ["github.event.repository.private == false",
                "github.event.pull_request.head.repo.full_name == github.repository",
                "github.head_ref == 'codex/macos-apple-silicon-pilot'",
                "github.event.action == 'labeled'", "github.event.label.name == 'mac-package'",
                "github.actor == 'alexnosx'"]
    assert set(terms) == set(expected) and len(terms) == 6
    values = dict(zip(expected, [not private, repo, branch, action == "labeled",
                                 label == "mac-package", actor == "alexnosx"]))
    assert all(values[term] for term in terms) == allowed


def test_build_has_no_ollama_install_and_qualifies_before_only_four_final_outputs(workflow):
    steps = workflow["jobs"]["build"]["steps"]
    preflight = next(s for s in steps if s.get("name") == "Verify packaging host and offline runtime")
    assert '"$(uname -s)" = "Darwin"' in preflight["run"]
    assert '"$(uname -m)" = "arm64"' in preflight["run"]
    assert '"$RUNNER_ENVIRONMENT" = "github-hosted"' in preflight["run"]
    assert "assert_no_ollama" in preflight["run"]
    build = next(s for s in steps if s.get("name") == "Build pilot")
    qualify = next(s for s in steps if s.get("name") == "Qualify extracted pilot")
    assert steps.index(preflight) < steps.index(build) < steps.index(qualify)
    assert build["run"].strip() == "python build_macos.py"
    assert "scripts/qualify_macos_pilot.py" in qualify["run"]
    for argument in ("--bundle", "--manifest", "--report"):
        assert argument in qualify["run"]
    upload = next(s for s in steps if s.get("uses") == "actions/upload-artifact@v4")
    assert steps.index(upload) > steps.index(qualify)
    assert upload["with"]["retention-days"] == "14"
    assert upload["with"]["if-no-files-found"] == "error"
    assert upload.get("if", "success()") == "success()"
    assert upload["with"]["path"].splitlines() == [
        "dist/macos-pilot/Simplicitor-macos-arm64-pilot.zip",
        "dist/macos-pilot/SHA256SUMS-macos-pilot.json",
        "dist/macos-pilot/macos-pilot-qualification.json",
        "dist/macos-pilot/MAC-PILOT-README.txt"]
    content = "\n".join(s.get("run", "") for s in steps)
    assert "packaging/macos/MAC-PILOT-README.txt" in content
    for forbidden in ("python build.py", "brew install", "curl", "ollama pull", "gh release",
                      "notarytool", "xattr", "workflow_dispatch"):
        assert forbidden not in content


@pytest.mark.parametrize("relative", ["docs/macos-pilot.md", "packaging/macos/MAC-PILOT-README.txt"])
def test_both_instructions_cover_delivery_trust_folders_and_prior_model_results(relative):
    text = " ".join((WORKFLOW.parents[2] / relative).read_text(encoding="utf-8").split())
    for required in ("14 days", "GitHub sign-in", "outer", "unchanged pilot ZIP", "browser",
                     "shasum -a 256", "Open Anyway", "ad-hoc", "not notarized",
                     "~/Applications", "~/Simplicitor", "~/Library/Application Support/Simplicitor",
                     "existing", "Ollama", "qwen3:8b-q4_K_M", "llama3.1:8b-instruct-q4_K_M",
                     "Q4_K_M", "11/12", "272/280", "97.14%", "zero unflagged wrong",
                     "262/280", "93.57%", "95%", "Windows", "not Mac qualification",
                     "unchecked", "must-pass", "optional", "not checked", "model tag",
                     "before", "after", "feedback", "annoyed", "wished"):
        assert required in text, required
