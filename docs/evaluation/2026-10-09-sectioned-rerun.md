# Sectioned-extraction revision: saved-output rerun

**Whole-file extraction passes. Sectioned extraction fails the revised zero-unflagged-wrong criterion.** The single full-corpus run produced the results below and the CLI exited **1**. It did not reproduce Alex's separate 36/40, zero-unflagged-wrong result.

| Path | Files | Correct saved Data cells | Unflagged wrong | Criterion | Result |
|---|---:|---:|---:|---|---|
| Whole file | 28 | 277/280 (98.93%) | 0/280 (0%) | At least 95% accuracy; at most 1% unflagged wrong | PASS |
| Sectioned | 4 | 33/40 (82.5%) | 1/40 (2.5%) | Zero unflagged wrong; accuracy is informational | FAIL |
| Combined, diagnostic only | 32 | 310/320 (96.875%) | 1/320 (0.3125%) | No aggregate release gate | Not used |

[JSON report](2026-10-09-sectioned-rerun.json) records per-file counts, path criteria, saved-output status, processing coverage, review burden, and informational timings. Its diagnostic `aggregate_passed=true` cannot override the failing sectioned path or overall `passed=false`.

## Changes and method

Section requests now have the same format as whole-file requests, containing only current source units, confirmed columns, record ID, and an optional user request. They contain neither previous_fields nor source_scope. Budgeting also excludes accumulated fields; code owns accumulation.

Trimmed, case-insensitive string "null" now becomes absent like an empty value. Verified values win over grounding/conversion failures in either order, retaining failed alternatives. Multiple failed proposals do not create a verified conflict that blocks a later verified value. Real verified conflicts and request/schema/truncation failures remain flagged.

The production extraction ran on the unchanged 32-file [manifest](../../tests/extraction/fixtures/full-pipeline-manifest.json), saved each candidate, reopened Data and Evidence, and used the existing scorer. The selected original profile was qwen3:8b, actual model `qwen3:8b-q4_K_M`, reported 8.2B, Q4_K_M. Settings remained `num_ctx=16384`, `num_predict=4096`, `temperature=0`, `seed=0`, `think=false`, timeout 180 seconds. SYSTEM_PROMPT, column definitions, all fixture files/labels, and model settings are unchanged. The request payload, null normalization, merge logic, and path criteria are the approved code changes.

All 32 workbooks saved and reopened. All reader-emitted units were processed; no excluded/failed units, request errors, or reader coverage warnings were reported in this corpus. Each large DOCX used five requests and each large PDF three. An independent recount from the saved sheets confirms 310/320 correct and one unflagged wrong, with no Data formulas.

## Remaining errors and review burden

In manifest order, the four large files scored **6/10, 9/10, 8/10, 10/10**. The unflagged error is the contract identifier in the large DOCX contract. It passed grounding but differs from its independent label; it is not merely outer whitespace. Grounding consistency still does not establish semantic correctness.

Six other sectioned slots were incorrect and flagged. Five were missing proposals and one failed verbatim grounding. All eight labelled absent slots across the full corpus were correctly blank and flagged. Whole-file extraction flagged two correctly extracted nonmissing values out of 270 (0.74%); sectioned extraction flagged none of its 32 correct nonmissing values.

This is one observed run. No repeated trials, prompt tuning, changed labels/settings, or additional semantic extraction repairs were performed to obtain a pass.

## Verification and boundaries

The permitted local suite passed 164 checks, including both merge orders, retained alternatives/conflicts, request/schema/truncation flags, literal-null parsing/projection, non-null text containing "null", context accounting, saved-cell path gates/exit codes, failed saving/processing coverage, the actual corpus, page boundaries, and map generation. The full source suite also passed on the hosted Windows runner; [verification](2026-10-09-sectioned-verification.json) records the exact source commit and step result. It ran only there because the full suite includes deletion tests. The automatic packaging/installer result is not verified for this source revision.

The evaluator's `output_complete` tracks successful saved output and processing states. Pre-existing reader-warning handling is unchanged; the key alone does not prove absence of source-reader warnings on other documents. This corpus reported none.

Raw workbooks remain in ignored workspace output. Reports contain aggregate metadata, not source text, values, quotes, or raw responses. No installer, uninstaller, Windows Sandbox, or install/uninstall/delete tests ran on Alex's PC. No LICENSE/dependency change, tag, release, or publication. The sectioned path remains unqualified under the revised criterion.
