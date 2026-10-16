# Azure desktop source acceptance evidence

Status: Claude reviewed Tasks 1-4 at `a080209` and confirmed the code/tests, with 1,377 isolated tests passing. His three visual findings are corrected on `codex/2.5.0-azure-desktop`, as measured below. Claude's follow-up check and Alex's Qt and merge approval are pending. No merge, version bump, build, tag or release.

The [approved plan](../superpowers/plans/2026-10-16-release-2.5.0.md) and its wording table govern this work. The [Azure reference](azure-desktop.html) remains unchanged. Product version is still **2.3.2**, read from version.py; Task 5 owns 2.5.0 preparation.

## Source identity and verification

Original Task 4 capture baseline: `edd70da735c887acbbf05bab5460654f0944e97b` (Task 3), plus Task 4's presentation changes. The current follow-up captures use baseline `a0802097ea22221d9fadf288ba2c2177c1373bd0`, plus the three visual corrections below. Captures precede their documentation commit. Each `capture-metadata.json` therefore explicitly marks its source commit as a base and records SHA-256 for the capture script, main window, defaults/styles, version and all widget source files. Those fingerprints are checked against the committed files. The local matrix manifest records the final commit after commit/push; this avoids claiming the parent alone contains the captured changes.

| Task | Commit before Task 4 | Targeted result | Full isolated suite |
|---|---|---|---|
| 0, reviewed by Claude | `9f4ebc0` | 120 passed | 1,334 passed |
| 1, shared styles/header/footer | `675ae07` | 133 passed | 1,341 passed in 111.88 s |
| 2, choices and Write layout | `7759ed4` | 209 passed | 1,353 passed in 116.65 s |
| 3, Pull/Edit/dialogs | `edd70da` | 70 affected appearance/Edit checks passed after the four-row fix | 1,359 passed in 113.19 s |
| 4, scale and reachability | This task | 118 passed | **1,377 passed in 118.37 s** |
| Claude visual-review follow-up | After `a080209` | 7 final regressions passed | **1,384 passed in 156.67 s** |

Task 1's sandbox run had 1,340 passed and one existing hard-link failure: `test_save_as_refuses_existing_source_alias` was denied `os.link` (WinError 5) before its assertion. Alex's authorized unchanged rerun with hard-link permissions passed all 1,341. Both logs are retained. Subsequent full suites use that permitted local test environment directly; no test is changed, skipped or marked to avoid the restriction. Passing runs retain the existing pytest-cache permission warning.

The full command is `.venv/Scripts/python.exe -m pytest -q -o faulthandler_timeout=60 --basetemp .venv/pytest-tmp`, with USERPROFILE, APPDATA and LOCALAPPDATA redirected under `.venv/test-home`. Logs and red/green evidence are in `.venv/plan-execution/2026-10-16-release-2.5.0/`.

## Capture matrix

The refreshed PNGs, contact sheets and measurement files are local source artifacts under `C:/Codex/Simplicitor/.venv/screens-2.5.0-followup/`. `matrix.json` indexes these six sets. Each folder includes `capture-metadata.json`, `label-background-checks.json` and `contact-sheet.jpg`. The original Task 4 captures remain under `.venv/screens-2.5.0/` for comparison.

| Folder | QT_SCALE_FACTOR | Logical window | Physical main-window PNG | Screenshots | Grey label samples |
|---|---|---|---|---|---|
| 1280x800-100 | 1 | 1280 x 800 | 1280 x 800 | 32 | 0 |
| 1280x800-125 | 1.25 | 1280 x 800 | 1600 x 1000 | 32 | 0 |
| 1280x800-150 | 1.5 | 1280 x 800 | 1920 x 1200 | 32 | 0 |
| 1024x640-100 | 1 | 1024 x 640 | 1024 x 640 | 32 | 0 |
| 1024x640-125 | 1.25 | 1024 x 640 | 1280 x 800 | 32 | 0 |
| 1024x640-150 | 1.5 | 1024 x 640 | 1536 x 960 | 32 | 0 |

