# Simplicitor Implementation Guide

This document breaks the PRD into concrete build phases. Each phase produces a runnable application. Complete each phase fully before starting the next.

---

## Phase 1: Application Skeleton

**Goal:** Main window opens, two empty panels visible, settings dialog works, config persists.

### Tasks

1. Create the project structure (all directories and __init__.py files).
2. Set up requirements.txt:
   - PySide6>=6.6
   - python-docx>=1.1
   - openpyxl>=3.1
   - python-pptx>=0.6.23
   - pypdf>=4.0
   - pdfplumber>=0.11
   - requests>=2.31
3. Create defaults.py with all constants:
   - Color hex values from PRD section 4.7
   - Default paths: Documents/Simplicitor/Generated, /Uploads, /Backups, /Logs
   - Ollama base URL, polling interval (5s), timeout (60s)
   - Max prompt length (2000 chars)
   - Model parameter threshold (7B)
4. Create settings.py:
   - Load/save JSON config from app data directory
   - Four configurable paths: generated files, uploads, backups, logs
   - Create directories on first run if they do not exist
   - Reset to defaults function
5. Create logging_setup.py:
   - Daily rotating file handler
   - Format: timestamp, operation type, status, details
   - Never log file content or user prompts
6. Create main_window.py:
   - Window title: "Simplicitor"
   - Minimum size: 1024x640
   - Top bar: app title label (left), spacer, settings gear icon button (right)
   - Horizontal splitter: left panel (Create), right panel (Edit)
   - Panel backgrounds: #F5F5F5
   - Segoe UI font throughout
7. Create create_panel.py (placeholder):
   - Header label: "Create"
   - File type selector (QComboBox): Word, Excel, PowerPoint
   - Save location: QLineEdit + Browse button (QFileDialog)
   - Prompt: QPlainTextEdit with placeholder text
   - Character counter label (0/2000)
   - Generate button (disabled for now)
   - Status indicator area (empty for now)
8. Create edit_panel.py (placeholder):
   - Header label: "Edit"
   - Drop zone placeholder (QLabel styled as drop target)
   - Supported files label: "Supported: .docx, .xlsx, .pptx, .txt, .pdf"
   - File list (QListWidget, empty)
   - Prompt: QPlainTextEdit with placeholder text
   - Character counter label (0/2000)
   - Save button (disabled for now)
   - Status indicator area (empty for now)
9. Create settings_dialog.py:
   - Modal QDialog
   - Four path fields with Browse buttons
   - View Logs button (opens log directory in Windows Explorer via os.startfile)
   - Reset to Defaults button
   - Save and Cancel buttons
10. Create main.py entry point:
    - Initialize QApplication
    - Load settings
    - Set up logging
    - Create and show main window

### Verification
- App launches and shows two-panel layout
- Settings dialog opens, paths can be changed, config persists on restart
- View Logs button opens the log folder
- Window resizes properly, panels maintain proportions

---

## Phase 2: Ollama Connection

**Goal:** App shows live Ollama connectivity status, model name, model selector dropdown.

### Tasks

1. Create ollama_client.py:
   - get_models() -> list[dict]: GET /api/tags, returns model names and metadata
   - get_running_model() -> str | None: GET /api/ps, returns currently loaded model
   - get_model_info(name: str) -> dict: POST /api/show, returns parameter count etc.
   - check_connection() -> bool: try GET /api/tags with 3s timeout
   - generate(model: str, prompt: str, system: str, format: dict | None) -> str: POST /api/generate, returns response text
   - All methods raise custom OllamaConnectionError or OllamaGenerationError
2. Create status_bar.py (update top bar in main_window):
   - Green/red connectivity dot (QLabel with colored circle, 12px)
   - Model name label
   - Model selector dropdown (QComboBox, populated from installed models)
   - On model change in dropdown: update internal state only, do not auto-load
3. Add connection polling:
   - QTimer in main_window, fires every 5 seconds when disconnected
   - On successful connection: populate model list, select current model, enable controls
   - On disconnection: red dot, "AI engine not connected", disable Generate/Save buttons, gray out prompts
4. Add first-run experience:
   - If Ollama not detected on startup, show friendly message in both panels:
     "Simplicitor cannot find your AI engine. Please start Ollama and click Retry."
   - Retry button triggers immediate connection check
   - Optional: "How to start Ollama" link opens https://ollama.com in default browser
5. Add model capability banner:
   - After connecting, query /api/show for parameter count
   - If under 7B: show non-blocking info banner below top bar
   - Banner text: "You are running a lightweight model. Simple tasks will work well. For best results with complex documents, try a model with 7B parameters or more."
   - Dismiss button (X) on the banner
   - Re-evaluate when model changes in dropdown

### Verification
- Start app with Ollama running: green dot, model name shown, dropdown populated
- Start app without Ollama: red dot, friendly message, controls disabled
- Start Ollama while app is running: auto-reconnects within 5 seconds
- Stop Ollama while app is running: goes to disconnected state
- Select a sub-7B model: info banner appears
- Dismiss banner: stays dismissed until model changes

