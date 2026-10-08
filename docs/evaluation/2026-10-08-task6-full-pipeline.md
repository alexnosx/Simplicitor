# Task 6 saved-output evaluation

Selected qwen3:8b was run once through `--full-pipeline` on all 32 actual files. Whole-file extraction passes. **Sectioned extraction fails both quality fractions and is not release-ready.** The aggregate fraction passes because the 28 smaller files dominate the denominator; that does not qualify the sectioned path. No extraction repairs or release actions were taken.

| Path | Files | Correct saved Data cells | Unflagged wrong | Same thresholds |
|---|---:|---:|---:|---|
| Whole file | 28 | 277/280 (98.93%) | 0/280 (0%) | PASS |
| Sectioned | 4 | 28/40 (70%) | 1/40 (2.5%) | FAIL |
| Aggregate | 32 | 305/320 (95.3125%) | 1/320 (0.3125%) | PASS |

The unchanged thresholds are at least 95% accuracy and at most 1% unflagged wrong slots, without rounding. [JSON report](2026-10-08-task6-full-pipeline.json) contains per-file counts, timings, coverage, subgroup fractions, and review burden. No source text, model response, quote, raw workbook, or absolute user path is tracked in the report.

## Method and retained settings

- Read actual DOCX/text-layer PDF files, call production `extract` with confirmed fixture columns, save through the production writer, and reopen the XLSX. Score reopened Data values under the existing scorer; saved Evidence statuses supply flags. No label-derived flags or in-memory extraction values enter scoring.
- Use all 28 original cases unchanged, plus four new independently authored large cases in [full-pipeline-manifest.json](../../tests/extraction/fixtures/full-pipeline-manifest.json). Each added document has 18 authored pages with fields near the start, middle, and end. A regression check proves the three fact blocks occupy distinct production sections. The DOCX character-based page equivalents differ from rendered pages.
- Actual model: `qwen3:8b-q4_K_M`, reported 8.2B, Q4_K_M. `num_ctx=16384`, `num_predict=4096`, `temperature=0`, `seed=0`, `think=false`, timeout 180 seconds. These settings, the generic prompt, original labels and column definitions, and thresholds were unchanged.
- Live run used the original profile's selected-Qwen entry only. It exercised six sections for each large DOCX and three for each large PDF. All 32 workbooks saved and reopened. No failed/excluded units or request errors were reported. Grounding consistency does not establish semantic correctness.

Reproduce with the selected-Qwen entry from `tests/extraction/fixtures/profiles.json` in an ignored profile file:

```powershell
.venv/Scripts/python.exe scripts/evaluate_extraction.py --full-pipeline --manifest tests/extraction/fixtures/full-pipeline-manifest.json --profiles .venv/task6-qwen-profile.json --report .venv/evaluation/task6.json
```

The evaluator's `passed` field and exit status retain the existing aggregate gate. Its JSON/Markdown and console output also expose each path's result. Do not interpret an aggregate PASS as a passing sectioned result.

## Coverage, flags, and limits

The four large files scored 7/10, 4/10, 7/10, and 10/10 respectively in manifest order. Their coverage was complete. Saved Evidence issues include missing values, non-verbatim proposals, unknown anchors, unverified alternatives, and conflicts. One semantically incorrect value passed grounding without a flag. The failure therefore cannot be dismissed as an unprocessed-section or save error.

Whole-file extraction flagged two correctly extracted nonmissing values out of 270 (0.74%); sectioned extraction flagged none of its 28 correct nonmissing values. All eight labelled absent slots were flagged: seven were correctly blank, while the sectioned absent slot contained an incorrect proposal. Flag rates do not change value accuracy.

A deterministic integration test reads an actual 900,000-character DOCX as exactly 300 page equivalents, processes its production sections, saves the workbook, and verifies the reopened identifier. Adding a one-page source makes 301 pages; reader preflight and production extraction both reject it before any further model call. This proves the job boundary, not live-model accuracy on 300 pages.

Third-party notices and hosted build evidence are covered by the [packaging procedure](../code-signing.md). Broader native UI, Python/Office-free-machine, SmartScreen, license/business-use decisions, and publication remain outside this task. No installer, uninstaller, Sandbox, or install/uninstall/delete tests ran on Alex's PC. LICENSE is unchanged.
