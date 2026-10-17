# Azure desktop source acceptance evidence

Status: Alex approved the Qt result and fast-forward merge on 2026-10-16 at `0cd1742`, after Claude confirmed both row/path follow-ups and a full isolated run of 1,389 tests. Task 5 preparation is authorized; Task 6 publication still requires Alex's separate go.

The [approved plan](../superpowers/plans/2026-10-16-release-2.5.0.md) and its wording table govern this work. The [Azure reference](azure-desktop.html) remains unchanged. The approved reference retains **2.3.2**. The refreshed Task 5 source captures read **2.5.0** from version.py; publication is still a separate gate.

## Source identity and verification

Original Task 4 capture baseline: `edd70da735c887acbbf05bab5460654f0944e97b` (Task 3), plus Task 4's presentation changes. The first visual follow-up used `a080209` plus the three corrections below. The approved compact-row/path captures use baseline `8e92c8c419bfc0c2a3adace320d6f6944d3033ea` plus the two new layout changes. Captures precede their documentation commit. Each `capture-metadata.json` therefore explicitly marks its source commit as a base and records SHA-256 for the capture script, main window, defaults/styles, version and all widget source files. Those fingerprints are checked against the committed files. The local matrix manifest records the final commit after commit/push; this avoids claiming the parent alone contains the captured changes.

| Task | Commit before Task 4 | Targeted result | Full isolated suite |
|---|---|---|---|
| 0, reviewed by Claude | `9f4ebc0` | 120 passed | 1,334 passed |
| 1, shared styles/header/footer | `675ae07` | 133 passed | 1,341 passed in 111.88 s |
| 2, choices and Write layout | `7759ed4` | 209 passed | 1,353 passed in 116.65 s |
| 3, Pull/Edit/dialogs | `edd70da` | 70 affected appearance/Edit checks passed after the four-row fix | 1,359 passed in 113.19 s |
| 4, scale and reachability | This task | 118 passed | **1,377 passed in 118.37 s** |
| Claude visual-review follow-up | After `a080209` | 7 final regressions passed | **1,384 passed in 156.67 s** |
| Compact source rows and folder path | After `8e92c8c` | 125 passed, including 5 new regressions | **1,389 passed in 229.25 s** |

Task 1's sandbox run had 1,340 passed and one existing hard-link failure: `test_save_as_refuses_existing_source_alias` was denied `os.link` (WinError 5) before its assertion. Alex's authorized unchanged rerun with hard-link permissions passed all 1,341. Both logs are retained. Subsequent full suites use that permitted local test environment directly; no test is changed, skipped or marked to avoid the restriction. Passing runs retain the existing pytest-cache permission warning.

The full command is `.venv/Scripts/python.exe -m pytest -q -o faulthandler_timeout=60 --basetemp .venv/pytest-tmp`, with USERPROFILE, APPDATA and LOCALAPPDATA redirected under `.venv/test-home`. Logs and red/green evidence are in `.venv/plan-execution/2026-10-16-release-2.5.0/`.

## Capture matrix

The Task 5 refreshed PNGs, contact sheets and measurement files with version 2.5.0 are local source artifacts under `C:/Codex/Simplicitor/.venv/screens-2.5.0-preparation/`. The approved compact-row/path set remains under `.venv/screens-2.5.0-compact/`. `matrix.json` indexes these six sets. Each folder includes `capture-metadata.json`, `label-background-checks.json` and `contact-sheet.jpg`. Original Task 4 and first visual-follow-up captures remain under `.venv/screens-2.5.0/` and `.venv/screens-2.5.0-followup/` for comparison.

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

Reproduce a set from source with the scale environment above, for example `.venv/Scripts/python.exe scripts/capture_screens.py .venv/screens-2.5.0-compact/1024x640-125 --size 1024x640`. `--state 4-review-and-save` captures that state plus its action view. Invalid sizes/states fail with a plain CLI error. Existing output-directory-only invocations remain valid.

## Claude's three visual findings, accepted at 8e92c8c

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

## Compact source rows and single-line folder path

Five failing checks preceded these changes: three file-state cases could not fit three complete rows in the existing list, and the folder path wrapped at both tested widths. Source rows now put the filename, unchanged status badge and Remove on one line. Compact row padding retains the 11 pt font and the existing progress bar. Only the Describe source list changes; the extraction progress list keeps its existing layout and behavior.

The new ElidedLabel paints a middle-elided single line at its current width. Its QLabel text, accessible name and tooltip retain the full literal value. It is used for Describe filenames and the Write folder path; resizing does not shorten stored text. Change remains beside the path, and choosing another folder refreshes both the displayed text and full tooltip. No wording, requests, worker logic, settings fields or save rules change.

All three desktop scale runs measured the same logical geometry:

