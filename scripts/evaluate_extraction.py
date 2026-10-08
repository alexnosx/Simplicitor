"""Evaluate whole actual fixture files, without a production UI or sectioner."""
import argparse
from dataclasses import asdict, dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import ipaddress
import json
from pathlib import Path
import re
import sys
import time
from typing import Mapping
from urllib.parse import urlsplit

import requests

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "simplicitor") not in sys.path:
    sys.path.insert(0, str(ROOT / "simplicitor"))

from app.config.defaults import (
    EXTRACTION_MAX_JOB_PAGES,
    EXTRACTION_NUM_CTX,
    EXTRACTION_NUM_PREDICT,
    EXTRACTION_TIMEOUT_S,
    OLLAMA_BASE_URL,
)
from extraction.grounding import failed_fields, parse_fields
from extraction.models import (
    ColumnSpec, SourceDocument, build_response_schema,
)
from extraction.source_readers import SourceReadError, read_source

from extraction.request_format import SYSTEM_PROMPT, build_extraction_prompt


class EvaluationError(ValueError):
    """A safe evaluation error code without source or server contents."""


@dataclass(frozen=True)
class ScoredField:
    value: object
    flagged: bool


@dataclass(frozen=True)
class ExpectedField:
    expected_value: object
    expected_type: str


@dataclass(frozen=True)
class EvaluationReport:
    total: int
    correct: int
    unflagged_wrong: int
    flagged_correct: int
    expected_missing: int
    flagged_expected_missing: int
    correct_values: int

    @property
    def flag_rate_correct(self) -> float:
        """Review burden on correctly extracted nonmissing values."""
        return self.flagged_correct / self.correct_values if self.correct_values else 0.0

    @property
    def passed(self) -> bool:
        """Apply both fixed quality fractions to the full denominator."""
        return passes_quality_gate(self.correct, self.unflagged_wrong, self.total)


def passes_quality_gate(correct: int, unflagged_wrong: int, total: int) -> bool:
    """No rounding: 95% accuracy and at most 1% unflagged wrong slots."""
    return total > 0 and 100 * correct >= 95 * total and 100 * unflagged_wrong <= total


def _matches(actual: object, expected: ExpectedField) -> bool:
    want = expected.expected_value
    if want is None:
        return actual is None
    if expected.expected_type == "text":
        return isinstance(actual, str) and actual == want
    if expected.expected_type == "date":
        if isinstance(actual, datetime):
            actual = actual.date()
        return isinstance(actual, date) and actual == want
    if isinstance(actual, bool) or not isinstance(actual, (int, float, Decimal)):
        return False
    try:
        value = Decimal(str(actual))
        return value.is_finite() and value == Decimal(str(want))
    except InvalidOperation:
        return False


def score_results(
    actual: Mapping[tuple[str, str], ScoredField],
    labels: Mapping[tuple[str, str], ExpectedField],
) -> EvaluationReport:
    """Score independent labels without feeding them into extraction or flags."""
    correct = unflagged = flagged_correct = missing = flagged_missing = correct_values = 0
    for key, expected in labels.items():
        field = actual.get(key, ScoredField(None, True))
        good = _matches(field.value, expected)
        correct += good
        unflagged += not good and not field.flagged
        if expected.expected_value is None:
            missing += 1
            flagged_missing += field.flagged
        else:
            flagged_correct += good and field.flagged
            correct_values += good
    return EvaluationReport(len(labels), correct, unflagged, flagged_correct, missing,
                            flagged_missing, correct_values)


def _loopback_url(url: str) -> str:
    parsed = urlsplit(url)
    if parsed.scheme not in ("http", "https") or parsed.username or parsed.password:
        raise EvaluationError("loopback_url_required")
    try:
        local = parsed.hostname == "localhost" or ipaddress.ip_address(parsed.hostname).is_loopback
    except ValueError:
        local = False
    if not local:
        raise EvaluationError("loopback_url_required")
    return url.rstrip("/")


def call_ollama(
    url: str, model: str, source: SourceDocument,
    columns: tuple[ColumnSpec, ...], settings: dict,
) -> str:
    """Send the complete fixture in one schema-constrained, thinking-off request."""
    url = _loopback_url(url)
    prompt = build_extraction_prompt(source, columns)
    body = {"model": model, "system": SYSTEM_PROMPT, "prompt": prompt,
            "format": build_response_schema(columns, (source.source_id,)),
            "options": settings, "think": False, "stream": False}
    try:
        with requests.Session() as session:
            session.trust_env = False
            response = session.post(url + "/api/generate", json=body, timeout=EXTRACTION_TIMEOUT_S)
            response.raise_for_status()
            payload = response.json()
        if not isinstance(payload, dict) or not isinstance(payload.get("response"), str):
            raise EvaluationError("invalid_ollama_response")
        return payload["response"]
    except requests.Timeout:
        raise EvaluationError("ollama_timeout") from None
    except (requests.RequestException, ValueError) as exc:
        if isinstance(exc, EvaluationError):
            raise
        raise EvaluationError("ollama_request_failed") from None