---

## Phase 3: File Generation

**Goal:** User can generate Word, Excel, and PowerPoint files from natural language prompts.

### Tasks

1. Create system prompts in prompts/ directory:
   - system_word.txt: Instructs LLM to return JSON with title, sections array (heading, content, type)
   - system_excel.txt: Instructs LLM to return JSON with sheet_name, headers, rows, formulas
   - system_pptx.txt: Instructs LLM to return JSON with title, slides array (title, bullets, type)
   - Each prompt must: demand JSON only (no markdown fences, no preamble), provide the exact schema, include one example, state that styling will be handled separately
2. Create llm_response_parser.py:
   - parse_word_response(text: str) -> dict
   - parse_excel_response(text: str) -> dict
   - parse_pptx_response(text: str) -> dict
   - Strip markdown fences if present, handle common JSON errors
   - Raise ParseError with details on failure
3. Create word_generator.py:
   - generate(parsed: dict, output_path: Path, style_hints: dict | None) -> Path
   - Uses python-docx to create document from parsed structure
   - Applies default formatting: Calibri/Arial headings, reasonable spacing, basic table styling
   - Handles: headings, paragraphs, bullet lists, basic tables
4. Create excel_generator.py:
   - generate(parsed: dict, output_path: Path, style_hints: dict | None) -> Path
   - Uses openpyxl to create spreadsheet
   - Bold headers, auto-width columns, basic number formatting
   - Inserts formulas where specified
5. Create pptx_generator.py:
   - generate(parsed: dict, output_path: Path, style_hints: dict | None) -> Path
   - Uses python-pptx to create presentation
   - Title slide, content slides with bullets, section divider slides
   - Default clean layout
6. Create file_generator.py (dispatcher):
   - generate(file_type: str, llm_response: str, output_path: Path) -> Path
   - Parses response, dispatches to correct generator
   - Handles retry: if parse fails, calls Ollama again with simplified prompt, then fails gracefully
7. Create generate_worker.py:
   - QObject-based worker, runs on QThread
   - Signals: started, progress(str), completed(Path), error(str)
   - Workflow: send prompt to Ollama -> parse response -> generate file -> emit completed
8. Wire up create_panel.py:
   - Generate button enabled only when: Ollama connected, file type selected, prompt non-empty
   - On Generate click: disable button, show spinner, start worker
   - On completed: green status, show file path, "Open file" button (os.startfile)
   - On error: red status, dismissible error banner, log details
   - Auto-generate file name from prompt (first 5 words, sanitized) + timestamp
9. Add prompt character counter:
   - Live counter: "142 / 2000"
   - Block input beyond 2000 characters
10. Add guided prompting:
    - Placeholder text changes based on file type selection (see PRD section 4.3)
11. Add complex prompt tip:
    - If sub-7B model active AND prompt > 500 chars or contains style keywords: show inline tip

### Verification
- Generate a basic Word document from a simple prompt
- Generate an Excel spreadsheet with headers and data
- Generate a PowerPoint with 3-5 slides
- Open generated files in Microsoft Office and verify they are valid
- Test with a prompt that causes LLM to return invalid JSON: verify retry then graceful failure
- Verify file names are auto-generated and unique
- Verify error banner appears and is dismissible
- Verify Generate button disables during generation and re-enables after

---

## Phase 4: File Upload and Manipulation

**Goal:** User can upload files, apply prompts, and save modified files with automatic backup.

### Tasks

1. Create drop_zone.py:
   - QLabel subclass with drag-and-drop support
   - Accept drops of .docx, .xlsx, .pptx, .txt, .pdf files
   - Reject unsupported types with message
   - Also acts as click target to open QFileDialog
   - Visual feedback on drag hover (border color change)
2. Create file_list.py:
   - QListWidget showing uploaded files
   - Items show: file name, file type icon (optional), upload time
   - Ordered by upload time (most recent first)
   - Single selection. Selected item is highlighted.
   - Most recently uploaded file auto-selected
3. Create backup_service.py:
   - backup_if_needed(file_path: Path, backup_dir: Path) -> Path | None
   - Check if backup already exists for this file (originalname_backup.ext)
   - If no backup exists: copy original to backup_dir, return backup path
   - If backup already exists: return existing backup path (do not overwrite)
   - Never delete backups
4. Create file_manipulator.py:
   - extract_text(file_path: Path) -> str: reads file content as plain text
     - .docx: python-docx paragraph extraction
     - .xlsx: openpyxl cell value extraction (all sheets)
     - .pptx: python-pptx slide text extraction
     - .txt: plain read
     - .pdf: pdfplumber text extraction
   - apply_changes(file_path: Path, original_text: str, llm_response: str) -> Path
     - For .docx/.xlsx/.pptx: reconstruct file with modified content (best-effort formatting preservation)
     - For .txt: write modified text directly
     - For .pdf: save output as .docx or .txt alongside original (never write back to PDF)
