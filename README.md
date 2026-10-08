# Simplicitor

*Windows document work with local Ollama. The next release will focus on confidential, selective editing.*

[![License: Polyform Noncommercial 1.0](https://img.shields.io/badge/license-Polyform%20Noncommercial%201.0-blue)](LICENSE) [![Platform: Windows 10/11](https://img.shields.io/badge/platform-Windows%2010%2F11-lightgrey)](https://github.com/alexnosx/Simplicitor/releases) [![Built with: Python + PySide6 + Ollama](https://img.shields.io/badge/built%20with-Python%20%2B%20PySide6%20%2B%20Ollama-informational)]()

## What it is

The current v1.2 source generates Word, Excel, and PowerPoint files through Ollama, including PowerPoint decks from built-in or uploaded templates. Its legacy Edit workflow extracts text and reconstructs files; it does not yet support verified selective edits or preservation of the rest of a document. Current downloads are unsigned onefile executables.

## Approved next direction

Simplicitor will serve nontechnical Windows users who already have Ollama, a usable local model, and the Microsoft Office desktop applications. It will offer three workflows through two main modes:

| User action | Workflow |
|---|---|
| Create new, with a prompt | Generate a document from the instructions. |
| Create new, with a prompt and source files | Read the sources and create a new document using their information. |
| Edit document | Modify approved parts of an existing document. |

For example, an accounting Excel workbook can supply the facts and calculated figures for a new Word report. In the reverse direction, a large Word or PDF source can supply records for a new Excel workbook with agreed columns and source references. Scanned PDFs require a local OCR/vision path that still needs selection and testing. Source files remain unchanged. Editing changes only approved targets. All three workflows will validate and preview a separate candidate before approval and saving of a new output. Contracts, financial documents, proposals, policies, and presentations are representative uses.

The approved packaging route is a free standalone application with an NSIS installer as the main download and a portable ZIP as the secondary option, distributed through GitHub Releases and linked from `simplicitor.com`. Microsoft Store publication and paid signing are outside this route. Unsigned Windows warnings or blocks can remain.

**These are approved requirements, not shipped features.** Prompt-only generation exists; source-based creation, selective preservation, and the common review workflow still need implementation. See [active requirements](PRD.md), the [architecture proposal](docs/superpowers/specs/2026-10-08-document-architecture-design.md), [UI design](docs/superpowers/specs/2026-10-08-document-workspace-ui-design.md), [packaging](docs/code-signing.md), and [project status](docs/PROJECT_STATUS.md). The current Noncommercial license remains in effect; business-use licensing has not been changed.

Simplicitor is not a chat interface. It is not a RAG tool. It is not a model manager or a general-purpose AI assistant. It does one thing: it turns a local LLM into a document production tool with a file output you can actually use.

## Why this exists

People who already run a local model need a familiar way to work with confidential business documents. Simplicitor aims to make document tasks usable without scripts or agent configuration, while keeping processing local and proposed changes reviewable. The next requirements focus on modifying existing files without losing unselected content.

## Screenshot

![Simplicitor screenshot](docs/screenshot.png)

## Install and run

### Download the binary

Current releases provide an unsigned `Simplicitor.exe` on the [Releases](https://github.com/alexnosx/Simplicitor/releases) page. Windows may warn or block it. An installer and portable ZIP are planned but are not available from the current build workflow. See [packaging and known trust limits](docs/code-signing.md); a new installer alone will not prove that a security detection is resolved.

### Build from source

Requirements: Python 3.11+, Git.

```bat
git clone https://github.com/alexnosx/Simplicitor.git
cd Simplicitor
pip install -r requirements.txt
pip install -r requirements-build.txt
python resources/create_icon.py
python build.py
```

The build script (`build.py`) invokes Nuitka in onefile mode with the PySide6 plugin, bundles the prompt files, the default pptx template, and the built-in templates, and writes `dist\Simplicitor.exe`. Build duration depends on the compiler and machine; installer support is not yet configured in this script.

## Requirements

- Windows 10 or 11 (64-bit)
- A running Ollama instance reachable at `localhost:11434`
- At least one model pulled (`ollama pull <model>`)
- Model quality depends on the model and task. Tested model/runtime combinations and hardware requirements remain to be established. The current sub-7B info banner is guidance, not a reliability guarantee.

## Generate from a template (PowerPoint)

Added in v1.2. Instead of building slides from a blank canvas, you can hand Simplicitor a real PowerPoint design and have the LLM fill its layouts. The result keeps the template's branding, fonts, colors, and layout, so the deck looks like a designer made it rather than a script.

**How it works:**

1. In the Create panel, with PowerPoint selected, click **From template...** to open the picker.
2. Pick a template — either a built-in one or one you upload — and confirm the structure.
3. Type your prompt in the main Create field and click **Generate** as usual. The deck is rendered into the template's design.

**What ships:**

- **`business_pitch`** — a clean charts 16x9 template with title / agenda / content / closing slide types. Bullet lists on the agenda and content slides.
- **`technical_overview`** — a title / architecture / bullets layout set for engineering documentation.

Both seed on first launch into `Documents\Simplicitor\Templates` (the location is configurable in Settings). The folder is yours: delete a default to make Simplicitor restore it on next launch, or drop in your own templates and they appear in the picker. The template CLI (`python simplicitor/cli.py`) uses this same folder, so templates imported from either surface show up in both.

**Uploading your own template:**

Click **Upload a .pptx...** in the picker. Simplicitor scores the layouts and writes a draft manifest. Your deck needs a layout with a content placeholder beyond the title, or it is rejected: check Home > Layout or View > Slide Master for a body, content, or picture area. The result keeps the deck's theme and layouts; your slides are stripped.

**What the LLM sees:**

Only the schema. Field names, slide-type names, max-character and max-item limits, and a single one-shot example assembled from the manifest. The LLM produces validated JSON keyed to the manifest's fields; Python renders it. If the model returns malformed JSON or content that fails schema validation, the pipeline runs one repair attempt and surfaces a clear error if that fails too.

## How it was built

Simplicitor was built PRD-first: a v1.0 PRD was written before any code, iterated to v1.2 against scope creep and architectural stress tests, then broken into six implementation phases. Claude Opus 4.6 was the strategic thinking partner for architecture and contract design; Claude Code handled all implementation across approximately 1.4 million tokens of generation. The human role was PM, architect, code reviewer, and tester — not coder. Not a single line of code was written by hand. See [BUILD_STORY.md](BUILD_STORY.md) for the full account.

## Architecture at a glance

- **Content and rendering are separate**: the LLM produces content and structure; Python handles formatting, colors, and layout. Model quality still requires evaluation on the chosen tasks.
- **Templates fill placeholders, never repaint** — for PowerPoint, the LLM emits content keyed to a manifest's fields and Python renders it into a real `.pptx` design; the template's masters, layouts, and theme are the source of truth for styling
- **Scope detection on manipulation** — out-of-scope prompts (theme colors, visual styling) are detected and rejected before any file is touched; no silent failures
- **Legacy backups** use a filename-based destination and reuse existing backups. Same-named source files can collide; this remains a file-safety gap to fix.
- **Model capability guidance, not gatekeeping** — sub-7B models show a non-blocking info banner; the app coaches users instead of blocking them
- **Nuitka packaging** currently produces a onefile executable; the approved next route uses a standalone payload and a free NSIS installer.
- **Local processing is the requirement**: application inference calls target localhost Ollama. Verify that the chosen model also runs locally. Metadata-only logging is the policy, but content-bearing error paths remain a known privacy gap; see [project status](docs/PROJECT_STATUS.md).

## License

Simplicitor is licensed under the [PolyForm Noncommercial License 1.0.0](LICENSE). You may read, fork, modify, and use it for personal and noncommercial purposes. You may not sell it, include it in a paid product, or use it as part of a commercial offering. See [LICENSE_NOTICE.md](LICENSE_NOTICE.md) for a plain-English summary.

## Contributing

Issues are welcome but not guaranteed to be addressed — this is a personal demonstration project with limited maintenance bandwidth. Pull requests are not currently accepted. Forks for personal use are encouraged under the license terms.

## Author

Built by [Alexandru Pop](https://www.linkedin.com/in/alexandru-pop-b29b73198/)
