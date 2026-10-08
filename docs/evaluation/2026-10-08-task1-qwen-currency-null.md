# Task 1 Qwen rerun after currency and null fixes

Run date: 2026-10-08 on [B1](../PROJECT_STATUS.md#benchmark-environment), Ollama 0.32.13, source [b0c068a](https://github.com/alexnosx/Simplicitor/commit/b0c068ac27656c63150f86b7094e7c6ad41d5545). [JSON evidence](2026-10-08-task1-qwen-currency-null.json) records settings and per-fixture aggregates.

The selected qwen3:8b Q4_K_M candidate scored **277/280 (98.93%)**, with **0/280 unflagged wrong values**: **PASS** under the unchanged 95% accuracy and 1% unflagged-error thresholds.

| Corpus group | Correct |
|---|---|
| Original 20 documents | 200/200 (100%) |
| Eight narrative documents | 77/80 (96.25%) |

Two of 270 correct nonmissing values were flagged (0.74%). All seven expected-missing slots were flagged separately. All three wrong projections were flagged. All 28 actual fixture files were scored, with no request failures.

Only two behaviors changed before this rerun: numeric conversion accepts a leading/trailing currency symbol or uppercase three-letter code after verbatim grounding, and blank/whitespace model values become absent nulls in parsing and Data projection. The generic system prompt, fixture files, labels, column definitions, settings, and thresholds were unchanged. The Qwen-only profile was an untracked selection of the existing candidate, not a changed corpus/profile file.

Thinking remained off; num_ctx 16384, num_predict 4096, temperature 0, seed 0, HTTP timeout 180 seconds. Timings are informational. Labels remained scorer-only. No changes were made in response to this run's scores.

The prerequisite full isolated suite passed 753 tests. This is the Task 1 direct whole-file gate. Task 2 production transport/sectioning is checked separately, and the saved-XLSX full-pipeline release gate remains Task 6.
