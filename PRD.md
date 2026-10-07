# Simplicitor product requirements

Updated 2026-10-07. Approved product direction; the installer and selective editing workflow are not implemented yet.

## Purpose and audience

Simplicitor is a free Windows desktop application for nontechnical people who already have Ollama and a usable local model. Its primary purpose is to modify confidential Word, Excel, and PowerPoint documents by changing approved parts and preserving the rest. Document creation remains supported.

Users should work with files and instructions, without configuring an agent harness, writing scripts, or learning model parameters. Sales staff, accounting staff, and privacy staff are representative users. Simplicitor does not make a GDPR compliance guarantee.

The first release in this direction assumes Ollama and a model are already installed. Detect and explain connection or model problems; do not build model installation or management into this scope. No specific model, minimum hardware profile, or replacement agent harness has been selected.

## Current implementation and requirements authority

The v1.2 source has Create and Edit panels, local Ollama integration, Office generators, and a manifest-driven PowerPoint template engine. Its legacy Edit path extracts text and reconstructs files. It does not provide target selection, a draft preview, approval before publication, or verified preservation of unselected content.

The current build produces an unsigned Nuitka onefile executable. The agreed installer and portable ZIP are future deliverables. Documentation of a requirement is not evidence that the application meets it.

This file governs the new product requirements. [The archived v1.2 PRD](docs/archive/PRD_v1.2.md), `docs/Simplicitor_PRD_v1.2.docx`, and [the original implementation guide](docs/Simplicitor_Implementation_Guide.md) remain historical references. New user decisions supersede historical scope restrictions. [Project status](docs/PROJECT_STATUS.md) records implementation evidence and remaining decisions.

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

1. A nontechnical user with working local Ollama can install and launch without Python, a terminal, or agent configuration.
2. Installer launch, application launch, local model connection, upgrade, and uninstall pass on clean Windows test environments. Record the tested versions and any security warning or block.
3. Installer and portable ZIP contain the same tested application resources and work independently of a development checkout.
4. Exact targets and original values are validated. Ambiguous, stale, or unsupported edits cannot silently proceed.
5. Approved replacements are correct, and preservation fixtures show that unaffected content, formulas, styles, media, and relationships survive.
6. IDs with leading zeroes remain text with the same identity and associations. Calculations use supplied inputs and deterministic computation.
7. The candidate opens in Microsoft Office without a repair prompt, and preview identifies relevant reflow or overflow.
8. Approval applies to the reviewed candidate version. Failure, rejection, or cancellation does not change the original or publish incomplete output.
9. Network and logging checks show local processing and no document-content leakage for the tested configuration.
10. Existing generation and template behavior remains covered by regression checks.

## Decisions still needed

- Preview technology, fidelity expectations, and whether installed Microsoft Office is required.
- Supported rich-text and Office feature envelopes for each editing format.
- Candidate naming, version identity, storage, retention, and cancellation behavior.
- Tested model/runtime combinations and practical hardware requirements.
- Exact Windows or antivirus detection blocking the current executable.
- License terms that permit the intended business use. The existing PolyForm Noncommercial license remains unchanged until Alex decides otherwise.

## Work outside this scope

A general-purpose agent, a chat platform, persistent agent memory, a RAG system, model management, cloud services, plugins, batch automation, automatic updates, PDF write-back, and Mac/Linux support are not part of the agreed first scope. Any expansion requires an explicit user decision. Packaging and selective editing are separate implementation workstreams; approving these documents does not authorize publication or unrelated features.
