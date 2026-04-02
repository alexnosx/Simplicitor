# Simplicitor

## Project Overview

Simplicitor is a native Windows desktop application that connects to a locally running Ollama instance and lets non-technical users generate and manipulate Office documents (Word, Excel, PowerPoint) through natural language prompts. Two-panel UI: Create (generate new files) and Edit (manipulate existing files). No cloud, no browser, no terminal. Double-click .exe, it works.

Full requirements: `docs/Simplicitor_PRD_v1.2.docx`
Build phases: `docs/Simplicitor_Implementation_Guide.md`

The PRD is the source of truth. If something is ambiguous, ask rather than guess.

## Tech Stack

- **UI:** PySide6
- **LLM Backend:** Ollama REST API (localhost:11434)
- **Documents:** python-docx, openpyxl, python-pptx
- **PDF Reading:** pypdf, pdfplumber (read-only, no write-back)
- **Packaging:** Nuitka
- **Language:** Python 3.11+
- **Target OS:** Windows 10/11 only

## Project Structure

```
simplicitor/
    main.py
    app/
        __init__.py
        main_window.py
        widgets/
            __init__.py
            create_panel.py
            edit_panel.py
            settings_dialog.py
            status_bar.py
            file_list.py
            drop_zone.py
        workers/
            __init__.py
            ollama_worker.py
            generate_worker.py
            manipulate_worker.py
        services/
            __init__.py
            ollama_client.py
            file_generator.py
            file_manipulator.py
            backup_service.py
        generators/
            __init__.py
            word_generator.py
            excel_generator.py
            pptx_generator.py
        parsers/
            __init__.py
            llm_response_parser.py
        config/
            __init__.py
            settings.py
            defaults.py
        utils/
            __init__.py
            logging_setup.py
            file_utils.py
    prompts/
        system_word.txt
        system_excel.txt
        system_pptx.txt
        system_manipulate.txt
    tests/
    docs/
        Simplicitor_PRD_v1.2.docx
        Simplicitor_Implementation_Guide.md
    requirements.txt
    README.md
```

## Coding Conventions

- Type hints on all function signatures.
- Docstrings on all public methods.
- No global state. Pass dependencies explicitly.
- PySide6 threading: QThread with worker objects (moveToThread pattern), not subclassed QThread. Signals/slots only. Never touch UI from a worker thread.
- Every external call (Ollama API, file I/O, LLM parsing) wrapped in try/except. Errors produce user-friendly messages and log technical details. Never crash.
- Logging: Python logging module, daily rotation, never log file content or user prompts.
- Constants: all magic numbers, default paths, color hex values, timeouts go in `app/config/defaults.py`.
- Imports: standard library first, third-party second, local third. Absolute imports only.
- Line length: 100 characters max.
- Naming: snake_case for functions/variables, PascalCase for classes, UPPER_SNAKE for constants.

## UI Design Rules

- Colors (light theme only, dark mode is v2):
  - Background: #FAFAFA
  - Panel backgrounds: #F5F5F5
  - Primary accent (buttons, active): #2563EB
  - Body text: #1E1E1E
  - Success: #16A34A
  - Error: #DC2626
  - Disabled: #9CA3AF
  - Borders: #E5E7EB
  - Info banner background: #EFF6FF
- Font: Segoe UI. Regular for body, semibold for headings/buttons.
- No gradients, no deep shadows, max 4px border radius.
- Dismissible banners for errors and info (colored strip + text + X button).
- All long-running operations show a spinner and disable the triggering button.

## Ollama Integration

- Base URL: `http://localhost:11434`
- Model list: `GET /api/tags`
- Running model: `GET /api/ps`
- Model metadata: `POST /api/show` with `{"name": "model_name"}`
- Generate: `POST /api/generate` or `POST /api/chat`
- Connection polling: every 5 seconds when disconnected
- Timeout: 60 seconds on generation/manipulation calls
- Use Ollama's `format` parameter with JSON schema for structured output
- Connection drop mid-operation: abort, show error, preserve prompt in text area

## LLM Contract Design (Critical)

The LLM produces content and basic structure. Python code handles all formatting, colors, and layout. DO NOT ask the LLM to produce complex styling JSON. Keep it simple.

**Word generation** - LLM returns:
```json
{
  "title": "string",
  "sections": [
    {
      "heading": "string",
      "content": "string (paragraphs separated by \\n\\n)",
      "type": "text|table|list"
    }
  ]
}
```

**Excel generation** - LLM returns:
```json
{
  "sheet_name": "string",
  "headers": ["string"],
  "rows": [["cell_value"]],
  "formulas": [{"cell": "B10", "formula": "=SUM(B2:B9)"}]
}
```

**PowerPoint generation** - LLM returns:
```json
{
  "title": "string",
  "slides": [
    {
      "title": "string",
      "bullets": ["string"],
      "type": "title|content|section"
    }
  ]
}
```

**File manipulation** - LLM receives extracted text, returns modified text. Python handles file reading/writing.

If LLM response fails to parse, retry ONCE with simplified prompt, then fail gracefully.

## Backup Rules

- One backup per file, created on first manipulation only.
- Stored in configured backup directory.
- Name: `originalname_backup.extension`
- Never overwrite existing backup. Never delete backups.
- Show backup path in success message.

## Build Phases

Read `docs/Simplicitor_Implementation_Guide.md` for detailed tasks. Build in order:

1. **Phase 1: Skeleton** - Main window, panels, settings, config
2. **Phase 2: Ollama** - Connection, status, model selector, polling
3. **Phase 3: Generate** - File generation (Word, Excel, PowerPoint)
4. **Phase 4: Edit** - Upload, manipulation, backup
5. **Phase 5: Polish** - Error UX, banners, edge cases
6. **Phase 6: Package** - Nuitka compilation

Complete each phase fully before the next. Each phase must produce a runnable app.

## What NOT to Build

No chat history, no RAG, no model management, no plugins, no cloud, no dark mode, no PDF write-back, no auto-update, no Mac/Linux. If I ask for something not in the PRD, flag it as scope creep and confirm before building.

## Assumptions

When you must assume something to keep moving, add a `# TODO: ASSUMPTION - [explanation]` comment. Prefer the simpler implementation. This is a v1 product.
