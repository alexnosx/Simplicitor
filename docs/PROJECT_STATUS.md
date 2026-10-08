# Simplicitor project status

Updated 2026-10-08. The three agreed workflows, Office prerequisite, UI design, and architecture proposal are recorded for review; application implementation status is unchanged. This note is the ongoing status record; update it instead of creating competing handoff notes.

## Agreed direction

- Free Windows desktop application for nontechnical people with working local Ollama and a usable model.
- Three workflows share two modes: Create new from a prompt, Create new from a prompt and read-only source files, and Edit document for approved selective changes. All use a separate candidate, validation, preview, approval, and a new output.
- XLSX accounting data used to create a DOCX report is a required source-based creation example. Compute supported figures deterministically, retain evidence and source references, and leave supplied sources unchanged.
- Large Word/PDF sources used to create an Excel workbook are also required. Confirm columns, types, and record boundaries; retain provenance and coverage; expose uncertain values. PDF input is read-only. Local OCR/vision for scanned or mixed PDFs remains to be selected and tested.
- General document work is the product's purpose. Contracts, financial documents, policies, proposals, and presentations are examples; timesheets do not define the product.
- The first product requires installed Microsoft Word, Excel, and PowerPoint desktop applications. Alex confirmed this prerequisite on 2026-10-08 to simplify editing fidelity and preview implementation.
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
| Create from source files, including Excel-to-Word reporting | Agreed requirements; not implemented. |
| Word/PDF-to-Excel extraction and local OCR/vision | Agreed source-based creation case; structured extraction and recognition are not implemented. |
| Legacy Edit workflow | Implemented, but reconstructs files from extracted text. |
| Selective targets, preservation, draft preview, approval | Approved requirements, not implemented. |
| Shared Edit document and Create new workspace | UI proposal and simulated browser example; not implemented in PySide6. |
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
- Office integration, preview engine, and tested Office versions. Requiring installed desktop Office is now an agreed prerequisite.
- Supported Office feature envelopes, target identities, stale-source checks, candidate approval/version identity, retention, and cancellation.
- Supported source-ingestion formats and output combinations, numerical evidence validation, calculation/recalculation rules, and treatment of large or incomplete sources.
- DOCX/PDF extraction schemas and record reconciliation, text-layer quality and coverage, provenance, and the local OCR/vision engine and tested scanning support envelope.
- Tested local model/runtime combinations and hardware requirements. No Hermes integration or model replacement was selected.
- License alignment with the intended business audience. Current PolyForm Noncommercial terms remain unchanged; free distribution alone does not grant business-use rights.

## UI design proposal

Alex endorsed Edit document and Create new modes with explicit target selection. The [workspace proposal](superpowers/specs/2026-10-08-document-workspace-ui-design.md) records the shared layout, format-specific selection, review, and save behavior. The [interactive example](design/document-workspace.html) uses synthetic contracts, financial data, and presentation text. Its proposals, previews, model readiness, and saving are simulations; it makes no AI calls or document writes. Browser interaction checks cover the example only, not the application engine.

On 2026-10-08 Alex authorized committing and pushing the design changes. This authorization does not include application implementation or release publication.

Verification on 2026-10-08: the repository HTML was opened directly in Edge using the existing Playwright runtime. Six interaction groups passed, covering the three editing formats, Create, revision and save safeguards, retained drafts on mode/document switches, Settings, and a 360-pixel layout without outer horizontal overflow. There were no browser script errors or external network requests. Repository-map tests passed 5 of 5 in 1.04 seconds. These results apply to the simulated design; the application suite and live Office/model integrations were not rerun for this documentation change.

## Next step

Review the [architecture proposal](superpowers/specs/2026-10-08-document-architecture-design.md), including source-based creation, before resolving the subsystem decisions and preparing an implementation plan. Packaging remains a separate workstream based on `docs/code-signing.md`, including reproduction of the Windows block and clean-machine checks. Implementation, new runtime dependencies, and release publication remain separately authorized actions.

## Architecture recommendation under review

The [architecture proposal](superpowers/specs/2026-10-08-document-architecture-design.md) consolidates the recommendation for review: retain Python/PySide6, Ollama, and the creation/template engines; add one controller, a local job workspace, and a document worker with Office adapters and PDF extraction. It covers prompt-only creation, read-only source analysis, reporting and structured extraction, and selective editing through common candidate review/publication. Native Office editing, PDF preview, and local OCR/vision remain proposed integrations, not verified capabilities. Commercial viability means usability and reliability; pricing and license terms remain separate decisions.

Alex explicitly confirmed all three workflows on 2026-10-08 and requested that the documentation be committed and pushed for Opus review. This includes the previously uncommitted Office-prerequisite and architecture notes. The HTML example still demonstrates the earlier UI concept and does not implement source attachments. No application implementation or messaging of another chat is part of this documentation task.

The proposal retains the material risks and open decisions: Office ownership/coexistence and prompts, source/candidate identity, feature preservation, numerical evidence, calculation rules, large-source coverage, privacy, retention, and cancellation. Packaging and business-use licensing remain release dependencies. See the proposal for the reuse plan, failure behavior, delivery gates, and official references.

Read-only inspection on 2026-10-08 found Word, Excel, and PowerPoint COM registrations and x64 Office version `16.0.20326.20158`. Qt PDF and Qt PDF Widgets are available in the existing virtual environment; `win32com` is not. No Office app was launched and no automation, preview, preservation, or source-analysis integration was tested. `pywin32` remains a proposed new dependency, not installed or added to requirements. Application code, dependencies, build scripts, license, and the interactive HTML are unchanged by this documentation update.

Documentation checks for the earlier review update at commit `40b9bc8`: all four workflow tables matched, local Markdown links resolved, root agent instructions were byte-identical, and the generated repository map was current and deterministic. Repository-map tests passed 5 of 5 in 0.98 seconds. Eight Markdown files changed, including the new architecture proposal. Application tests and browser checks were not rerun because application code and the HTML example did not change.

Follow-up on 2026-10-08: Alex added the reverse case, large Word or PDF input used to create Excel output. Requirements, architecture, UI guidance, and shared instructions now include complete-scope extraction, explicit schemas, source references, literal typed cells, uncertainty review, and text/scanned/mixed PDF handling. The existing PDF method only joins page text and truncates it; the declared `pdfplumber` dependency offers text/table extraction but not OCR. No application code, new dependency, or recognition engine was added in this follow-up.

Alex authorized committing and pushing this follow-up on 2026-10-08. Pre-commit verification covers the eight Markdown files, local links, mirrored instructions, unchanged workflow tables, and deterministic repository-map generation. Application tests and browser checks are not rerun for these prose-only changes; earlier test results remain historical evidence.