5. Create system prompt for manipulation:
   - system_manipulate.txt: instructs LLM to receive file content and a user instruction, return the modified content as plain text
   - For structured files (Excel), return modified data in simple CSV-like format that the manipulator can parse
6. Create manipulate_worker.py:
   - QObject-based worker on QThread
   - Signals: started, progress(str), completed(Path, Path), error(str)
   - completed signal includes: saved file path AND backup path
   - Workflow: extract text -> backup original -> send to Ollama -> parse response -> write back -> emit completed
7. Wire up edit_panel.py:
   - On file drop/browse: copy file to configured uploads directory, add to file list, auto-select
   - Save button enabled only when: Ollama connected, file selected, prompt non-empty
   - On Save click: disable button, show spinner, start worker
   - On completed: green status, message includes backup path
   - On error: red status, dismissible banner, backup untouched, log details
8. Add file content preview (optional, nice-to-have):
   - When a file is selected, show first ~200 characters of extracted text below the file list as context
9. Handle edge cases:
   - Corrupted files: catch exceptions on read, show "This file could not be read" message
   - Password-protected files: catch specific exceptions, show appropriate message
   - Large files exceeding context window: truncate with warning "This file is large. Only the first portion will be processed."
   - PDF output: when PDF is selected, change Save button label to "Extract" and note that output will be .docx or .txt
   - Empty file: show message "This file appears to be empty."

### Verification
- Drag and drop a .docx file: appears in file list, is copied to uploads directory
- Select file, enter prompt, click Save: file is modified, backup created
- Modify same file again: no new backup created (one-to-one rule)
- Upload a PDF, apply prompt: output saved as .docx alongside original
- Upload corrupted file: graceful error message
- Check backup directory: correct backup files present
- Verify original files at source location are never modified

---

## Phase 5: Polish

**Goal:** All UX details from the PRD are implemented. App feels complete.

### Tasks

1. Error UX audit:
   - Every error path produces a human-readable dismissible banner
   - No stack traces, error classes, or HTTP codes visible to user
   - All technical details in log files
   - Test: disconnect Ollama mid-generation, upload corrupted file, send prompt that produces unparseable JSON
2. Connection drop mid-operation:
   - Abort gracefully
   - Show error message
   - Preserve user prompt in text area
   - Return to ready state when connection restores (no auto-retry)
3. Model capability banner:
   - Verify banner shows/hides correctly on model switch
   - Verify inline tip appears for long/complex prompts on sub-7B models
4. Guided prompting:
   - All placeholder texts from PRD section 4.3 implemented
   - Placeholders change dynamically on file type selection (Create) and file selection (Edit)
5. Settings completeness:
   - All four paths configurable and persist
   - View Logs opens correct directory
   - Reset to Defaults works
   - Directories auto-created if missing
6. File name generation:
   - Sanitize special characters
   - Limit to reasonable length
   - Timestamp suffix ensures uniqueness
   - Verify no collisions on rapid successive generations
7. Threading audit:
   - No UI access from worker threads
   - Spinner shows during all long operations
   - Both panels remain interactive independently
   - Generate/Save buttons properly disable and re-enable
8. Logging audit:
   - Daily rotation works
   - All operations logged (generate, manipulate, connection, errors)
   - No file content or user prompts in logs
   - Log format is consistent and parseable

### Verification
- Complete end-to-end walkthrough of all PRD scenarios
- Stress test: rapid generation requests, large files, disconnection during operation
- Visual audit: colors match PRD section 4.7, fonts are Segoe UI, spacing looks clean

---

## Phase 6: Packaging

**Goal:** Single .exe that runs on a clean Windows 10/11 machine.

### Tasks

1. Create Nuitka build script (build.py or build.bat):
   - nuitka --standalone --onefile --windows-disable-console --enable-plugin=pyside6
   - Include all prompts/ directory files as data
   - Include all required Python packages
   - Set application icon
   - Set version metadata
2. Test on clean Windows VM:
   - No Python installed
   - No PySide6 installed
   - .exe launches and works
3. Measure executable size (target: 50-80MB)
4. Test with Windows Defender:
   - Default settings
   - Note any warnings (expected without code signing)
5. Prepare for code signing:
   - Document the EV certificate purchase process
   - Document the signing command
   - Document AV vendor submission process (Microsoft, Kaspersky, ESET, Bitdefender, Avast)
6. Create README.md:
   - What Simplicitor is
   - Requirements: Windows 10/11, Ollama installed and running
   - Installation: download .exe, double-click
   - Recommended models: Qwen 3 8B or larger
   - Troubleshooting: common issues and fixes

### Verification
- .exe runs on clean Windows 10 VM
- .exe runs on clean Windows 11 VM
- File generation and manipulation work from the packaged .exe
- No missing DLLs or import errors
- Application icon displays correctly
- Startup time under 3 seconds
