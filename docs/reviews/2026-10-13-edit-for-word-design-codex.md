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

## Draft 2

Reviewed 2026-10-13: `ef458c46c8ea7b05a77588290456e0918ffca658`, against `5bf4d31`, using only the changes to the [technical design](../superpowers/specs/2026-10-13-edit-for-word-design.md). Line numbers below refer to Draft 2. The earlier review above is unchanged.

**Seven original findings are resolved; F5 and F6 are not resolved.** The original P1 examples are addressed. The corrections introduce a valid-point-comment refusal (F10), specify incomplete formatting resolution (F11), and use an insufficient destination fingerprint (F12). These three P2 issues need correction before planning. F13 is a P3 correction to the new budget claim, not a request to change the limits or algorithm. D1 to D3 were not reopened.

### Resolution of F1 to F9

| Finding | Result | Reason |
|---|---|---|
| F1 | Resolved | Lines 94, 106 and 198 add whole-story field depth/comment state to opening and verification. The balanced three-paragraph field and comment probes now mark all three paragraphs read-only, including the plain middle paragraph. The new rejection of every unmatched comment endpoint introduces the separate F10 regression. |
| F2 | Resolved | Lines 109, 114, 163, 173, 182 and 199 replace general relocation with a boundary-only policy, reject dropping a marker-bearing paragraph, retain markers on its continuation, and compare the entire splice interval including gaps. The original inline-bookmark extent/order examples are now read-only; boundary and gap markers retain their ordered stream. The collapsed `_GoBack` exception retains a zero-length range and its order rather than expanding it over rewritten text. |
| F3 | Resolved | Lines 179 and 180 use one recorded prefix for every generated element and convert self-closing paragraphs to opening/closing tags. Replace-and-split probes for `x:`, the default namespace and `<w:p/>` produce well-formed XML and reopen with the two expected paragraphs. |
| F4 | Resolved | Line 181 separates the continuation's verbatim properties from the added paragraph's explicit allow-list. The original direct `pageBreakBefore` example now retains that property only on the continuation. The corresponding synthetic outputs report direct page-break values `[True, None]`. |
| F5 | Not resolved | Lines 124, 203 and 207 fix the missing display blocks and derive After from the verified bytes, which resolves the text-only-review mismatch. However, the new effective-formatting rule uses fallback lookup where character-style toggle composition is required, and its numbering predicate does not explicitly respect `numId=0`. F11 gives the counterexamples and correction. |
| F6 | Not resolved | Lines 209 to 224 correctly move source/path checks after staging, freeze the original path, define missing/unreadable-original outcomes, and preserve the candidate for a destination retry. But destination size and modification time are not a content fingerprint. A changed destination can match both recorded values and still be overwritten. See F12. |
| F7 | Resolved | Lines 134, 159 and 244 bound the instruction and make context optional, fitted against the actual serialized-request estimate. The 40,000-character neighbour is skipped while the small core fits. A genuine core refusal now allows shortening either the description or selection. The new assertion that the character limits guarantee a fit needs the narrower wording in F13. |
| F8 | Resolved | Line 163 explicitly rejects all-whitespace output for a selection containing text, while preserving blank paragraphs in a nonempty proposal and allowing a blank original to be filled. Those three validation cases pass the synthetic rule checks. |
| F9 | Resolved | Lines 79 and 86 explicitly check the Transitional relationship/root namespace and distinguish true/false values. Treating omitted protection enforcement conservatively as on matches Microsoft's documented Word behaviour, even though the ISO default differs; see [Word's protection deviation](https://learn.microsoft.com/en-us/openspecs/office_standards/ms-oi29500/e12d2773-e2d0-45bf-b1c2-b8f0548e156d). No D3 or format-scope change is requested. |

### F10. P2: the new range scan rejects valid point comments

**Evidence:** Lines 84 and 94 reject a comment end without a start and anything still open at the story end. OOXML permits either a lone `commentRangeStart` or a lone `commentRangeEnd` as a point anchor when the matching comment reference exists. Microsoft's [CommentRangeStart](https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.wordprocessing.commentrangestart?view=openxml-3.0.1) and [CommentRangeEnd](https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.wordprocessing.commentrangeend?view=openxml-3.0.1) rules explicitly distinguish these from nonconformant missing references.

Both synthetic packages have a real comment part, matching reference, one point marker, and an unrelated body paragraph. They reopen in python-docx. The literal Draft 2 scan refuses the entire file in both cases; the start-only case also incorrectly treats the unrelated following paragraph as part of an open comment range. Draft 1's local read-only checks did not impose this whole-file refusal. This is a regression introduced by the F1 correction, not a request to support editing comments.

**Correction:** Distinguish paired comment ranges from valid point anchors using the collected marker/reference IDs before computing range coverage. Paired ranges still protect every intersecting paragraph. Point anchors and their reference paragraphs remain read-only locally and do not open a range to the story end. Keep refusal for genuinely invalid or ambiguous associations. Add start-only and end-only point fixtures alongside the balanced multi-paragraph case.

### F11. P2: the new display resolver needs composition and explicit numbering cancellation

**Evidence:** Line 124 describes direct formatting followed by character-style, paragraph-style and defaults fallback. Bold and italic in character styles are toggle properties, so selecting the first present `true` is insufficient. The saved synthetic fixture has no direct bold and a derived character style with bold on based on a character style also having bold on. Draft 2's first-hit rule returns bold on; composition of those two character-style toggles from an off base gives off. See the primary [python-docx toggle-property analysis](https://python-docx.readthedocs.io/en/latest/dev/analysis/features/text/font.html#toggle-properties) and Microsoft's [Bold definition](https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.wordprocessing.bold?view=openxml-3.0.1). This is a rule/fixture comparison, not a new native-Word rendering result.

The numbering sentence also allows a list marker when the paragraph's own **or** inherited `numPr` has a non-zero ID. A synthetic `List Bullet` paragraph has direct `numId=0` and inherited `numId=1`. That OR predicate shows a bullet despite the direct cancellation. Microsoft defines [numId zero](https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.wordprocessing.numberingid?view=openxml-3.0.1) as removing numbering at that hierarchy level. If the sentence intended ordered fallback instead, the zero case must be stated explicitly so the plan does not fall through to the style.

**Correction:** Specify a Word-compatible composition of defaults, paragraph formatting and character-style chains, applying direct bold/italic last as absolute overrides. Account for toggle semantics instead of a first-present boolean lookup; retain the limited bold/italic display scope. Resolve numbering in precedence order and treat an explicit zero as cancellation, not absence. Add double-character-toggle, direct on/off override and direct-zero-over-list-style fixtures to both reading and candidate-derived review checks. Include the toggle fixture in the already-planned native Word check; no new runtime renderer is requested.

### F12. P2: destination metadata alone does not detect changed contents

**Evidence:** Line 209 records only size and modification time; line 213 compares that state at commit. The probe creates a valid destination DOCX containing `Value 30`, records its state, and replaces its contents with a valid same-length DOCX containing `Value 45` while preserving its modification time. Even using nanosecond timestamps, both metadata values match while SHA-256 differs. The Draft 2 guard therefore authorizes overwriting the new contents. No write needs to occur in the acknowledged check-to-replace race window: this change is complete before the commit check.

**Correction:** Include the destination content digest in the frozen state for an existing destination and compare it immediately before replacement. Continue distinguishing an absent destination from an existing one. A changed digest uses the already-written destination-retry outcome, keeping the candidate and requiring Save As/confirmation again. Retain the optimistic-check caveat and source recheck; no locking subsystem is needed. Add this same-size, same-time, changed-content case to the save tests.

### F13. P3: character limits do not guarantee that the core request fits

**Evidence:** Line 159 newly claims the 6,000/2,000-character limits guarantee a fit for text using at most three UTF-8 bytes per character. The core also includes per-paragraph indices and style metadata, which those text limits do not bound. A synthetic core with 1,000 paragraphs, just `Example` in the first and the others blank, has only **1,006 selected characters including paragraph separators**, a 16-character instruction, and all-ASCII text. Even using compact JSON and a short system prompt, its serialized estimate is **20,770.8 tokens**, above 16,384. A longer system prompt cannot make it fit. The runtime defensive estimate catches this, so the algorithm remains safe.

**Correction:** Remove the guaranteed-fit assertion. State that ordinary selections usually fit and every core request is checked after serialization, including metadata. Retain the current refusal, limits and optional-context algorithm. Add one normal-settings metadata-heavy core refusal to the budget tests instead of covering core refusal only with reduced test settings. No extra paragraph-count limit is requested.

### Draft 2 verification and boundary

- Reviewed `git diff 5bf4d31 ef458c4 -- docs/superpowers/specs/2026-10-13-edit-for-word-design.md` and the affected definitions in context. Application code, the plan, mockup and decisions were not reassessed for unrelated gaps.
- Ran the scratch probe `.venv/review-edit-word-draft2/probe_draft2.py` with the existing Python environment. Its final run exited 0. Assertions cover balanced story ranges, both point-comment refusals, corrected prefix/self-closing construction, ordered boundary/gap markers, the explicit structural-property split, character-style composition, numbering cancellation, the destination fingerprint counterexample, context fitting and blank-output validation.
- The scratch XML/package rules are approximations of the design, not an implemented editing engine. Package reopening proves python-docx readability, not native Word rendering or all six product checks. No source-suite run, live model request, Word/COM call, producer export, application change, dependency installation, build or qualification was performed. Claude's second spike remains reported evidence rather than independently repeated native acceptance.
- D1 to D3, unchanged byte-map/splice behaviour, and unrelated capture/formatting gaps were set aside as outside this revision's review. The new findings arise only from Draft 2's corrections. Synthetic scripts/files/results remain ignored under `.venv/review-edit-word-draft2/`.
- Append-only review change; regenerate the map and verify links/whitespace before commit. The design, code, LICENSE, main and release records remain unchanged. Correct the three P2 issues and F13's wording before the next approval decision; this review authorizes neither planning nor implementation.

## Draft 3

Reviewed 2026-10-13: `c0428f757f8604bb1620f560b1bb95142d3af819`, against `ef458c4`, using only the changes to the [technical design](../superpowers/specs/2026-10-13-edit-for-word-design.md). Line numbers below refer to Draft 3. The earlier review sections are retained as historical findings.

**One P2 correction remains: partial numbering overrides (F14).** F10, F12, F13 and the open part of F6 are resolved. The bold correction in F11 is confirmed in Word; the numbering correction handles explicit zero but introduces the F14 regression, leaving F5/F11 incomplete as written. No new preservation defect was found in the changed comment, fingerprint or budget rules. D1 to D3 and previously resolved findings were not reopened.

### Resolution of the requested findings

| Finding | Result | Reason |
|---|---|---|
| F5, open part | Not resolved | Candidate-derived Before/After display remains specified correctly. The corrected bold rules pass the native Word controls below, but the new whole-`numPr` precedence rule can omit a bullet that Word displays. F14 prevents closing the remaining display-fidelity requirement. |
| F6, open part | Resolved | Lines 220 and 224 freeze an existing destination's SHA-256 and compare it at the commit point, retaining the source/path rechecks and explicit retry/discard outcomes. This closes the outstanding content-fingerprint issue without adding locks. |
| F10 | Resolved | Line 96 pairs comment markers first, treats a lone start/end with its reference as a point rather than an open range, and refuses reversed/repeated associations. Synthetic start-only and end-only cases now keep the anchor paragraph read-only and the unrelated following paragraph editable; a balanced three-paragraph range still protects all three. |
| F11 | Not resolved | Lines 128 to 133 resolve inheritance within each style chain, combine paragraph/character values across levels and apply direct formatting absolutely. Word 16 confirms the stated bold outcomes; my earlier contrary same-chain expectation is withdrawn. Explicit `numId=0` cancellation now works, but line 135 introduces the partial-override problem in F14. |
| F12 | Resolved | The digest distinguishes the two valid same-size/same-time DOCX contents from the previous counterexample. The scratch check detects the changed digest, so the written destination-retry outcome applies. |
| F13 | Resolved | Line 170 removes the guaranteed-fit assertion and explicitly includes serialized metadata in every core estimate. The test matrix now includes a metadata-heavy refusal at normal settings. The 1,000-paragraph example is correctly refused without changing the approved context or character limits. |

### Word evidence and correction of my earlier F11 example

I opened a synthetic seven-paragraph DOCX read-only in a separate Word instance and queried the paragraph ranges through the existing Word object model. Word reported version **16.0**, build **16.0.20326**. The first three controls gave:

| Synthetic case | Word `Range.Font.Bold` | Result |
|---|---|---|
| Bold character style B based on bold character style A, on a normal paragraph | `-1` | Bold |
| Bold paragraph style plus bold character style A | `0` | Not bold |
| Bold paragraph style with direct bold off | `0` | Not bold |

This independently confirms Claude's central distinction between inheritance within a character-style chain and the interaction of paragraph/character formatting. **My Draft 2 expectation that the two bold character styles in one chain would display as not bold was wrong for Word 16. I withdraw that part of F11.** The implementation tests should use the Word-qualified result in Draft 3, not my earlier reference calculation. This review does not challenge the remaining unchanged formatting coverage with new cases.

### F14. P2: whole-`numPr` precedence loses inherited numbering on partial overrides

**Evidence:** Draft 3 line 135 says a direct `w:numPr` decides, with style inheritance considered only when there is no direct `numPr`. A `numPr` can supply a level without a `numId`, or have no children. Selecting the first whole block loses a list ID supplied by the paragraph style.

The fixture uses the built-in `List Bullet` style, whose style properties contain `numId=1`. Word's native `Range.ListFormat` measurements were:

| Direct paragraph numbering properties | Draft 3 whole-block interpretation | Word `ListType` | Word result |
|---|---|---|---|
| No direct `numPr` | Inherit style ID | `2` | Bullet |
| `<w:numPr><w:ilvl w:val="0"/></w:numPr>` | Direct block has no ID, so no list | `2` | Bullet, level 1 |
| `<w:numPr><w:numId w:val="0"/></w:numPr>` | Cancel list | `0` | No list |
| `<w:numPr/>` | Direct block has no ID, so no list | `2` | Bullet |

`ListString` was nonempty for all three bullet cases and empty for explicit zero. These are Word-based results, not a standards-only inference. A literal reference implementation of line 135 predicts list flags `[True, False, False, False]`; Word gives `[True, True, False, True]`. Draft 2's own-or-style predicate displayed the inherited bullet in the partial/empty cases, so the new block-level precedence introduces this regression while fixing zero cancellation. It affects the reading view and candidate-derived review; the saved OOXML can still display the bullet correctly in Word.

**Correction:** Resolve the effective `numId` by the first *present `numId`* in direct properties and then the paragraph style chain, rather than by the first present `numPr` container. A present zero stops inheritance and cancels the list; a missing `numId` continues inheritance. A direct `ilvl` overrides a level, not the list ID, and an empty `numPr` supplies no override. Apply the same component fallback to partial style-chain properties. Add level-only and empty-direct-`numPr` fixtures to reading and Review After tests, retaining the existing explicit-zero and inherited-list cases. No new numbering feature or full layout renderer is requested.

### Draft 3 verification and boundary

- Reviewed `git diff ef458c4 c0428f7 -- docs/superpowers/specs/2026-10-13-edit-for-word-design.md` and the changed definitions/test matrix in context. No unrelated design gap, resolved preservation finding or D1 to D3 decision was reassessed.
- Scratch checks in `.venv/review-edit-word-draft3/probe_draft3.py` exited 0: both point-anchor cases, balanced range protection, reversed/repeated comment rejection, digest detection despite equal destination size/time, normal-settings metadata refusal, and comparison of the native Word results with the written numbering rule.
- The successful native probe used the already-installed Windows PowerShell/Word COM interface. It opened only the synthetic fixture with `ReadOnly=true`, did not add it to recent files, requested no repair, saved nothing through Word, and closed without saving. The fixture SHA-256 before and after was `6876d4fe346f83e6071b7901872ca09ad145b3ef243699b9154ccdb5cc5b3b4f`. Its final run exited 0; a subsequent process check confirmed zero remaining Word processes. No existing user document or running Word instance was attached.
- Synthetic inputs, scratch scripts and measured JSON remain ignored under `.venv/review-edit-word-draft3/`. No tool/dependency installation, source-suite run, live model request, application/code change, installer, build or qualification action was performed. This small Word check establishes these formatting outcomes, not overall editor or producer compatibility.
- Only this review append and regenerated map metadata are committed. The design, application, plan, mockup, LICENSE, main and release records remain unchanged. Correct F14 before treating the design as ready for the implementation-plan approval step; no plan or implementation is authorized by this review.
