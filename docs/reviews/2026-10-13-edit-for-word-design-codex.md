# Codex review: 2.3.0 Edit for Word technical design

Reviewed 2026-10-13. Design: [Draft 1](../superpowers/specs/2026-10-13-edit-for-word-design.md), commit `5bf4d31522efb8c431bacaa527efd55a45f0fc48` on `spec/2.3.0-edit-word`. Code and requirements baseline: main `909030844d08452cb88bba41d4d2d2b115284d54`. Inputs: [PRD preservation contract](../../PRD.md#post-first-release-requirements), [approved mockup](../design/edit-document.html) at `1dd4949`, and the [2.3.0 roadmap](../superpowers/plans/2026-10-12-release-2.2.0.md#after-220-edit-for-word-230-roadmap).

**Revise before writing the implementation plan.** The bounded splice and independent editing package are viable, but the current rules can admit edits inside protected ranges and change bookmark meaning while passing verification. There are also concrete XML-construction failures and mismatches with the approved reading/review flow. Findings F1 and F2 are P1; F3 to F8 are P2; F9 is P3. D1, D2 and D3 remain settled and unchanged.

## Numbered findings

### F1. P1: editability must include ranges crossing paragraph boundaries

**Evidence:** Design lines 94 to 100 classify each paragraph from its own children and descendants. A complex field can begin and separate in paragraph 0, have plain result text in paragraph 1, and end in paragraph 2. The middle paragraph contains only allowed `w:r/w:t` and its text matches python-docx. It is therefore editable under these rules despite being a field result. A comment range beginning in paragraph 0 and ending in paragraph 2 has the same defect. The synthetic probes produced `[read-only, editable, read-only]` for both cases.

Changing that field result can be undone when Word updates the field; changing commented text violates the agreed read-only rule. None of the six checks looks at the containing range, so re-scanning with the same local rules does not catch it. Complex fields and comment anchors are story-level constructs, not necessarily confined to one paragraph. See Microsoft's [FieldChar](https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.wordprocessing.fieldchar?view=openxml-3.0.1) and [CommentRangeStart](https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.wordprocessing.commentrangestart?view=openxml-3.0.1) descriptions.

**Correction:** During the opening scan, track nested complex fields and comment ranges across the main story, including intervening body blocks. Mark every intersecting body paragraph read-only with the existing field/comment reason. Treat unmatched or ambiguous range boundaries conservatively. Check editability using that same range information after patching. Add three-paragraph field and comment fixtures, including a selection containing only the unmarked middle paragraph. This does not change D3: Track Changes being enabled remains allowed.

### F2. P1: bookmark relocation changes meaning and contradicts check 6

**Evidence:** Design line 156 moves all starts to the beginning and all ends to the end of an output paragraph. Three synthetic cases expose different failures:

- Two disjoint inline bookmarks have the original marker order `start A, end A, start B, end B`. The specified patch produces `start A, start B, end A, end B`. Check 6 rejects an otherwise ordinary edit because the marker order changed.
- A bookmark around only `30 days` in `Pay within 30 days of receipt.` expands to the entire rewritten sentence. The proposed text is correct, the marker bytes/order are unchanged, and **all six specified checks pass**. A REF field or navigation target using that bookmark now addresses a different range. Byte preservation of the field's part does not preserve the intended bookmark boundary.
- A bookmark start in the gap between two selected paragraphs is retained by line 148. It is inside the replacement but is not a marker belonging to either selected paragraph. Check 6's expected marker set excludes it: the probe has two markers in the splice interval but only one in the selected paragraphs.

Monotonic source indices do not establish bookmark boundary semantics or preserve marker order. The standard also requires a matching start to precede its end in document order; see [BookmarkEnd](https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.wordprocessing.bookmarkend?view=openxml-3.0.1).

**Correction:** Define the supported bookmark policy before the plan. The smallest first-release policy is to support unambiguous paragraph-boundary bookmarks, retaining their ordered markers, and make paragraphs with inline or ambiguous bookmark boundaries read-only with a reason. Do not silently relocate a dropped source's markers: reject a proposal when their correct placement cannot be preserved. This retains the demonstrated bookmarked-heading case without requiring a general bookmark editor. If inline bookmarks are retained instead, their text offsets need explicit alignment rules and a safe refusal for ambiguous mappings.

Change check 6 to compare the ordered raw marker stream from the entire original `[S,E)` interval, including gaps. Also verify pairing/document order against markers outside the interval. Add the three cases above and a bookmark crossing the selection boundary. Keeping marker bytes alone is insufficient.

### F3. P2: replacement construction is incomplete for empty paragraphs and alternate prefixes

**Evidence:** Line 150 promises to reuse the paragraph's namespace prefix, including an empty prefix. Lines 154 and 157 then prescribe literal `<w:p>`, `<w:r>`, `<w:t>`, `<w:tab/>` and `<w:br/>`. Synthetic packages using only an `x:` binding or a default WordprocessingML namespace open in python-docx. Using the table's literal generated runs makes Expat reject the candidate with `unbound prefix`.

An original `<w:p/>` also opens correctly. Reusing its complete start-tag bytes and appending runs plus `</w:p>`, as line 154 prescribes, produces a mismatched closing tag. The map can locate this paragraph correctly while the builder still fails. Both cases are already promised in the design's test matrix. Check 3 catches the failures before saving, but it does not make those edits work.

**Correction:** Specify one namespace-aware name builder for every generated element, using a binding valid at the splice location. Normalize a reused self-closing paragraph tag into an opening tag while preserving its attributes. Keep this byte change inside the selected paragraph. Test both replacing and splitting default-prefix, alternate-prefix and self-closing paragraphs through all six checks, not only through the opening scanner.

### F4. P2: inserted paragraphs copy structural properties prohibited by the roadmap

**Evidence:** Design line 155 copies all `w:pPr` bytes for every output from the source. The roadmap says inserted paragraphs never copy section or structural properties. The editability rules exclude `w:sectPr`, but allow an explicit `w:pageBreakBefore`. Splitting such a paragraph into two outputs duplicates that property. The synthetic result opens and python-docx reports `page_break_before == True` for both paragraphs: the second paragraph acquires a new forced page break. The six checks accept this.

**Correction:** Distinguish the first retained output's properties from additional paragraphs. Retain the original properties on the first output; define the smaller formatting/list property set allowed on additional outputs, excluding explicit page-break and other structural/positioning properties. Alternatively refuse count-changing proposals for paragraphs carrying unsupported structural properties. State which rule applies so the plan does not invent it. Add a split fixture with `pageBreakBefore`, alongside the existing section-break refusal and ordinary list continuation tests.

### F5. P2: reading and review omit formatting the approved mockup shows

**Evidence:** Line 104 uses direct bold/italic and a list marker when `w:numPr` is set, without defining style inheritance. A normal `List Bullet` paragraph created using the installed python-docx has no direct `pPr/numPr`; its style does. A run using the built-in `Strong` character style has `run.bold is None` while the style is bold; a synthetic italic paragraph style likewise leaves `run.italic is None`. Testing only direct properties misses these cases even outside headings, whose display markup may supply bold independently.

There is a second mismatch: line 235 explicitly says review does not show formatting, and `EditCandidate` carries before/after texts only. The approved mockup's `renderComparison()` calls the same `makeContent()` used by the reading view, with bold, italic, headings and list markers. Its payment example shows the changed number in bold on both sides. A plain-text review cannot reveal the mixed-formatting loss acknowledged by the design.

**Correction:** Resolve the effective bold/italic and numbering needed by this limited reading view, including paragraph/character style inheritance and explicit off values. Carry display spans into Before and After; derive After from the actual verified candidate, using the same limited display renderer. Add D2's green word highlight independently of bold/italic. This requires no full Word layout renderer. Add inherited-list, inherited-bold/italic and explicit-override fixtures, and verify that review displays the formatting actually saved.

### F6. P2: save checks happen before the commit window and leave failure transitions undefined

**Evidence:** Lines 183 to 185 check the source hash, then stage/read back the output, then replace the destination. A synthetic interleaving changed the original after the successful hash check but before replacement. The sequence still saved the output. A second interleaving changed an already-confirmed destination after overwrite confirmation; the unconditional replace overwrote those newer contents without another confirmation. These are simulations of the specified sequence, not tests of an existing editing implementation.

The design also defines the hash-mismatch transition but not what happens when the original is deleted, moved or becomes unreadable. The current `jobs.same_path` correctly recognizes normalized paths and existing aliases; it is suitable for the guard, but it is only a check at the time it runs.

**Correction:** Freeze the source identity/path with the opened document and define an optimistic save commit point. After staging/read-back, immediately recheck the original hash and the original-destination guard before replacement. On mismatch, missing original or failed source recheck, save nothing and give an actionable reopen message. Specify whether the candidate is discarded for each case.

Freeze the destination's existence/content state when Save As and any overwrite confirmation are accepted. If it changes before commit, require a new confirmation instead of replacing it silently. Add synthetic interleaving tests and ensure failures preserve the destination and clear temporary output. Describe these as optimistic checks, not protection against every possible concurrent filesystem write; a new locking subsystem is not requested.

### F7. P2: unbounded neighbouring context can make even a tiny selection impossible to edit

**Evidence:** Lines 128 and 136 send up to four complete neighbouring paragraphs, then refuse an over-budget request with advice to select a shorter part. The selected-text limit does not bound those neighbours or the instruction. In the probe, a 19-character selection with one 40,000-character neighbouring paragraph estimates **20,416 tokens before even adding the system prompt**, exceeding `num_ctx=16384`. Shortening the selection cannot solve this refusal.

**Correction:** Keep the chosen limits and estimate. Define context as optional and fit it within the remaining budget after the system prompt, instruction, selected paragraphs and reserves. The simplest rule is to omit whole neighbouring paragraphs that do not fit, in a deterministic order, without shortening the selected content. If the core request still does not fit, distinguish an oversized instruction from an oversized selection in the message. Test a short selection next to a long paragraph, an overlong instruction, and a genuine core-request refusal.

### F8. P2: the response minimum does not enforce the stated no-whole-selection-deletion rule

**Evidence:** Line 138 says deletion of the entire selection is impossible because at least one paragraph is required. For two nonempty selected paragraphs, `{"paragraphs":[{"source":0,"text":""}]}` passes the described schema, source-order, XML-character and no-change validation rules. It produces one empty paragraph, and the count check `2 - 2 + 1` passes. The entire selected text has disappeared even though one paragraph node remains.

**Correction:** Explicitly enforce the stated scope rule: when the original selection contains non-whitespace text, reject a proposal whose complete output is whitespace-only. Keep legitimate blank paragraphs within an otherwise nonempty proposal, and allow filling an originally blank paragraph. Add both cases to proposal validation and the model-check corpus. This leaves D1 unchanged.

### F9. P3: make the already-decided format/settings checks explicit

**Evidence:** Line 71 attributes Strict exclusion to the main-part content type. That predicate alone does not establish the XML namespace or the package relationship vocabulary. Strict uses different namespace/relationship identifiers; Microsoft's [SDK description](https://learn.microsoft.com/en-us/office/open-xml/about-the-open-xml-sdk) explains the namespace conversion required to read it. A content-type check should not be the only specified conformance check.

Line 78 also describes `w:trackRevisions` presence as the Track Changes flag. Its on/off value must be interpreted: an explicit false value is not enabled Track Changes, as Microsoft's [TrackRevisions example](https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.wordprocessing.trackrevisions?view=openxml-3.0.1) shows. This is a parsing detail of D3, not a request to reconsider it.

**Correction:** Explicitly require the supported Transitional main-document namespace and package relationship type before body mapping, giving the existing standard-docx refusal for Strict. Parse OOXML on/off values for Track Changes and protection, including absent/default and explicit false values. Add refusal and settings fixtures. Keep the current format exclusions and D3 notice text.

## What is sound and what the six checks establish

| Area | Assessment |
|---|---|
| Byte map and splice | The quote-aware Expat byte-index recipe worked on the synthetic UTF-8 BOM, multibyte text, escaped entities, CDATA, CRLF, attribute `>`, empty-element and body comment/PI probe. Counts and editable text comparisons provide useful independent guards. Keep byte offsets distinct from decoded-text offsets. F3 concerns construction, not a reproduced scanner mislocation. |
| Preservation contract | Comparing every other decompressed package part and exact main-part prefix/suffix is the right boundary for the PRD. Rebuilding ZIP compression does not itself change an OOXML part's content. No whole-part serialization or COM-saved candidate is needed. |
| Checks 1 and 2 | Establish the unedited-byte boundary when measured against the frozen original and selection. They do not establish the meaning of moved markers inside the selection. |
| Checks 3 and 4 | Reject malformed XML and establish python-docx readability/counts. They are not an Office schema or Word-openability proof. The one-off native check remains separate. |
| Checks 5 and 6 | Re-scanning is useful, but repeats the editability omissions in F1. F2 shows both a false acceptance and false rejections in the bookmark rule. Strengthen these specific invariants rather than assuming another parse proves preservation. |
| Existing anchors | Direct body paragraph indices match `source_readers._read_blocks` and `Document.paragraphs`; table/display positions must remain separate. Headers/footers remain their own read-only containers. |
| Existing OllamaClient | `generate(..., output_format=..., options=..., think=False, local_only=True)` is supported. The local route already disables environment proxies, checks loopback, validates `prompt_eval_count` against the supplied context/output limits, and rejects output-limit responses. Use safe editing messages; never log those exceptions' response payloads. |
| Worker/UI ownership | Frozen setups, one action per worker, cancellation checks around HTTP, terminal/finished signals, late-result rejection and an uncancellable accepted save fit the established pattern. Busy mode/settings/file gates and pick-before-discard are consistent with the approved flow. |
| Formatting policy | Copying original `rPr` for unchanged text and giving changed text a deterministic source style is implementable. The deliberately limited policy is not exact Word layout fidelity. F4 and F5 address structural-property copying and whether the user can see the result. |
| Model gate | The fixed 12-task, 11/12-per-candidate threshold and zero verification failures are clear enough to plan. Freeze task labels and attempt seed, record settings/model identity, and run the actual candidate builder for the gate. Keep labels out of requests and report both candidates. A different seed permits variation but does not guarantee a different proposal. No live gate was run in this review. |

The blanket refusal of paragraph-local namespace declarations is conservative and stricter than XML requires. It is defensible for the initial supported subset; do not claim that every such paragraph contains unsafe content. If relaxed later, bindings must be retained on inserted paragraphs and on copied property fragments. This review does not request a general compatibility expansion.

## Verification and limitations

- Inspected the entire design, the approved artifact at `1dd4949`, the roadmap and PRD, and the current reader, OllamaClient, worker and path-guard code. Those application files are unchanged from the reviewed main.
- Ran a throwaway synthetic probe with the existing Python environment and python-docx 1.2.0. Its final run exited 0 with assertions covering the range, marker, namespace, empty-paragraph, byte-offset, inheritance, structural-property, request-budget and save-interleaving examples above. The blank-output example separately checks the described validation conditions and paragraph-count result. These probes exercise stated design rules; there is no editing implementation to qualify yet.
- The single-inline-bookmark candidate was packaged and reopened, and all six checks were reproduced while the bookmark extent changed. Prefix and self-closing failures were reproduced with namespace-aware Expat, rather than inferred from screenshots.
- Scratch scripts, synthetic files and results stay untracked under `.venv/review-edit-word/`. No customer content was used. No live model request, application change, native Office/COM opening, installer, build or qualification action was performed. No tool or dependency was installed.
- The Word spike in the design is Claude's reported evidence, not independently repeated here. No actual LibreOffice or Google Docs export was produced or opened. The future plan should include small synthetic exports from those producers if compatibility is to be claimed; the handwritten XML probes do not qualify their complete output.
- For this documentation-only review, the application suite was not rerun. Review links, whitespace and generated map are checked before committing. Only this review and its generated map entry are changed; the design, plan, mockup, application, main branch, LICENSE and release records are untouched.

The next action is Claude's design correction and Alex's approval. This review does not authorize an implementation plan or application work.