Each run is a separate QApplication process, with `QT_AUTO_SCREEN_SCALE_FACTOR=0`, `QT_SCREEN_SCALE_FACTORS=1`, and the scale set before application creation. Logical window sizes and physical PNG sizes are asserted, including fractional scaling. This exercises real Qt scale/layout handling, rather than merely changing a saved image's device-pixel ratio.

The original 16 capture names remain. Eight added states show Settings, the built-in picker, disconnected Create, a Create error, Edit without a model, Edit busy, a Word paragraph removal and Edit Save. Eight `-actions.png` views additionally show scrolled controls. There are 24 staged states and eight action views per set, 192 PNGs across the matrix. All data is synthetic; discovery and work are staged without live model requests.

Important views in every folder:

- `1-create-describe.png`, `1b-write-template.png` and `1b-write-template-actions.png`: empty Write and the chosen built-in template, including the reachable folder action.
- `2a-files-reading.png`, `2-create-with-files.png`, `2b-files-partly-read.png`: source reading states and the unchanged reading-problems heading.
- `3-choose-columns.png`, `3b-pull-busy.png`: column setup and extraction progress. The four column rows remain visible at 1280 x 800.
- `4-review-and-save.png` and its action view: highlighted values plus reading problems. `4b-highlighted-values`, `4c-reading-problems` and `4d-clean-review` cover the other acknowledgement combinations.
- `5c-edit-review.png` and `9-edit-deletion-review.png`, with their action views: Before/After, preserved green additions and red deletions, the paragraph-removal notice and Use this change / Try again / Cancel.
- `7-settings.png`, `7b-built-in-template.png`: the real owned dialogs. The picker contains only business_pitch and technical_overview, seeded using the existing default-template helper inside the isolated capture profile.
- `8-disconnected.png`, `8b-create-error.png`, `8c-edit-no-model.png`, `8d-edit-busy.png`, `9b-edit-save.png`: remaining visible states and native-control affordances.

Reproduce a set from source with the scale environment above, for example `.venv/Scripts/python.exe scripts/capture_screens.py .venv/screens-2.5.0-followup/1024x640-125 --size 1024x640`. `--state 4-review-and-save` captures that state plus its action view. Invalid sizes/states fail with a plain CLI error. Existing output-directory-only invocations remain valid.

## Claude's three visual findings

The original action-reachability checks did not prove that the complete Describe cards fit or that a focused button's styled text rectangle was wide enough. New regressions use the application's 11 pt typography and inspect those bounds directly. Before the fixes, five cases failed: filled Write needed 410 pixels and ready Pull 400 pixels inside a 344-pixel viewport; the source note had 134 pixels for 211 pixels of text; focused mode text had 70 pixels for 74 pixels of text. The hover case already passed and remains covered.

Describe now has compact vertical card margins/spacing, a 96-140 pixel description box, a 96-128 pixel source list, Change beside the save-folder path, and the template button/name/Clear on one row. The source note is a single, vertically centred line. Header buttons reserve a transparent two-pixel border in every state; focus changes its colour without shrinking the text area. No wording, actions or workflow gates changed.

The capture check also reproduced a remaining six-pixel overflow while sources were Reading. A separate failing regression preceded the final source-list height correction. Strengthening the Write case with `C:\Users\Example\Documents\Simplicitor\Generated` instead of an abbreviated path reproduced another 14 pixels of overflow; the compact template row resolves it. The final tests and captures use that full synthetic path. Capture snapshots now deliver pending Qt LayoutRequest events before measuring and grabbing, including the initial discovery layout, as the existing action-reveal helper already does. There are no sleeps or retry loops for these measurements.

All three 1280x800 scale runs measured the following in logical pixels:

| State or control | Measured result |
|---|---|
| Empty Write, Write with template, Pull Reading, Pull Ready | Body and viewport both 1232 x 344; horizontal and vertical scroll maxima both 0 |
| Pull's DOCX/selectable-text/scanned-PDF hint | Entire label inside the visible viewport in Reading and Ready |
| Source files are kept unchanged | 211 pixels available for 211 pixels of text, on one line |
| Create new at startup, focused and checked | 74-pixel styled content area for 74 pixels of text |
| Edit document | 97-pixel styled content area for 97 pixels of text |

