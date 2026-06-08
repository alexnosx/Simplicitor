# How Simplicitor Was Built

## The hypothesis

Every serious attempt at local AI tooling for non-technical users eventually collides with the same wall: after a user installs Ollama and pulls a model, there is nowhere productive to take it. The chat interfaces — Open WebUI, LM Studio, Jan.ai, GPT4All — are well-executed, but chat is the commodity. What is missing is output: a file, a document, something that exists outside the terminal and can be taken to a meeting or sent to a colleague.

The hypothesis was that a narrow, well-scoped tool — one that turns a local LLM into a document production interface, nothing more — was both buildable and useful. The secondary hypothesis was that this could serve as a real test of AI-assisted development at a scale beyond toy projects. Both turned out to be true.

## PRD-first approach

No code was written until there was a signed-off PRD. The v1.0 document specified the target user, the core flows, the file types in scope, the explicit out-of-scope list, and the LLM contract design. It was iterated to v1.2 against three kinds of pressure: scope creep ("what if we added PDF write-back?"), user empathy gaps ("what does a non-technical user actually see when Ollama isn't running?"), and architectural stress tests ("what happens if the LLM returns malformed JSON?").

The most valuable section of the PRD turned out to be "What we are NOT building." Listing chat history, RAG, model management, plugins, cloud sync, and dark mode as explicit non-goals before implementation started meant those conversations never happened mid-build. Every potential scope addition could be answered with a reference to that section rather than a fresh negotiation.

## Six phases of implementation

**Phase 1 — Skeleton.** Main window, two-panel layout, settings dialog, config system. The goal was a runnable shell with correct structure before any real functionality. Getting the PySide6 threading model right (QThread with worker objects, never touch UI from a worker thread) happened here, which prevented a category of bugs in every subsequent phase.

**Phase 2 — Ollama connection.** REST API integration, connection status indicator, model selector, 5-second polling loop. The connection polling design — reconnect silently, show the user a non-blocking status indicator rather than a blocking error — defined the app's resilience behavior.

**Phase 3 — File generation.** Word, Excel, and PowerPoint generation from natural language prompts. The LLM contract was designed here: simple JSON schemas with content and structure only, Python handles all formatting. This decision was the most consequential of the project.

**Phase 4 — File upload and manipulation.** Drag-and-drop file loading, text extraction, manipulation pipeline, one-to-one backup logic. PDF was added as read-only input. This phase introduced the manipulation scope problem — see Notable bugs below.

**Phase 5 — Polish.** Error UX, dismissible banners, model capability guidance, edge case handling, icon integration. This phase took longer than expected because the gap between "technically functional" and "usable" turned out to be substantial.

**Phase 6 — Packaging.** Nuitka compilation, resource bundling, build script. Hit the python-pptx template gotcha here (see Notable bugs). Produced the final single-file `.exe` at approximately 30 MB.

## Key architectural decisions

**LLM contract design.** The LLM produces content and structure. Python handles all formatting, colors, and layout. This constraint exists because asking a small model to produce complex styling JSON alongside content produces unreliable output. Keeping the contract simple — document text, section headings, table rows, bullet points — means a 4B model can succeed where a complex schema would fail. The LLM is responsible for what the document says. Python is responsible for how it looks.

**Scope detection on manipulation.** The manipulation pipeline can change text and structure. It cannot change themes, colors, or visual styling — those require format-level operations that Python-docx and python-pptx do not expose through the text extraction path. The failure mode without scope detection is silent: the LLM would process the prompt, return something, Python would write the file, and the user would see a green success banner on an unchanged file. The fix was a keyword-based scope check at the top of the manipulation worker, before any file is touched. Out-of-scope prompts are rejected with a clear explanation. No backup is created. No UI flicker.

**One-to-one backup logic.** A backup is created on the first manipulation of a file. Subsequent manipulations of the same file reuse the existing backup. The backup always represents the original, unmodified state. This prevents version sprawl and makes the backup semantically meaningful rather than just the previous iteration.

**Model capability guidance.** Sub-7B models trigger a non-blocking informational banner explaining that the model is lightweight and complex prompts may degrade. The app does not block generation. Users are informed and trusted to make their own choice. Gatekeeping small models would break the experience for users with limited hardware.

**Nuitka over PyInstaller.** Nuitka compiles Python to C and links a real binary. PyInstaller produces a self-extracting archive that unpacks at runtime. The Nuitka binary is smaller (~30 MB vs 80–150 MB for equivalent PyInstaller output), starts faster, and produces dramatically fewer antivirus false positives because it does not look like a packed executable.

## Notable bugs and learnings

**The silent success bug.** The manipulation pipeline accepted out-of-scope prompts, processed them, and returned a success banner on an unchanged file. This was caught during testing — "change the theme color to blue" produced a green confirmation message on a file that was byte-for-byte identical to the input. The bug was not a crash, which made it worse: users would trust the confirmation, open the file, and discover nothing had changed. The fix was the scope check described above.

