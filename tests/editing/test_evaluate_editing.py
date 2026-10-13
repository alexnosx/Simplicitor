"""The model check's tasks are valid, its checks reject lossy edits, and it records identity."""
import importlib.util
import json
from pathlib import Path

import pytest

from editing.body_map import selection_problem
from editing.package import open_document
from tests.editing.conftest import FIXTURES

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "evaluate_editing.py"
spec = importlib.util.spec_from_file_location("evaluate_editing", SCRIPT)
evaluate_editing = importlib.util.module_from_spec(spec)
spec.loader.exec_module(evaluate_editing)
TASKS = json.loads((FIXTURES / "edit_tasks.json").read_text(encoding="utf-8"))
TAGS = {"good:8b": {"name": "good:8b", "digest": "sha256:abc",
                    "details": {"quantization_level": "Q4_K_M", "parameter_size": "8.2B"}},
        "wrong:8b": {"name": "wrong:8b", "digest": "sha256:def",
                     "details": {"quantization_level": "Q8_0"}}}


def test_twelve_tasks_with_unique_ids_valid_selections_and_passing_examples():
    assert len(TASKS) == 12 and len({t["id"] for t in TASKS}) == 12
    for task in TASKS:
        opened = open_document(FIXTURES / task["fixture"])
        first = next(b.index for b in opened.paragraphs if b.text.startswith(task["start"]))
        assert selection_problem(opened.blocks, first, first + task["count"] - 1) is None, task["id"]
        assert evaluate_editing.check(task, task["example_pass"]) == [], task["id"]


@pytest.mark.parametrize("task_id, lossy", [
    ("replace-value", ["45 days"]),
    ("replace-word", ["brief findings report"]),
    ("rename-headings", ["Introduction Details", "Introduction Details"]),
    ("exclamation", ["new page! final report!", "new page! final report!"]),
    ("polite-requests", ["draft report", "draft report"]),
    ("polite-requests", ["Please draft.", "Please report."]),
    ("polite-requests", ["Pleased to include a document review and findings report.",
                         "Please deliver the first draft within two weeks with feedback."]),
    ("split", ["Example Services and Sample Studio.", "This is a review project."]),
    ("polite-requests", ["Please review the findings report.",
                         "Please deliver the first draft within two weeks and keep feedback concise."]),
    ("polite-requests", ["Please preview the findings report.",
                         "Please deliver the first draft within two weeks and keep feedback concise."]),
    ("merge", ["document review findings report two weeks"]),
    ("add-sentence", ["Due in December."]),
    ("list-items", ["final presentation", "final presentation", "final presentation"]),
    ("merge", ["Two weeks."]),
])
def test_lossy_replies_fail_their_checks(task_id, lossy):
    task = next(t for t in TASKS if t["id"] == task_id)
    assert evaluate_editing.check(task, lossy) != []


class Client:
    """Answers each task with its example, or with a lossy reply for chosen tasks."""

    def __init__(self, answers):
        self.answers = answers

    def generate(self, model, prompt, system, **kwargs):
        instruction = json.loads(prompt)["instruction"]
        return json.dumps({"paragraphs": self.answers[instruction]})


def _answers(lossy=()):
    answers = {t["instruction"]: t["example_pass"] for t in TASKS}
    for task_id, reply in lossy:
        answers[next(t["instruction"] for t in TASKS if t["id"] == task_id)] = reply
    return answers


def test_examples_pass_through_the_production_route():
    report = evaluate_editing.evaluate(["good:8b"], Client(_answers()), TASKS, TAGS)
    model = report["models"][0]
    assert model["model"] == {"tag": "good:8b", "digest": "sha256:abc", "quantization": "Q4_K_M",
                              "parameter_size": "8.2B"}
    assert (model["passed"], model["verification_failures"], model["gate"]) == (12, 0, "pass")
    assert report["settings"]["temperature"] == 0.3 and report["gate"] == "pass"


def test_codex_lossy_replies_fail_through_the_full_evaluator():
    lossy = [("merge", ["document review findings report two weeks"]),
             ("polite-requests", ["Please draft.", "Please report."]),
             ("split", ["Example Services and Sample Studio.", "This is a review project."])]
    model = evaluate_editing.evaluate(["good:8b"], Client(_answers(lossy)), TASKS, TAGS)["models"][0]
    assert sorted(r["id"] for r in model["results"] if r["result"] != "pass") == ["merge", "polite-requests", "split"]
    assert model["passed"] == 9 and model["gate"] == "fail"


def test_lossy_replies_lower_the_score_and_fail_the_gate():
    lossy = [("replace-value", ["Invoices are payable within 45 days."]),
             ("exclamation", ["This paragraph starts on a new page!", "Use the agreed scope!"])]
    model = evaluate_editing.evaluate(["good:8b"], Client(_answers(lossy)), TASKS, TAGS)["models"][0]
    failed = sorted(r["id"] for r in model["results"] if r["result"] != "pass")
    assert failed == ["exclamation", "replace-value"]
    assert model["passed"] == 10 and model["gate"] == "fail"


def test_dropping_a_bookmarked_heading_is_an_invalid_proposal():
    lossy = [("rename-headings", ["Introduction and Details"])]
    model = evaluate_editing.evaluate(["good:8b"], Client(_answers(lossy)), TASKS, TAGS)["models"][0]
    assert [(r["id"], r["result"]) for r in model["results"] if r["result"] != "pass"] == [
        ("rename-headings", "invalid proposal")]


@pytest.mark.parametrize("model", ["wrong:8b", "missing:8b"])
def test_unidentified_or_wrong_quantization_fails_without_running(model):
    report = evaluate_editing.evaluate([model], Client({}), TASKS, TAGS)
    entry = report["models"][0]
    assert entry["gate"] == "fail" and entry["reason"] == "model identity" and entry["results"] == []
    assert report["gate"] == "fail"


@pytest.mark.parametrize("first", [
    "Please review the document and prepare a short findings report.",
    "Please review the project document and provide a short findings report.",
])
def test_measured_polite_rewrites_pass(first):
    task = next(t for t in TASKS if t["id"] == "polite-requests")
    second = "Please deliver the first draft within two weeks and keep feedback concise."
    assert evaluate_editing.check(task, [first, second]) == []


@pytest.mark.parametrize("first", ["Please review the findings report.", "Please preview the findings report."])
def test_polite_rewrite_losing_the_document_review_fails_the_gate(first):
    lossy = [("polite-requests", [first, "Please deliver the first draft within two weeks and keep feedback concise."])]
    model = evaluate_editing.evaluate(["good:8b"], Client(_answers(lossy)), TASKS, TAGS)["models"][0]
    assert [r["id"] for r in model["results"] if r["result"] != "pass"] == ["polite-requests"]
    assert model["passed"] == 11