def _model_details(url: str, model: str) -> dict:
    with requests.Session() as session:
        session.trust_env = False
        response = session.post(_loopback_url(url) + "/api/show", json={"model": model}, timeout=15)
        response.raise_for_status()
        payload = response.json()
        details = payload.get("details", {}) if isinstance(payload, dict) else {}
        if not isinstance(details, dict):
            details = {}
    size = details.get("parameter_size", "")
    match = re.fullmatch(r"([0-9]+(?:\.[0-9]+)?)\s*([BMK])", str(size).upper())
    count = Decimal(match[1]) * {"B": 10**9, "M": 10**6, "K": 1000}[match[2]] if match else 0
    return {"parameter_size": size, "parameter_count": int(count),
            "quantization": details.get("quantization_level", "unknown")}


def _expected(value: object, kind: str) -> ExpectedField:
    if value is not None:
        if kind == "date":
            value = date.fromisoformat(value)
        elif kind == "decimal":
            value = Decimal(str(value))
        elif kind == "integer":
            value = int(value)
    return ExpectedField(value, kind)


def evaluate(manifest: Path, profiles: Path, url: str) -> dict:
    """Run both candidates on actual files; persist aggregate counts only."""
    cases = json.loads(manifest.read_text(encoding="utf-8"))["cases"]
    candidates = json.loads(profiles.read_text(encoding="utf-8"))["candidates"]
    options = {"num_ctx": EXTRACTION_NUM_CTX, "num_predict": EXTRACTION_NUM_PREDICT,
               "temperature": 0, "seed": 0}
    prepared, labels = [], {}
    for case in cases:
        columns = tuple(ColumnSpec(**c) for c in case["columns"])
        truth = json.loads((manifest.parent / case["labels"]).read_text(encoding="utf-8"))
        if set(truth) != {c.id for c in columns}:
            raise EvaluationError("fixture_labels_incomplete")
        for column in columns:
            labels[(case["id"], column.id)] = _expected(truth[column.id], column.kind)
        prepared.append((case, columns))
    output = {"options": options, "think": False, "fixture_count": len(cases),
              "field_slots": len(labels), "candidates": []}
    for candidate in candidates:
        model = candidate["model"]
        item = {"name": candidate["name"], "model": model,
                "reference_only": candidate.get("reference_only", False)}
        print("Evaluating " + candidate["name"], flush=True)
        try:
            item.update(_model_details(url, model))
            if item["parameter_count"] < 8_000_000_000:
                raise EvaluationError("model_size_below_8b_or_unknown")
        except (requests.RequestException, ValueError):
            item.update(status="setup_failed", passed=False)
            output["candidates"].append(item)
            continue
        actual, case_reports = {}, []
        for index, (case, columns) in enumerate(prepared, 1):
            started = time.monotonic()
            error = None
            try:
                source = read_source(manifest.parent / case["file"], case["id"])
                if source.page_cost > EXTRACTION_MAX_JOB_PAGES:
                    raise SourceReadError("page_limit")
                response = call_ollama(url, model, source, columns, options)
                fields = parse_fields(response, source, columns)
            except (SourceReadError, EvaluationError) as exc:
                error = "source_read_failed" if isinstance(exc, SourceReadError) else str(exc)
                fields = failed_fields(columns, error)
            for column in columns:
                result = fields[column.id]
                actual[(case["id"], column.id)] = ScoredField(result.data_value, result.flagged)
            keys = [(case["id"], c.id) for c in columns]
            score = score_results({k: actual[k] for k in keys}, {k: labels[k] for k in keys})
            case_reports.append({"source_id": case["id"], **asdict(score),
                                 "request_error": error,
                                 "seconds": round(time.monotonic() - started, 3)})
            print(f"  {index}/{len(cases)}: {score.correct}/{score.total} correct", flush=True)
        score = score_results(actual, labels)
        item.update(status="scored", **asdict(score), passed=score.passed,
                    accuracy=score.correct / score.total if score.total else 0,
                    unflagged_wrong_rate=score.unflagged_wrong / score.total if score.total else 0,
                    flag_rate_correct=score.flag_rate_correct,
                    flag_rate_expected_missing=(score.flagged_expected_missing / score.expected_missing
                                                if score.expected_missing else 0),
                    fixtures=case_reports)
        output["candidates"].append(item)
    output["passed"] = any(c["passed"] and not c["reference_only"] for c in output["candidates"])
    return output


def main(argv: list[str] | None = None) -> int:
    """Write JSON and Markdown reports; return nonzero when the gate fails."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--profiles", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--url", default=OLLAMA_BASE_URL)
    args = parser.parse_args(argv)
    try:
        report = evaluate(args.manifest, args.profiles, _loopback_url(args.url))
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        lines = ["# Actual-file extraction evaluation", "", "All timings are informational.", "",
                 "| Candidate | Correct | Unflagged wrong | Gate |", "|---|---|---|---|"]
        for candidate in report["candidates"]:
            denominator = candidate.get("total", 0)
            correct = candidate.get("correct", "not scored")
            wrong = candidate.get("unflagged_wrong", "not scored")
            gate = "PASS" if candidate["passed"] else "FAIL"
            lines.append(f"| {candidate['name']} | {correct}/{denominator} | {wrong} | {gate} |")
        args.report.with_suffix(".md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        print("Gate: " + ("PASS" if report["passed"] else "FAIL"), flush=True)
        return 0 if report["passed"] else 1
    except (OSError, ValueError, KeyError, TypeError):
        print("Evaluation setup failed. Check fixture/profile files and loopback URL.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
