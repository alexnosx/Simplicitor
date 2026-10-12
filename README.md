# Simplicitor

[![License: MIT from 2.0.0](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Windows desktop document work with local models.

English is the target language. Other languages may work but are not tested or claimed.

## Project direction

[PRD.md](PRD.md) is the source for release scope, prerequisites, later milestones, and acceptance gates. [Project status](docs/PROJECT_STATUS.md) shows what exists and the decisions still open.

The review set is the [document architecture](docs/superpowers/specs/2026-10-08-document-architecture-design.md), [UI design](docs/superpowers/specs/2026-10-08-document-workspace-ui-design.md), and [2.1.0 implementation plan](docs/superpowers/plans/2026-10-09-release-2.1.0.md). Build procedures are in [packaging](docs/code-signing.md). Historical screenshots and phase plans describe earlier versions.

## Screenshot

Historical pre-2.1.0 screenshot; the [approved workspace mockup](docs/design/document-workspace.html) shows the new layout.

![Earlier Simplicitor screenshot](docs/screenshot.png)

## Install and run

### Download the binary

Published downloads are on the [Releases](https://github.com/alexnosx/Simplicitor/releases) page. Version 2.1.0 is prepared but has not been tagged or published. Its [release notes](docs/releases/v2.1.0-notes.md) describe these planned downloads:

- `Simplicitor-2.1.0.msi`: installs for the current Windows user.
- `Simplicitor-portable.zip`: unpack and run `Simplicitor.exe` without installing.
- `SHA256SUMS.json`: download checksums.

For the MSI, uninstall an existing 2.0.0 setup.exe installation from Settings > Apps first. Settings and documents are preserved. The MSI is unsigned and Windows may show an unknown-publisher or security warning. Packaging does not remove that warning.

### Hosted build

The [Build workflow](.github/workflows/build.yml) compiles the standalone payload with Nuitka 4.2.2, creates the per-user MSI with pinned WiX 5.0.2, and archives that same payload. MSI version is 2.1.0; the executable version is 2.1.0.0. The hosted Windows runner qualifies refusal of an old NSIS installation, install, repair, major upgrade, startup without Ollama and settings-preserving uninstall before uploading artifacts.

Pushes run source tests only. Full builds run at approved milestones by manual dispatch and on authorized tags. See the [testing policy](docs/superpowers/plans/2026-10-09-release-2.1.0.md#testing-policy-alex-2026-10-09) and [packaging procedures](docs/code-signing.md). Do not run build.py, WiX, installer/uninstaller or qualification tools on Alex's PC. Publication requires explicit approval.

### Run from source without building

From PowerShell in the checkout, create the environment once if needed:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Start Ollama, then launch the application:

```powershell
.\.venv\Scripts\python.exe .\simplicitor\main.py
```

For the existing checkout at `C:\Codex\Simplicitor`, the environment is already installed; only the launch command is needed. Select an installed local model in the top bar. The native walkthrough used `qwen3:8b-q4_K_M`, the installed Q4_K_M tag of the selected Qwen candidate.

Try one synthetic extraction:

1. Keep **Create new** selected. In Source files, click **browse** and choose `tests\extraction\fixtures\invoice-01.docx`. Adding it selects Excel automatically.
2. Enter: `Extract the invoice number, customer name, gross total, and due date.`
3. Click **Next: choose columns**. Edit the names/descriptions/types if needed. Keep identifiers as text. If a date column has ambiguous numeric dates, choose the day/month order in its details.
4. Click **Extract to Excel** to confirm the columns and start extraction.
5. Select grid values to inspect their saved quotes, anchors, and issues. This fixture should retain invoice ID `00123` as text, gross total `12500.00` as a number, and due date `2026-04-14` as a date.
6. If output is flagged or incomplete, review it and check the acknowledgement. Click **Save to Excel** to choose a new `.xlsx` file. Windows asks before replacing an existing output; source files cannot be replaced.

To create from a prompt, leave Source files empty, select Word, Excel, PowerPoint or PDF and click **Create file**. For PowerPoint, **Use a template** opens the existing template flow. **Edit document** explains the deferred editing feature. Source-run checks do not qualify the installer or replace the full-pipeline accuracy evaluation.

## Requirements

A GPU with 8 GB VRAM is recommended, not required or checked.

See [release prerequisites](PRD.md#workflow-scope) and the [model evaluation requirements](PRD.md#limits-and-evaluation-gates). For the existing application, start Ollama locally and pull a model with `ollama pull <model>`.

## Generate from a template (PowerPoint)

Added in v1.2. Instead of building slides from a blank canvas, you can hand Simplicitor a real PowerPoint design and have the LLM fill its layouts. The result keeps the template's branding, fonts, colors, and layout, so the deck looks like a designer made it rather than a script.

**How it works:**

1. In Create new with no source files and PowerPoint selected, click **Use a template** to open the picker.
2. Pick a template — either a built-in one or one you upload — and confirm the structure.
3. Type your prompt in the main Create field and click **Create file**. The deck is rendered into the template's design.

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

Use the [repository map](REPO_MAP.md) for existing module responsibilities, the [architecture design](docs/superpowers/specs/2026-10-08-document-architecture-design.md) for document components and packaging, and [project status](docs/PROJECT_STATUS.md) for implementation state and known defects.

## License

Simplicitor 2.0.0 onward is licensed under the [MIT License](LICENSE), copyright (c) 2026 Alexandru Pop. Personal and commercial use, modification, and distribution are permitted under its terms. Releases up to and including v1.2.1 remain under [PolyForm Noncommercial 1.0.0](https://github.com/alexnosx/Simplicitor/blob/v1.2.1/LICENSE). See [LICENSE_NOTICE.md](LICENSE_NOTICE.md) for a plain-English summary and the third-party license distinction.

## Contributing

Issues are welcome but not guaranteed to be addressed — this is a personal demonstration project with limited maintenance bandwidth. Pull requests are not currently accepted. Forks are encouraged under the license terms.

## Author

Built by [Alexandru Pop](https://www.linkedin.com/in/alexandru-pop-b29b73198/)
