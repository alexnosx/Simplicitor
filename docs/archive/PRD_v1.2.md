# Simplicitor — Product Requirements Document v1.2

*Thursday Software SRL — April 2026*

---

## 1. Product overview

### 1.1 What Simplicitor is

Simplicitor is a native Windows desktop application that connects to a locally running Ollama instance and lets non-technical users generate and manipulate Office documents (Word, Excel, PowerPoint) through natural language prompts. The user double-clicks an `.exe`, sees a clean two-panel interface, types what they need, and gets a file. No terminal, no browser, no command line.

### 1.2 Target user

A Windows user who has installed Ollama and pulled at least one model, is motivated by privacy or cost savings, is not a developer, and has hit the wall where they can chat with AI in a terminal but cannot produce anything useful beyond conversation. They want to use AI to create and edit real documents without learning prompting techniques or command-line tools.

### 1.3 Core value proposition

The local AI space is saturated with chat interfaces (Open WebUI, LM Studio, Jan.ai, GPT4All). Simplicitor does not compete on chat. Chat is the commodity. Simplicitor competes on output: the ability to turn a local LLM into a document productivity tool. The differentiator is practical file generation and manipulation, not another conversation window.

### 1.4 Positioning

Standalone native Windows application. No browser dependency, no Docker, no MCP integrations, no cloud connection. Layered on the already-working Ollama plus Python file-generation pipeline. Designed for double-click usage.

---

## 2. What Simplicitor is NOT building in v1

This section exists to kill scope creep before it starts. The following features are explicitly excluded from v1, regardless of how useful they may seem:

- Chat history or conversation memory. Each prompt is stateless.
- RAG (retrieval-augmented generation) or document indexing.
- Model management (downloading, deleting, or configuring models). Ollama handles this.
- Plugin or extension system.
- Custom templates or template marketplace.
- Cloud sync, cloud backup, or any network activity beyond localhost Ollama.
- Multi-user or collaboration features.
- Mac or Linux support. Windows only.
- PDF write-back. PDF is read-only input.
- Image generation or image editing.
- Automated workflows, chaining, or batch processing.
- Auto-update mechanism. Updates are manual reinstall for v1.
- Dark mode. Light theme only in v1.

If a feature is not in sections 4 through 7 of this document, it does not exist in v1.

---

## 3. Technical architecture

### 3.1 Stack

| Component | Technology |
|-----------|-----------|
| UI | PySide6 |
| LLM backend | Ollama REST API (localhost:11434) |
| Word generation | python-docx |
| Excel generation | openpyxl |
| PowerPoint generation | python-pptx |
| PDF reading | pypdf, pdfplumber (read-only) |
| Packaging | Nuitka |
| Language | Python 3.11+ |
| OS target | Windows 10/11 only |

### 3.2 Distribution and signing

Nuitka compiles the application to a native binary, which substantially reduces antivirus false positive rates compared to PyInstaller. The resulting executable is typically 50–80 MB including PySide6 and all dependencies. However, an unsigned executable from an unknown publisher will still trigger Microsoft SmartScreen warnings on first launch.

Code signing with an EV (Extended Validation) certificate is required before any public distribution. An EV certificate provides immediate SmartScreen reputation, bypassing the download volume threshold that standard OV certificates require. Budget: approximately $200–400/year.

Pre-distribution checklist:
- Compile with Nuitka in standalone mode with all dependencies.
- Sign the `.exe` with the EV certificate.
- Submit the signed binary to the top 5 AV vendors (Microsoft, Kaspersky, ESET, Bitdefender, Avast/AVG) via their false positive reporting forms.
- Test on a clean Windows 10 and Windows 11 machine with default Defender settings.

### 3.3 Ollama integration

The app communicates with Ollama via its REST API at `http://localhost:11434`. On startup the app polls `/api/tags` to detect available models and `/api/ps` for the currently loaded model. If Ollama is not running or not responding, the app enters a disconnected state with all generation and manipulation controls disabled. The app polls connectivity every 5 seconds while disconnected. When connection is restored, controls re-enable automatically.

---

## 4. User experience

### 4.1 First-run experience

Three scenarios:

**Scenario A: Ollama is running and a model is loaded.**
The app launches into the normal two-panel view. The status bar shows a green indicator, the model name, and the app is ready to use. No onboarding wizard.

**Scenario B: Ollama is installed but not running.**
The app shows a friendly disconnected state: "Simplicitor cannot find your AI engine. Please start Ollama and click Retry." A single Retry button. No jargon, no error codes.

**Scenario C: Ollama is not installed.**
Same disconnected state as Scenario B. The app cannot distinguish between "not installed" and "not running" because both appear as a localhost connection failure.

### 4.2 UI layout

**Top bar:** App title, Ollama connectivity indicator, currently running model name, model selector dropdown, and settings gear icon.

**Left panel ("Create"):** File type selector (Word / Excel / PowerPoint), save location input with browse button, prompt text area with context-sensitive placeholder text, Generate button, and generation status indicator.

**Right panel ("Edit"):** File drop zone, uploaded file list (ordered by upload time, most recent first), prompt text area, Save button, and save status indicator.

**Settings dialog (modal):** Four configurable paths (generated files, uploaded files working directory, backups, logs), a View Logs button, and a Reset to Defaults button.

### 4.3 Guided prompting

Both prompt areas include context-sensitive placeholder text:

**Generate panel:**
- Word: *"Describe the document you need, e.g.: Create a project status report with sections for timeline, risks, and next steps"*
- Excel: *"Describe the spreadsheet you need, e.g.: Create a monthly budget tracker with columns for category, planned amount, actual amount, and difference"*
- PowerPoint: *"Describe the presentation you need, e.g.: Create a 5-slide pitch deck about our new product launch"*

