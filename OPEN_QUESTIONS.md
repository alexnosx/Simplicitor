# Open Questions

Genuine ambiguities found during a full-repo read (2026-07-01). Questions only, no
recommendations.

1. **Which template root is authoritative, the GUI's or the CLI's?** The CLI path
   (`simplicitor/templates_engine/config.py:32-56`, `list_templates`, `import_template`
   default `user_root`) resolves user templates to `%APPDATA%\Simplicitor\templates`
   with a `simplicitor.toml` override, while the GUI uses the single configurable
   folder `Settings.templates_dir` (default `Documents\Simplicitor\Templates`) via
   `list_library` / `ensure_default_templates` (`config.py:152-220`,
   `simplicitor/main.py:38`, `simplicitor/app/widgets/template_dialog.py:147`). A
   template imported through one surface is invisible to the other.
   `simplicitor/templates_engine/CLAUDE.md` (Two template directories table) documents
   only the APPDATA root; README documents only the Documents folder. Is the split
   deliberate and permanent, or is one root meant to be retired?

2. **Does the privacy rule cover LLM output?** `logging_setup.py:15-16` states file
   content and user prompts are never logged, and the root logger runs at DEBUG with
   the file handler capturing everything (`simplicitor/app/utils/logging_setup.py:37-39`).
   Yet `simplicitor/app/services/file_generator.py:56` logs the first 500 chars of the
   raw LLM response at debug level, and that response becomes the generated document's
   content (commit 00fe9a6 added it deliberately). Is generated content exempt from
   the never-log rule, or is this an unresolved conflict?

3. **Is `simplicitor/tests/` supposed to run at all?** `pytest.ini` sets
   `testpaths = tests`, so a bare `pytest` never collects `simplicitor/tests/test_cli.py`
   or `simplicitor/tests/templates_engine/test_pipeline.py`. The engine reference
   (`simplicitor/templates_engine/CLAUDE.md`, first paragraph) cites the CLI test as
   part of the engine's coverage. The pipeline copy also references a
   `fixtures/` directory that does not exist under `simplicitor/tests/templates_engine/`
   (line 13) and lacks the `tmp_template` conftest fixture, so it appears to be a stale
   duplicate of `tests/templates_engine/test_pipeline.py`. Which location is canonical,
   and how is `test_cli.py` intended to be collected?

4. **What is the intended config-dir fallback?** The docstring of
   `simplicitor/main.py:_config_dir` (lines 24-27) says it uses `%APPDATA%/Simplicitor`
   "falling back to ~/.simplicitor", but the code (lines 28-30) unconditionally builds
   `Path.home()/AppData/Roaming/Simplicitor` and creates it, with no fallback branch.
   `templates_engine/config.get_user_root` (config.py:50-54) does implement that
   fallback. Is the docstring stale, or is a fallback missing in `main.py`?

5. **Are the connectivity-poll timeouts intentional?** `check_connection` hard-codes a
   3 second timeout (`simplicitor/app/services/ollama_client.py:75`) even though
   CLAUDE.md's coding conventions require timeouts to live in
   `app/config/defaults.py`. Meanwhile `OllamaWorker._poll` (ollama_worker.py:84-96)
   calls `get_models`, `get_running_model`, and `get_model_params` each poll, all with
   `OLLAMA_TIMEOUT_S` (60 s), inside a 5 second poll interval; a hung-but-open Ollama
   socket could stall a single poll for minutes. Deliberate tradeoff or oversight?

6. **Is full formatting loss on .docx manipulation accepted v1 behavior?**
   `FileManipulator._apply_docx` (`simplicitor/app/services/file_manipulator.py:147-154`)
   writes a brand-new `Document()` containing only plain paragraphs, discarding the
   original file's styles, tables, and images, while `_apply_pptx` (lines 177-228)
   deliberately reopens the existing file to preserve its theme (comment at lines
   181-183). The manipulation scope message promises only that visual styling cannot
   be *changed*, not that it will be destroyed. Where is the rationale for the
   docx/pptx asymmetry recorded?

7. **Is substring keyword matching for scope detection intended?** The manipulation
   scope check (`simplicitor/app/workers/manipulate_worker.py:74-76`) tests
   `kw in prompt_lower` against `MANIPULATION_OUT_OF_SCOPE_KEYWORDS`
   (`defaults.py:65-69`), so "style" matches "lifestyle" and "color" matches
   "Colorado", rejecting in-scope text edits on .docx/.pptx files. BUILD_STORY
   describes the keyword check but not the substring-vs-word-boundary choice or its
   accepted false-positive rate. Is this documented anywhere?
