"""Edit for Word model check (release gate): 12 fixed tasks through the production route.

Usage: python scripts/evaluate_editing.py --models <installed tags> --out <report.json>
Pass per model: its installed tag, digest and quantization are identified, at least
PASS_MINIMUM of 12 tasks pass, and no candidate fails verification. The report holds task
IDs, results, failed check names and model identity only, never document text.
"""
import argparse
import json
from pathlib import Path
import re
import sys
from threading import Event

import requests

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "simplicitor") not in sys.path:
    sys.path.insert(0, str(ROOT / "simplicitor"))

from app.config.defaults import (  # noqa: E402
    EDIT_TEMPERATURE, EXTRACTION_NUM_CTX, EXTRACTION_NUM_PREDICT, EXTRACTION_TIMEOUT_S,
    OLLAMA_BASE_URL, OLLAMA_TAGS_ENDPOINT,
)
from app.services.ollama_client import OllamaClient  # noqa: E402
from editing import reading_view  # noqa: E402
from editing.models import EditError  # noqa: E402
from editing.package import open_document  # noqa: E402
from editing.patch import UNSAFE, build_candidate  # noqa: E402
from editing.proposal import request_change  # noqa: E402

FIXTURES = ROOT / "tests" / "editing" / "fixtures"
PASS_MINIMUM = 11  # Decision D4 is open; the approved design's bar applies until Alex decides.
QUANTIZATION = "Q4_K_M"


def _first_word(text: str) -> str:
    found = re.match(r"\W*(\w+)", text)
    return found.group(1) if found else ""


def check(task: dict, texts: list[str]) -> list[str]:
    """Names of the failed mechanical checks for one proposal's output paragraphs.

    expected: the whole result; expected_start: the first paragraphs exactly; required:
    exact substrings of the result; keeps: substrings ignoring case; paragraphs: per output
    paragraph, its first word, the substrings it must keep and the whole words it must
    contain (both ignoring case).
    """
    joined = "\n".join(texts)
    failed = []
    if "expected" in task and texts != task["expected"]:
        failed.append("expected")
    if "expected_start" in task and texts[:len(task["expected_start"])] != task["expected_start"]:
        failed.append("expected_start")
    failed += [f"required:{i}" for i, value in enumerate(task.get("required", [])) if value not in joined]
    failed += [f"keeps:{i}" for i, value in enumerate(task.get("keeps", []))
               if value.casefold() not in joined.casefold()]
    for k, spec in enumerate(task.get("paragraphs", [])):
        text = texts[k] if k < len(texts) else ""
        if "first_word" in spec and _first_word(text) != spec["first_word"]:
            failed.append(f"paragraph:{k}:first_word")
        failed += [f"paragraph:{k}:keeps:{i}" for i, value in enumerate(spec.get("keeps", []))
                   if value.casefold() not in text.casefold()]
        failed += [f"paragraph:{k}:words:{i}" for i, word in enumerate(spec.get("words", []))
                   if not re.search(rf"\b{re.escape(word)}\b", text, flags=re.IGNORECASE)]
    if "max_words" in task and len(joined.split()) > task["max_words"]:
        failed.append("max_words")
    if "min_paragraphs" in task and len(texts) < task["min_paragraphs"]:
        failed.append("min_paragraphs")
    if "max_paragraphs" in task and len(texts) > task["max_paragraphs"]:
        failed.append("max_paragraphs")
    return failed


def run_task(task: dict, model: str, client) -> dict:
    opened = open_document(FIXTURES / task["fixture"])
    first = next(b.index for b in opened.paragraphs if b.text.startswith(task["start"]))
    last = first + task["count"] - 1
    styles = {b.index: b.style for b in reading_view.build(opened) if b.kind == "paragraph"}
    try:
        proposal = request_change(opened, first, last, task["instruction"], styles, model, 0,
                                  client, Event())
    except EditError as exc:
        return {"id": task["id"], "result": "invalid proposal", "message": str(exc)}
    try:
        build_candidate(opened, first, last, proposal)
    except EditError as exc:
        verification = str(exc) == UNSAFE
        return {"id": task["id"], "result": "verification failed" if verification else "refused"}
    failed = check(task, [p.text for p in proposal.paragraphs])
    return {"id": task["id"], "result": "pass" if not failed else "check failed", "failed": failed}


def identity(model: str, tags: dict) -> dict:
    """The installed tag's digest and quantization from Ollama's model list."""
    entry = tags.get(model)
    if entry is None:
        return {"tag": model, "digest": None, "quantization": None}
    details = entry.get("details") or {}
    return {"tag": model, "digest": entry.get("digest"), "quantization": details.get("quantization_level"),
            "parameter_size": details.get("parameter_size")}


def evaluate(models: list[str], client, tasks: list[dict], tags: dict) -> dict:
    report = {"settings": {"seed": 0, "temperature": EDIT_TEMPERATURE, "num_ctx": EXTRACTION_NUM_CTX,
                           "num_predict": EXTRACTION_NUM_PREDICT, "timeout_s": EXTRACTION_TIMEOUT_S,
                           "think": False},
              "pass_minimum": PASS_MINIMUM, "quantization": QUANTIZATION, "models": []}
    for model in models:
        who = identity(model, tags)
        if not who["digest"] or who["quantization"] != QUANTIZATION:
            report["models"].append({"model": who, "gate": "fail", "reason": "model identity",
                                     "passed": 0, "tasks": len(tasks), "verification_failures": 0,
                                     "results": []})
            continue
        results = [run_task(task, model, client) for task in tasks]
        passed = sum(r["result"] == "pass" for r in results)
        verification = sum(r["result"] == "verification failed" for r in results)
        report["models"].append({
            "model": who, "passed": passed, "tasks": len(tasks), "verification_failures": verification,
            "gate": "pass" if passed >= PASS_MINIMUM and verification == 0 else "fail",
            "results": results,
        })
    report["gate"] = "pass" if report["models"] and all(m["gate"] == "pass" for m in report["models"]) else "fail"
    return report


def installed_tags(base_url: str) -> dict:
    """Ollama's installed models by tag, read from the local server only."""
    with requests.Session() as session:
        session.trust_env = False
        response = session.get(base_url.rstrip("/") + OLLAMA_TAGS_ENDPOINT, timeout=10)
        response.raise_for_status()
        return {m["name"]: m for m in response.json().get("models", [])}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models", nargs="+", required=True, help="installed tags, for example qwen3:8b-q4_K_M")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    tasks = json.loads((FIXTURES / "edit_tasks.json").read_text(encoding="utf-8"))
    report = evaluate(args.models, OllamaClient(OLLAMA_BASE_URL), tasks, installed_tags(OLLAMA_BASE_URL))
    args.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    for model in report["models"]:
        print(f"{model['model']['tag']}: {model['passed']}/{model['tasks']} passed, "
              f"{model['verification_failures']} verification failures, gate {model['gate']}")
    return 0 if report["gate"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
