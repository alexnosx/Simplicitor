# Simplicitor product requirements

Updated 2026-10-08. Approved product direction; the installer and selective editing workflow are not implemented yet.

## Purpose and audience

Simplicitor is a free Windows desktop application for nontechnical people who already have Ollama and a usable local model. It creates confidential Word, Excel, and PowerPoint documents from prompts or supplied source files, and selectively edits approved parts of existing documents while preserving the rest.

Users should work with files and instructions, without configuring an agent harness, writing scripts, or learning model parameters. Sales staff, accounting staff, and privacy staff are representative users. Simplicitor does not make a GDPR compliance guarantee.

The first release in this direction assumes Ollama, a usable local model, and the Microsoft Word, Excel, and PowerPoint desktop applications are already installed. Alex confirmed the desktop Office prerequisite on 2026-10-08. Detect and explain missing or unusable prerequisites; do not bundle Office or build model installation or management into this scope. No specific model, minimum hardware profile, or replacement agent harness has been selected. Requiring Office does not establish that the proposed automation or preview integration works.

## Current implementation and requirements authority

The v1.2 source has Create and Edit panels, local Ollama integration, Office generators, and a manifest-driven PowerPoint template engine. Its legacy Edit path extracts text and reconstructs files. It does not provide target selection, a draft preview, approval before publication, or verified preservation of unselected content.

The current build produces an unsigned Nuitka onefile executable. The agreed installer and portable ZIP are future deliverables. Documentation of a requirement is not evidence that the application meets it.

This file governs the new product requirements. [The archived v1.2 PRD](docs/archive/PRD_v1.2.md), `docs/Simplicitor_PRD_v1.2.docx`, and [the original implementation guide](docs/Simplicitor_Implementation_Guide.md) remain historical references. New user decisions supersede historical scope restrictions. [Project status](docs/PROJECT_STATUS.md) records implementation evidence and remaining decisions.

## Three agreed workflows

Alex confirmed these workflows on 2026-10-08. They share two main UI modes; source-based creation does not introduce a third mode.

| User action | Workflow |
|---|---|
| Create new, with a prompt | Generate a document from the instructions. |
| Create new, with a prompt and source files | Read the sources and create a new document using their information. |
| Edit document | Modify approved parts of an existing document. |

All three workflows produce a separate candidate for review and approval before saving a new output. Prompt-only generation exists in v1.2; source-based creation and the common candidate-review workflow are requirements, not implemented features. The [architecture proposal](docs/superpowers/specs/2026-10-08-document-architecture-design.md) describes how to reuse the existing engines.

## Creation workflow

1. Describe the required document and choose its output type.
2. Optionally attach local source files. Source inputs are read-only and distinct from an Edit document target.
3. Inspect the sources and confirm the relevant content, worksheets, tables, ranges, and reporting period when needed. Ask a focused question if ambiguity would materially change the result.
4. Extract typed information locally. Compute requested totals, differences, percentages, or other supported measures deterministically using code or Excel. The model explains and organizes the resulting evidence.
5. Generate a separate candidate using the existing output engines, validate it, and preview the saved document.
6. Review the content, numerical evidence, source references, and layout, then approve that candidate and save a new output. Sources remain unchanged.

The required cross-format example is an accounting XLSX workbook used to create a DOCX report. Preserve text identifiers and distinguish raw inputs, formula expressions, calculated values, missing values, and stale calculation results. Do not invent missing rates, currencies, dates, or amounts. Retain traceability from reported figures to source snapshots, worksheet/range references, and calculations, using source labels rather than exposing absolute paths in reports by default. Grounding and validation do not replace review of the model's narrative.

Large sources must be inspected and processed within an explicit scope. Deterministic extraction and aggregation may cover more rows than fit in a model prompt. Do not silently truncate relevant records, omit material information, or treat a partial report as complete. Narrow the scope or report a limitation when the request cannot be supported.

Source-based creation is local document work, not persistent indexing or a RAG system. Define supported source formats, Office features, and input/output combinations before claiming coverage. The three workflows do not imply that every format conversion is already supported.

## Representative workflows

| User | Input and requested change | Content to preserve |
|---|---|---|
| Sales | Adapt specified customer details and passages in a proposal. | Unselected terms, tables, branding, and embedded assets. |
| Accounting | Check a contractor timesheet against a supplied billing period and rates; propose corrections to specified entries. | Personal IDs, their associations, leading zeroes, unselected cells, formulas, and workbook structure. |
| Privacy | Revise specified policy passages or replace identified personal information. | Unselected text, document structure, and supported formatting. |

Accounting calculations must use deterministic code and supplied data. The model can interpret headings and explain discrepancies. Missing rates, ambiguous matches, or incomplete inputs must remain visible rather than being invented. The full timesheet reconciliation workflow is a use case to design, not an implemented feature or an expansion of the first editing slice.

## Selective editing workflow

1. Open a local source file without overwriting it or a different file with the same name.
2. Identify and confirm exact editable targets. The application may suggest targets, but ambiguous selections require clarification.
3. Describe the modification. The model proposes replacement content for the confirmed targets.
4. Validate the proposal and apply it to a separate candidate file using deterministic document operations.
5. Reopen and validate the saved candidate. Show the changed targets, before and after values, and a preview of the candidate.
6. Obtain approval for that candidate version and save a new output version. Further changes require another review.
7. Preserve the source on rejection, cancellation, malformed model output, stale targets, or write failure.

Context needed to interpret a target may be read locally. Permission to read context does not authorize changing it. Show the scope of a requested edit and stop if the source changed after inspection.

## First editing slice