| State/control | Measured result at 1280x800 |
|---|---|
| Source list | Existing 128-pixel height retained |
| Three files Reading | Three complete 38-pixel rows, including progress bars |
| Three files Ready | Three complete 32-pixel rows |
| Partly read plus two Ready files | Three complete 32-pixel rows; original badge wording retained |
| Write folder | One 26-pixel-high label beside Change; 315 pixels of displayed text within 328 pixels |
| Folder tooltip and accessible name | Full synthetic path retained exactly |
| Write/Pull Describe, source-format hint, source note, focused modes | Earlier desktop fit and text-bound checks still pass |

At 1024x640 the folder also stays on one line, with 246 pixels of text in 254 pixels; the full path remains available on hover. Describe still scrolls as allowed: empty Write has an 84-pixel range, Write with a template 130, Pull Reading 154 and Pull Ready 128. Three rows fit within the list itself; the smaller outer Describe viewport initially clips the third row, reachable by scrolling.

The capture set uses three existing synthetic invoice fixtures. Its staged review also has three rows, preserving one UI sample row per attachment; this is not a model evaluation or a change to the extraction pipeline. All 192 captures were regenerated. Metadata now records complete row rectangles, actual visibility through ancestor viewports, state labels, and the displayed/full folder values. Tests additionally use long filenames, verify accessible names and middle eliding, and exercise Remove and subsequent folder selection. Targeted suite: **125 passed**. Full isolated suite: **1,389 passed in 229.25 seconds**, with the existing pytest-cache permission warning and no freeze. Final log: `compact-rows-path-full.log`; the initial five failures are in `compact-rows-path-red.log`.

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

This is synthetic offscreen Qt source evidence, not an installed-Windows qualification or Alex's native scaling walkthrough. No model evaluation, Office/COM check or local build was run. Model prompts/settings, extraction, document patch/verification/save, settings schema, LICENSE and historical releases remain unchanged.

Claude's original code/test review: **passed at a080209**. His check of the three visual corrections: **passed at 8e92c8c, with 1,384 isolated tests passed**. The two further row/path corrections are measured above. Alex's Qt and merge approval: **granted on 2026-10-16 at 0cd1742**. Claude confirmed both row/path changes and 1,389 passing isolated tests. This records Alex's approval without adding unreported native walkthrough results. Task 5 is authorized; Task 6 is not.

## Task 5 version refresh

Main was fast-forwarded to approval record `5eeca9f`, without a merge commit. The version-only code change to 2.5.0 passed the full isolated suite: **1,389 passed in 210.91 seconds**, with the existing pytest-cache permission warning and no freeze. The approved hard-link-permitted environment was used without changing or skipping tests.

The six size/scale sets above were regenerated from that baseline plus version.py at 2.5.0. All 192 PNGs, six metadata source fingerprints and physical sizes were checked, with zero sampled grey label backgrounds. Codex inspected the refreshed desktop Pull view at 100% and 150%, the minimum-size contact sheet and the 125% Word deletion-review action view. Layout and gates retain the approved result. `docs/screenshot.png` is byte-identical to `1280x800-100/2-create-with-files.png`, SHA-256 `b9060e9aa903be5a3ffdf19d47744b75155d31465054daac378fddb0072e6a14`. The local matrix manifest records the committed source after the preparation commit. No model, engine, settings, LICENSE or capture-script change accompanies this version refresh. Hosted build qualification is recorded separately in project status.

## Post-release header correction, 2026-10-17

The installed 2.5.0 header exposed a packaged-resource lookup error and three missing
reference details. Nuitka 4.2.2's standalone `__compiled__.containing_dir` is the parent
of the executable directory, rather than the bundled-data root. `resource_path` now
resolves packaged assets beside `sys.executable`. Tests model that actual directory
relationship for installed and portable layouts, including loading the real S icon
from a synthetic payload with an unrelated working directory and no `sys.frozen` flag.

The header now draws document-plus and document-pencil navigation icons using Qt,
with muted, selected, hover and disabled colours, renders the subtitle in italic at
11 pt, and keeps the mockup's pale blue selected outline. The constant two-pixel
border and blue focus outline remain; strengthened geometry checks include both
the icon and the complete label. Ten affected checks failed before the correction;
the targeted suite passed 61 tests afterward. The full isolated suite passed
**1,395 tests in 216.88 seconds**, with the existing pytest-cache permission warning
and no freeze, using the hard-link-permitted environment without modifying or
skipping tests.

Fresh source captures are under `C:/Codex/Simplicitor/.venv/screens-header-fix/`, in
`1280x800-100`, `1280x800-125`, `1280x800-150`, `1024x640-100`, `1024x640-125` and
`1024x640-150`. Each set contains 32 synthetic screenshots and capture metadata with
source fingerprints, expected physical dimensions and layout measurements. Create
at 1280x800/100% and 1024x640/150%, and Edit Review at 1280x800/125%, were visually
checked against the approved header. The complete matrix's existing layout checks
passed, as did all **264** mode-button measurements with enough content width for
the full text, a 20-pixel icon and four-pixel gap. These are source captures and
simulated packaging tests, not a newly built
or installed executable. No version, release artifact or tag is changed.
