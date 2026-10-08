# 2.0.0 sectioned-source review policy: single full-corpus run

**Both path criteria pass; the CLI exited 0.** Sectioned PASS means every extracted cell requires review. The 40 sectioned slots do not qualify autonomous extraction accuracy.

| Path | Files | Correct saved Data cells | Unflagged values | Unflagged wrong | Criterion | Result |
|---|---:|---:|---:|---:|---|---|
| Whole file | 28 | 277/280 (98.93%) | 268 | 0 | At least 95% accuracy; at most 1% unflagged wrong | PASS |
| Sectioned | 4 | 33/40 (82.5%) | 0 | 0 | Zero unflagged values; accuracy informational | PASS |
| Combined, diagnostic only | 32 | 310/320 (96.875%) | 268 | 0 | No aggregate release gate | Not used |

[JSON report](2026-10-09-sectioned-review-policy.json) contains the actual per-file counts, path criteria, processing coverage, saved-output status, flags, and informational timings.

## Policy and values

Production extraction records sectioned_source per file requiring sectioning. The writer highlights every extracted Data cell and writes flagged primary Evidence with sectioned_source, retaining original validation issues and proposals. The review flag alone preserves verified values, Excel types, and numeric/date formats. Existing invalid proposals remain literal, and missing proposals remain highlighted blanks. The policy does not create a coverage warning. Existing saved-grid highlighting and Save As acknowledgement enforce review.

An independent reread verified **all 40 sectioned cells** are highlighted and have flagged primary Evidence with sectioned_source. All 320 saved values, types, and number/date formats match the preceding [33/40 run](2026-10-09-sectioned-rerun.md). No Data formulas were present. The formerly unflagged wrong contract identifier is now flagged for review; it was not corrected by the model. Six other sectioned slots remain wrong and flagged.

The four large files scored 6/10, 9/10, 8/10, and 10/10. Their 32 correctly extracted nonmissing values all require review, as does the correctly absent slot. Sectioned flag rates on correct and expected-missing values are intentionally 100%. Whole-file extraction remains unchanged: two flagged correct nonmissing values out of 270 (0.74%), and all seven expected-missing slots flagged.

## Method and scope

Exactly one --full-pipeline run used the existing 32-file [manifest](../../tests/extraction/fixtures/full-pipeline-manifest.json), production extraction/sectioning, saved candidates, reopened Data/Evidence, and the existing value scorer. No sectioned fixtures were added. All workbooks saved/reopened and all reader-emitted units were processed; no failed/excluded units, request errors, or reader warnings were reported. Each large DOCX used five requests; each large PDF three.

Selected original profile: qwen3:8b, actual model qwen3:8b-q4_K_M, reported 8.2B, Q4_K_M. Settings stayed num_ctx=16384, num_predict=4096, temperature=0, seed=0, think=false, timeout 180 seconds. SYSTEM_PROMPT, request format, fixture files, labels, columns, profiles/settings, dependencies, and LICENSE are unchanged.

The permitted local suite passed 185 checks, including saved types/formats/styles/Evidence, mixed whole/sectioned sources, retained invalid literal proposals, acknowledgement, correct-but-unflagged CLI rejection, unchanged whole-file thresholds, processing/save failures, existing grounding, corpus/page boundaries, and map generation. The full source suite also passed on the hosted Windows runner; [verification](2026-10-09-sectioned-review-verification.json) records the exact source commit and step result. It ran only there because the suite includes deletion tests. The automatic packaging/installer result is not verified for this source revision.

Raw workbooks remain in ignored workspace output. The evaluator's output_complete describes saved output and processing states; pre-existing reader-warning handling remains unchanged. No additional model trials, extraction tuning, local installer/uninstaller/Sandbox/install-uninstall-delete tests, tag, release, or publication were performed. Native packaging/UI and licensing decisions remain separate from this review-policy check.