**Edit panel:**
- Word file: *"What would you like to change? e.g.: Rewrite the executive summary to be more concise"*
- Excel file: *"What would you like to change? e.g.: Add a totals row and highlight cells where values exceed the budget"*
- PDF file: *"What would you like to extract? e.g.: Summarize the key findings from this report into bullet points"* (output saves as `.txt` or `.docx`, not PDF)

### 4.4 Error UX

Every error the user sees must be human-readable and actionable. All technical error details are written exclusively to the log file, never displayed in the UI. Error messages follow this pattern: *[What happened] + [What you can do]*.

Examples:
- "The file could not be generated. Try simplifying your description or check the log file for details."
- "The AI engine disconnected during processing. Please check that Ollama is running and try again."

Error messages are displayed as dismissible banners within the relevant panel.

### 4.5 Model capability guidance

If the active model has fewer than 7 billion parameters, a non-blocking info banner appears:

> "You are running a lightweight model. Simple tasks will work well. For best results with complex documents, try a model with 7B parameters or more."

The banner is dismissible. It does not disable any controls. If a user submits a prompt exceeding 500 characters or containing styling keywords while a sub-7B model is active, a brief inline tip appears: "Tip: this request may work better with a larger model."

### 4.6 Visual design

- Background: `#FAFAFA` / Panel backgrounds: `#F5F5F5`
- Primary accent (buttons, active state): `#2563EB`
- Body text: `#1E1E1E` / Success: `#16A34A` / Error: `#DC2626`
- Font: Segoe UI, regular for body, semibold for headings and button labels
- No gradients, no deep shadows, max 4px border radius

---

## 5. Functional requirements: file generation

### 5.1 Supported output types

Word (`.docx`), Excel (`.xlsx`), PowerPoint (`.pptx`)

### 5.2 Generation workflow

1. User selects file type and save location.
2. User types a natural language prompt.
3. User clicks Generate.
4. App sends the prompt to Ollama with a file-type-specific system prompt requesting structured JSON output.
5. App parses the LLM response and generates the file using the appropriate Python library.
6. On success: status turns green, file path displayed, Open File button provided.
7. On failure: human-readable dismissible error banner; technical details in log.

### 5.3 Generation rules

- All generation runs on a background thread. The UI never freezes.
- The Generate button is disabled while generation is in progress.
- File names are auto-generated from the prompt with a timestamp suffix.
- If the LLM response cannot be parsed, the app retries once with a simplified system prompt before reporting failure.
- Maximum prompt length: 2000 characters, enforced in the UI with a character counter.

---

## 6. Functional requirements: file manipulation

### 6.1 Supported input types

Word (`.docx`), Excel (`.xlsx`), PowerPoint (`.pptx`), plain text (`.txt`), PDF (`.pdf`, read-only — output to `.docx` or `.txt`)

### 6.2 Manipulation workflow

1. User uploads a file (drag-and-drop or browse). File is copied to the configured working directory.
2. User selects the file from the uploaded list.
3. User types a prompt describing the desired change.
4. User clicks Save.
5. On first manipulation: app creates a backup at `[backup_dir]/originalname_backup.ext`. One backup per file.
6. App sends extracted file content plus the prompt to Ollama.
7. App parses the LLM response and writes it back to the working copy.
8. On success: "File saved successfully. Your original is backed up at [backup path]."
9. On failure: human-readable error, backup remains untouched.

### 6.3 Backup behavior

First manipulation of a file creates a backup with a `_backup` suffix. Subsequent manipulations of the same file do not create additional backups. The backup always represents the original state. The app never deletes backups.

### 6.4 Formatting preservation

Formatting preservation is best-effort and must be communicated honestly:
- Text content changes: reliable.
- Basic formatting (bold, italic, font size): preserved where possible.
- Complex formatting (custom styles, conditional formatting, slide transitions): may be lost.

The save confirmation always includes: "Your original file is backed up automatically."

---

## 7. Global behavior

### 7.1 Ollama connectivity

- On startup: poll `http://localhost:11434/api/tags`. Enter connected or disconnected state.
- Connected: green indicator, all controls enabled.
- Disconnected: red indicator, all Generate and Save buttons disabled.
- While disconnected: poll every 5 seconds, auto-reconnect when Ollama responds.
- If connection drops mid-operation: abort gracefully, show error, file unchanged, user's prompt preserved.

### 7.2 Model selection

Top bar dropdown populated from installed Ollama models. Changing the model does not auto-load it — Ollama handles loading on demand at the next generation request.

### 7.3 Logging

- Log files rotated daily: `simplicitor_YYYYMMDD.log`
- Log entries: timestamp, operation type, status, error details where applicable
- Never log file content or prompt text
- Settings dialog includes a View Logs button opening the log folder in Explorer

### 7.4 Settings

Four configurable paths stored in a local JSON config file:
- Default save location for generated files → `Documents/Simplicitor/Generated`
- Working directory for uploaded files → `Documents/Simplicitor/Uploads`
- Backup files directory → `Documents/Simplicitor/Backups`
- Log directory → `Documents/Simplicitor/Logs`

### 7.5 Threading model

All Ollama API calls and file I/O run on background threads (QThread workers in PySide6). The UI thread is never blocked.

---

## 8. v1 success criteria

v1 ships when all of the following are true:

- A user with Ollama running can double-click `Simplicitor.exe` and see a working UI within 3 seconds.
- The user can generate a Word, Excel, or PowerPoint file from a natural language prompt.
- The user can upload an existing file, apply a prompt, and save the result with automatic backup on first manipulation.
- All errors produce human-readable, dismissible messages. No stack traces visible to the user.
- The `.exe` is compiled with Nuitka and does not crash. If something fails, it fails gracefully.