| Format | Initial operation | Boundaries |
|---|---|---|
| Word `.docx` | Replace selected plain text within a supported paragraph or text span. | Preserve unselected content and supported styles; define the rich-text support envelope before implementation. |
| Excel `.xlsx` | Replace selected literal cell values. | Preserve cell types and identifiers, unselected formulas, styles, sheets, and supported workbook objects. |
| PowerPoint `.pptx` | Replace selected text within an existing supported text shape or span. | Preserve unselected shapes, slides, layouts, themes, and assets. |

Formula modification, row or column insertion, new slides, chart updates, and layout redesign are outside this first slice. Each needs defined targets and preservation checks before inclusion. Existing generation features, including PowerPoint templates, remain available independently of selective editing.

Do not rebuild an entire document from extracted text to implement a selective edit. Reject unsupported features or operations before publishing a candidate. Library support alone does not prove preservation.

## Preservation and review

For supported inputs, only approved targets may change. Compare unselected content, formulas, formatting, relationships, and embedded assets before and after. Do not require a byte-identical ZIP container; define the permitted package and metadata changes as part of each format's support envelope.

Longer text can change Word pagination or overflow PowerPoint shapes even when styles survive. The preview must expose those effects. Unsupported features and preservation failures must produce actionable errors, without a success message or published output.

Source and candidate identity must not depend only on a filename. Keep same-named files distinct. Version and retention rules are still to be designed; do not treat the current `_backup` filename convention as a safe identity mechanism.

## Privacy and failure behavior

- Document inference and processing stay local. No cloud fallback, remote OCR, remote preview service, or automatic upload of documents.
- Confirm that Ollama uses a local model; a localhost endpoint alone is not sufficient proof of local inference.
- Keep client data, prompts, model responses, and sensitive identifiers out of tracked files and diagnostic logs. Review filenames, paths, exception messages, and HTTP error bodies for content leakage.
- Define storage and retention for sources, candidates, previews, and backups. Disclose those local copies.
- Use synthetic or suitably sanitized fixtures for development and tests.
- Keep long operations off the UI thread. Show progress and actionable errors, retain user instructions after failure, and never report success after a failed downstream write.

The existing implementation has privacy and file-safety gaps recorded in project status. They remain unresolved by this documentation update.

## Packaging and distribution

The approved route is a zero-cost direct download, with no Microsoft Store registration or purchased signing service.

- Build a standalone Nuitka application with its runtime dependencies and resources bundled.
- Produce a conventional NSIS installer as the main download, with per-user installation, shortcuts, and an uninstaller.
- Evaluate Nuitka 4.2 or newer's built-in NSIS installer support before adding a separate packaging script. Choose and verify the build version during implementation.
- Offer a portable ZIP of the same standalone payload as a secondary download.
- Use GitHub Releases for artifacts and `simplicitor.com` as the download entry point.
- Preserve documents and settings during upgrade and uninstall; any data-removal option must be explicit.
- Keep releases unsigned unless a separately approved zero-cost signing route becomes available. Self-signing is not a public trust solution.

An installer does not guarantee removal of SmartScreen warnings or antivirus blocks. Identify the actual block and test release artifacts with default Windows security settings. Do not ask users to disable protection. Full packaging details and official references are in [Packaging and distribution](docs/code-signing.md).

## Acceptance checks

1. A nontechnical user with working local Ollama and desktop Microsoft Office can install and launch without Python, a terminal, or agent configuration. Missing prerequisites produce actionable messages.
2. Installer launch, application launch, local model and Office connection, upgrade, and uninstall pass on clean Windows test environments with the stated prerequisites. Record the tested versions and any security warning or block.
3. Installer and portable ZIP contain the same tested application resources and work independently of a development checkout.
4. Exact targets and original values are validated. Ambiguous, stale, or unsupported edits cannot silently proceed.
5. Approved replacements are correct, and preservation fixtures show that unaffected content, formulas, styles, media, and relationships survive.
6. IDs with leading zeroes remain text with the same identity and associations. Calculations use supplied inputs and deterministic computation.
7. The candidate opens in Microsoft Office without a repair prompt, and preview identifies relevant reflow or overflow.
8. Approval applies to the reviewed candidate version. Failure, rejection, or cancellation does not change the original or publish incomplete output.
9. Network and logging checks show local processing and no document-content leakage for the tested configuration.
10. Existing generation and template behavior remains covered by regression checks.
11. Prompt-only creation, creation from source files, and selective editing all use candidate validation, preview, approval, and saving of a new output. Read-only source attachments never gain edit permission.
12. An accounting XLSX can produce a reviewed DOCX report with correct supported calculations, traceable figures, and unchanged sources. Ambiguous periods, missing data, stale results, and incomplete coverage are visible rather than invented or silently omitted.

## Decisions still needed

- Office integration and preview technology, fidelity expectations, and supported Office versions. Installed desktop Office is required initially; this prerequisite is no longer an open decision.
- Supported rich-text and Office feature envelopes for each editing format.
- Supported source-ingestion features and input/output combinations, numerical evidence validation, calculation/recalculation rules, and handling of large or incomplete sources.
- Candidate naming, version identity, storage, retention, and cancellation behavior.
- Tested model/runtime combinations and practical hardware requirements.
- Exact Windows or antivirus detection blocking the current executable.
- License terms that permit the intended business use. The existing PolyForm Noncommercial license remains unchanged until Alex decides otherwise.

## Work outside this scope

A general-purpose agent, a chat platform, persistent agent memory, a RAG system, model management, cloud services, plugins, batch automation, automatic updates, PDF write-back, and Mac/Linux support are not part of the agreed first scope. Any expansion requires an explicit user decision. Packaging and selective editing are separate implementation workstreams; approving these documents does not authorize publication or unrelated features.
