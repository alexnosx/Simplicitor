# Changelog

## v1.0 — April 2026

- Generate Word, Excel, and PowerPoint files from natural language prompts
- Upload existing files and apply manipulation prompts, with automatic backup on first edit
- PDF read-only input with output to `.docx` or `.txt`
- Model capability detection: non-blocking info banner for sub-7B models
- Out-of-scope prompt rejection: styling/visual manipulation prompts detected and rejected before any file is touched, with a clear explanation
- Dismissible error banners with human-readable messages; all technical details written to log files only
- Native Windows feel: two-panel UI, custom geometric icon, Segoe UI typography
- Settings: configurable paths for generated files, uploads, backups, and logs
- Single `.exe` via Nuitka — runs on a clean Windows 10/11 machine with no Python or installer required
- No cloud, no telemetry, no network activity beyond localhost Ollama
