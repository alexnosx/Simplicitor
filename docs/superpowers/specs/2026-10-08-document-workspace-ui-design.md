# Simplicitor document workspace design

Updated 2026-10-08. UI design proposal with an interactive example, not an implemented application feature. Alex requested committing and pushing the proposal. Application implementation remains a separate task.

## Purpose

Give nontechnical people with local Ollama a consistent way to create and selectively edit confidential Word, Excel, and PowerPoint documents. Contracts, financial workbooks, proposals, policies, and presentations are representative documents. Timesheets are one example, not the product's identity.

The user has endorsed the Edit document and Create new modes and selecting what may change. This proposal develops that direction into a shared workspace. Active product requirements remain in [PRD.md](../../../PRD.md).

## Interactive example

Open [document-workspace.html](../../design/document-workspace.html) in a browser. No server or installation is required. The HTML file is also the editable source of the example.

Use Open document to switch between a Word contract, an Excel forecast, and a PowerPoint briefing. Explore selection, comparisons, draft preview, revision, and approval. Create new demonstrates the same workspace for document generation.

Use sample data only. Responses are preset and do not interpret instructions. The document views are illustrative HTML, not Office renderings. Model readiness and save results are simulated; no AI service is called and no document is written. The standalone example has no external resource dependencies. Drafts and selections survive switching between examples during the current browser session; this is not persistent document storage.

## Shared layout

- Top bar: Simplicitor, Edit document, Create new, a compact local-model state, and Settings. Edit document is the default.
- Document area: approximately 65 percent of the workspace, with file identity, document view, selection highlights, and review tabs.
- Instruction area: approximately 35 percent, with the exact allowed targets, the request, and one primary next action.
- Progress: Choose parts, Review draft, Save new version. Create substitutes Describe document for the first step.
- Appearance: retain Segoe UI, the existing blue accent and light theme, restrained borders, and consistent spacing. Production values belong in `simplicitor/app/config/defaults.py`.

Use a resizable split in the desktop application. At narrow widths, the example stacks the controls; this does not add mobile platform support. Avoid permanent file lists and duplicate connection messages that take space from the document.

## Edit document

1. Open a source file and inspect its supported content without changing it.
2. Select exact targets. Show their identity under Allowed to change. Surrounding context can inform the request without gaining write permission.
3. Describe the modification and choose Propose changes. The production flow validates replacements and patches a separate candidate.
4. Review original and proposed values, then inspect the saved candidate's layout. Changes and Draft preview share the document area.
5. Choose Save new version, confirm the destination, and approve that candidate. Reject source overwrites and output collisions.

Revise request invalidates the previous candidate's approval. Keep the user's request and selection after failure. Switching modes or documents must not silently discard a draft. During processing, show neutral progress and prevent duplicate operations; completion is green, warnings amber, and failures actionable. These processing and failure states are requirements, not demonstrated integrations in the example.

## Format specific selection

| Format | First editing scope | Selection details |
|---|---|---|
| Word | Supported plain text spans or paragraphs. | Show the passage and its location. Reject unsupported rich text rather than flattening it. |
| Excel | Literal cell values. | Show worksheet, address, original value, and type. Preserve text identifiers, unselected formulas, and workbook features. |
| PowerPoint | Supported text spans or existing text shapes. | Show slide and shape identity. Selecting a slide does not authorize every object on it. |

Formula edits, structural changes, chart updates, and layout redesign are outside the initial selective editing scope. Longer text can change Word pagination or overflow PowerPoint shapes. Text comparison alone cannot prove layout or preservation.

## Create new

Reuse the document area, instruction area, review, and save actions. Replace target selection with document type and a request. Preserve existing PowerPoint template generation; do not imply that Word or Excel template engines already exist.

## Implementation boundaries

Retain PySide6, existing shared styling, connection discovery, and QObject workers with QThread signals. Use stacked views for modes and workflow states, a splitter for document and instructions, and format-specific document views behind the shared controls.

Replacing the legacy whole-file reconstruction is essential before the UI can promise selective editing. Preview rendering, support envelopes, candidate identity, retention, and cancellation still need concrete subsystem designs. The preview must render the saved candidate that approval will publish, and source changes must invalidate stale targets and approval.

## Verification

Before committing, check the standalone example's Word, Excel, and PowerPoint selection and review flows, Create mode, revision, mode switching, source-overwrite and output-collision rejection, and browser script errors. Check layout at desktop width and at 360 pixels. Verify documentation links and regenerate the repository map.

These checks demonstrate the design example only. They do not establish Office preservation, model quality, actual local inference, installation, or deployment. Application acceptance remains governed by PRD.md.