At 1024x640, Describe still scrolls as allowed: empty Write has a 98-pixel range, Write with a template 142, Pull Reading 154 and Pull Ready 128. The primary action and single-line source note remain outside that scroll area. The bounded file list has its own scroll bar when necessary; the card and its format hint fit at 1280x800. Existing review/action captures still cover acknowledgement and Save to Excel, and Edit Review at all six size/scale combinations.

The seven final regression cases pass. The final full isolated suite passed **1,384 tests in 156.67 seconds**, with the existing pytest-cache permission warning and no freeze. Logs are `visual-followup-red.log`, `visual-followup-reading-red.log`, `visual-followup-folder-red.log`, `visual-followup-green.log` and `visual-followup-full-final.log` under the execution-log folder above. Earlier full runs passed 1,383 tests before the extra Reading case, then 1,384 before strengthening the full-folder-path case.

## Layout checks and corrections

- Exact approved header/copy, shared version and real ICO; modes and Settings stay on the white second row. The selected-model footer is literal, elides at 220 logical pixels and retains its full tooltip; disconnect clears it without another selection event.
- Choice clicks on the icon/title/caption/check region emit one action. Keyboard Space works; repeated selection is a no-op. Existing independent input/template retention, job invalidation, busy guards and request counts remain covered by migrated behavioral tests.
- At 1024 x 640, initial action-only tests were insufficient: the first visual pass exposed a collapsed review grid and overlapping column controls. New failing tests cover those defects. Columns, Excel review and Word review now use scrollable card bodies with minimum readable grid/view heights. Fonts stay at 11 pt or above; actions remain reachable by scrolling and focus. At 1280 x 800, the existing four-complete-column-row and light-disabled-selection checks pass.
- The acknowledgement is checked with a mouse and the enabled Save to Excel button reached with Tab for highlighted-only, reading-only and combined cases, at both sizes. The existing save gate is unchanged. Edit review with a long notice keeps readable Before/After views and keyboard-reachable actions.
- Switching Describe routes resets only the presentation scroll to show the new numbered card titles; descriptions, source files, format and template retention remain unchanged. A regression first reproduced the inherited scroll position of 201 pixels.
- The source capture helper initially sampled labels outside a scroll viewport as if they were painted. It now intersects ancestor clip bounds and scales sample coordinates into physical pixels, retaining the visible-label background check. Zero sampled visible label corners match the central grey in all six sets; completely clipped labels are counted separately.
- A complete minimum-size capture reproduced an old scroll-range query after the preceding review state changed height. The capture helper now delivers pending Qt layout requests before revealing controls. The regression passes without sleeps or retries. Staged data is cleared before the existing non-blocking worker-drain loop, including on capture failure, so no hidden discard dialog is entered.

## Visual inspection and remaining approval

Codex inspected contact sheets and full-size Create, busy columns, combined/reading-only review, Word deletion review and picker views. No overlapping controls remain in the inspected corrected states. Primary Write/Pull actions stay outside Describe's scroll area. Review's initial and scrolled action views make the smaller-window trade-off explicit: every control remains reachable, but the whole review need not fit at once.

Qt uses native font/layout metrics, flat bordered panels and Qt-drawn decorative file marks, rather than browser shadows or web icons. Native operating-system file dialogs retain their existing appearance and behavior. The accepted wording table intentionally retains several existing labels instead of the reference's illustrative copy. These are the planned differences, not missing workflow features.

This is synthetic offscreen Qt source evidence, not an installed-Windows qualification or Alex's native scaling walkthrough. No model evaluation, Office/COM check or build was run. Model prompts/settings, extraction, document patch/verification/save, settings schema, LICENSE and historical releases remain unchanged.

Claude's original code/test review: **passed at a080209, with three visual corrections requested**. His check of these corrections: **pending**. Alex's source walkthrough, Qt approval and merge approval: **pending**. Stop here before merge and Task 5.
