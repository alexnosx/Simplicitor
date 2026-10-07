# Simplicitor project status

Updated 2026-10-07. Documentation revision is complete; application implementation status is unchanged. This note is the ongoing status record; update it instead of creating competing handoff notes.

## Agreed direction

- Free Windows desktop application for nontechnical people with working local Ollama and a usable model.
- Confidential selective editing of Word, Excel, and PowerPoint is the primary workflow. Creation and the existing PowerPoint template engine remain supported.
- Confirm editable targets, propose replacements, patch a separate candidate, validate and preview it, then approve and save a new version.
- Preserve unselected content and supported document features. Unsupported edits fail safely rather than reconstructing the whole file.
- Representative users include sales, accounting, and privacy staff. Contractor timesheets include sensitive IDs and require deterministic calculations and identifier preservation.
- Zero-cost direct-download packaging: Nuitka standalone application, NSIS installer as the main artifact, portable ZIP secondary. No Microsoft Store or paid signing service.
- Installer packaging does not guarantee that unsigned Windows warnings or antivirus blocks disappear.

`PRD.md` is the active requirements source. `docs/code-signing.md` describes packaging. Historical v1 requirements remain in `docs/archive/PRD_v1.2.md` and the unchanged `docs/Simplicitor_PRD_v1.2.docx`.

## Current implementation

Source baseline reviewed: `main`, commit `7d060f9889a90a9b1bad25e5d10873734ede8625`. The public v1.2.0 tag is 20 commits behind that baseline; the downloaded release executable was not runtime-tested in this review.

| Area | State |
|---|---|
| Create workflow and PowerPoint templates | Implemented in source; current regression suite was run. |
| Legacy Edit workflow | Implemented, but reconstructs files from extracted text. |
| Selective targets, preservation, draft preview, approval | Approved requirements, not implemented. |
| Standalone installer and portable ZIP | Approved packaging direction, not implemented. |
| Windows or antivirus block | Reported by user; exact message or detection remains unverified. |
| Live model quality and Office rendering | Not integration-tested in this review. |

## Verification evidence

At the source baseline above, the existing suite passed 668 of 668 tests in 51.97 seconds using Python 3.12.14 and PySide6 6.11.2. The review used `.venv` and redirected `USERPROFILE` and `APPDATA` into a test directory because one existing widget test otherwise writes into the real Documents folder. This is source-level regression evidence, not a packaging or preservation gate pass.

Additional isolated probes reproduced:

- Same-named uploads overwrite an earlier working copy and reuse the earlier file's backup.
- A 2,001-word text file became 1,538 words after the manipulation worker truncated its input, accepted an echo response, and emitted success. An empty model response also overwrote a text file and emitted success.
- Excel read/write of unchanged extracted content split a comma-containing value, lost a formula, and converted a number to text. Excel generation converted string ID `00123` into number `123`.
- Word extraction omitted table text.
- A synthetic private value supplied as an invalid Word section type appeared in the parse-error log.

These are unresolved implementation issues. Passing the existing suite does not negate the reproductions. The original source and synthetic probe inputs were used; no client records were added to the repository.

Documentation-task checks on 2026-10-07: root `AGENTS.md` and `CLAUDE.md` were verified byte-identical; the archived PRD matches the original baseline; local Markdown links resolve; repository-map generator tests passed 5 of 5. An independent document review found and corrected the remaining model-size reliability claim in README. The generated map and Git whitespace diff were checked. Application tests were not rerun for these prose-only changes; the 668-test result above remains the earlier source-baseline evidence.

## Agent guidance review

`CLAUDE.md` was useful but contained stale or conflicting guidance. The revised `AGENTS.md` mirrors it exactly. Corrections include:

| Former guidance | Correction |
|---|---|
| Historical DOCX PRD governs all future scope. | Active requirements are in root `PRD.md`; current user decisions govern changes. |
| Stop on every ambiguity and report a commit for every task. | Make routine decisions independently; ask about material unresolved choices; report actual commit and check status. |
| Double-click works and packaging is complete. | Onefile build exists; installer, Windows trust, and clean-machine checks remain pending. |
| JSON mode and simplified-prompt retry apply generally. | Describe freeform, template, and manipulation paths separately. |
| One backup per file and metadata-only logs are established guarantees. | Filename collisions and content-bearing error paths remain known gaps. |
| DOCX formatting loss is accepted and preservation must not be added. | Historical v1 trade-off is superseded by the approved selective-editing requirements. |
| Original build phases must be executed from phase 1. | Treat them as historical implementation history, not the next work plan. |

No application code, build configuration, dependency declaration, or license was changed in this documentation task. Alex authorized committing and pushing these documentation changes on 2026-10-07. Application implementation, release tagging, and artifact publication remain outside that authorization.

## Open decisions and dependencies

- Exact security warning or antivirus detection on the current release.
- Tested Nuitka version and built-in NSIS installer options, including per-user installation and upgrade behavior.
- Preview engine and whether Microsoft Office must be installed for rendering or recalculation.
- Supported Office feature envelopes, target identities, stale-source checks, candidate approval/version identity, retention, and cancellation.
- Tested local model/runtime combinations and hardware requirements. No Hermes integration or model replacement was selected.
- License alignment with the intended business audience. Current PolyForm Noncommercial terms remain unchanged; free distribution alone does not grant business-use rights.

## Next step

Prepare the bounded packaging implementation design from `docs/code-signing.md`, including a reproduction of the reported Windows block and clean-machine checks. Define the selective-editing subsystem and its preservation fixtures as a separate implementation design before changing the legacy Edit path. The commit/push authorization covers this documentation revision only; implementation and release publication need their own authorization.