**The python-pptx template packaging gotcha.** In development, python-pptx loads a default template from its own package directory when you create a new presentation. Inside a Nuitka onefile executable, that package path does not exist. The symptom was PowerPoint generation working in development and silently failing in the compiled binary. The fix was to bundle a copy of the default template as a data file and pass its path explicitly to `Presentation()` instead of relying on the default.

**Antivirus false positives.** The compiled binary triggered warnings on multiple AV scanners despite containing nothing suspicious. This is a known characteristic of compiled Python — the Nuitka runtime and embedded bytecode match heuristic patterns for packed executables. The long-term fix is EV code signing, which establishes publisher reputation with Microsoft SmartScreen and the major AV vendors. Short-term, the binary was submitted to Microsoft's malware analysis portal and the warning cleared within 48 hours.

## What this project taught me

**PRD before code.** The time invested in the PRD before touching a keyboard paid back at every phase. Architectural decisions made in prose are cheap. The same decisions made in running code are expensive.

**Simple LLM contracts beat complex ones.** The instinct when designing LLM output schemas is to be comprehensive — capture all the styling, all the layout, all the metadata. That instinct is wrong for small models. The right call is the minimum schema that lets Python reconstruct the output faithfully. Complexity in the schema transfers directly to failure rate on smaller models.

**Silent failures are worse than crashes.** A crash is immediately visible. A silent success on an unchanged file is invisible until the user acts on the result. The most important tests to write are the ones that verify nothing happened when nothing should have happened.

**Distribution is harder than development.** Code signing, antivirus reputation, Windows icon caching, packaging quirks — none of these are programming problems, but they all block users from running the software. Budget time for them. They are not edge cases.

**Small models change architecture more than features do.** When you are building for Ollama users who may be running a 4B model on a consumer laptop, every architectural choice that reduces LLM complexity is a feature. The decision to handle formatting in Python instead of prompting for it is not a stylistic preference — it is what makes the app work for the actual target user.

## The role of the human

The human role in this project was PM, architect, code reviewer, and tester. Not coder. The PRD, the scope decisions, the architectural constraints, the UX calls — those came from human judgment. The implementation came from Claude Code.

What AI-assisted development at this scale actually feels like: it is collaborative but not symmetric. The AI is fast, consistent, and does not get bored of boilerplate. The human has to stay oriented — maintaining the mental model of the system, catching the places where an implementation is technically correct but architecturally wrong, and deciding when something that works is not yet something that is good. The human is the product judgment. The AI is the execution.

Approximately 1.4 million tokens of generation went into this project. Zero lines of code were written by hand.

## v1.2 — the template engine

The v1.0 release shipped with PowerPoint generation that built slides from a blank canvas. The result worked, but it never looked like something a designer made. Adding a templated path solved that without trading away the simple-LLM-contract design that made the from-scratch path reliable.

The architecture stayed the same: the LLM produces content and structure only, Python handles styling. The change was where the styling came from. Instead of being controlled by Python code, it is now controlled by a real `.pptx` template. The LLM is given a per-manifest JSON schema (slide types, field names, bullet limits) and a one-shot example assembled from that manifest. It produces validated content. Python renders the content into the template's layouts by placeholder index. The template's masters, layouts, and theme are the source of truth for every visual decision.

The engine was built across 13 phases (A through M), each with its own spec document and implementation plan in `docs/superpowers/`. Notable design calls:

- **Manifest-driven schema.** Adding a template means writing a YAML file that maps slide types to layout indices and fields to placeholder indices. No code change. The same engine runs across all templates.
- **Two default templates shipped:** `business_pitch` (charts 16x9) and `technical_overview`. Both seed into the user's Templates folder on first launch and are restored if deleted.
- **User uploads are first-class.** The picker accepts any `.pptx`. The engine inspects layouts, scores them, strips sample content, and writes a draft manifest. Decks built from hand-placed text boxes (no real placeholders) are rejected with a clear user-facing message.
- **One repair attempt on schema failure.** If the model returns malformed JSON or content that fails validation, the pipeline feeds the specific errors back and tries once more before failing cleanly. No partial output file is written on failure.

The hardest debugging session of v1.2 was a degenerate-output failure on gemma4-class models in the templated path. Ollama's OpenAI-compatible `/v1/chat/completions` endpoint applies grammar-constrained decoding when `response_format=json_object` is set, and smaller models can enter dead-end token states under that constraint. The fix was an opt-in flag (`json_mode`) on `chat_completion`: the templated path opts out and relies on the prompt's JSON instruction plus the existing parse-and-clean path. The non-templated path keeps the default behavior. The diagnostic chain that led to this fix is documented in the commits between `f1022ca` and `3f84d15`.

The other v1.2 lesson was about LLM length guidance. The system message had to be specific about scaling output to input depth — vague phrases like "produce as many slides as the request implies" left small models defaulting to the floor of any range. The final shape gives concrete defaults (8-12 slides), honors explicit length keywords ("brief", "comprehensive", "5-slide deck"), and tells the model to target the upper end of any range. Output sizes now match what the input warrants.
