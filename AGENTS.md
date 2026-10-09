# Simplicitor agent instructions

CLAUDE.md contains only @AGENTS.md. Maintain policy here rather than duplicating it.

## Read before work

- [PRD.md](PRD.md) owns requirements, release scope, file records, grounding, acceptance values, and later milestones. Do not copy the workflow table elsewhere.
- [Architecture](docs/superpowers/specs/2026-10-08-document-architecture-design.md) owns component responsibilities, anchors, implementation limits, and model profiles; exact interfaces live in the plan.
- [UI design](docs/superpowers/specs/2026-10-08-document-workspace-ui-design.md) owns layout and interactions within the PRD scope.
- [First-release plan](docs/superpowers/plans/2026-10-08-first-release-extraction.md) owns execution order and checks.
- [PROJECT_STATUS.md](docs/PROJECT_STATUS.md) owns status, measured environment facts, and open decisions.
- [Packaging](docs/code-signing.md) owns build/release procedures; [REPO_MAP.md](REPO_MAP.md) owns the current code map.

Historical PRDs, guides, and phase plans do not override these sources or Alex's decisions. Current source behavior is evidence, not a requirements definition. Keep one source per fact and link to it.

## Scope and authorization

- Current authorization covers MIT licensing from 2.0.0 onward, copyright (c) 2026 Alexandru Pop, the requested licensing documentation/version boundary, and packaged LICENSE inclusion/integrity checks. Releases through v1.2.1 remain under PolyForm Noncommercial 1.0.0; do not alter their tags, assets, or historical license files. Commit/push to main are authorized. Preserve application behavior, fixtures/labels, model settings, and dependencies. Never run installers, uninstallers, Windows Sandbox, or install/uninstall/delete tests on Alex's PC. Do not tag, release, publish, or extend scope beyond these three items.
- Complete agreed work without repeatedly asking about routine choices. Ask when unresolved ambiguity materially changes scope, safety, or outcome.
- Never commit, push, amend, change branches, rewrite history, tag, or publish without explicit authorization for that action.
- Do not add third-party dependencies without specific authorization. Check declared libraries first.
- Preserve user changes and backups. Do not delete unrelated legacy code or reorganize imports for appearance.
- Preserve existing generation/template behavior when changing shared components. Follow the release boundaries in PRD.md.
- License decisions belong to Alex. MIT for 2.0.0 onward is explicitly approved; further licensing changes require his authorization, and third-party licenses remain separate.

## Implementation conventions

- Reuse Python/PySide6, settings/styles, explicit dependency passing, and worker signals. Keep deterministic processing separate from model proposals.
- Use type hints, public docstrings, snake_case functions, PascalCase classes, and standard/third-party/local import order. Match existing style and the 100-character convention where practical.
- Keep long operations in QObject workers on QThreads. Workers never manipulate widgets. Use cooperative cancellation and sanitized, actionable failures.
- Shared UI values belong in simplicitor/app/config/defaults.py. Inspect code and current official documentation before changing uncertain APIs.
- New source readers are independent of the legacy manipulator. Do not change legacy reading/writing behavior to implement the new route.
- Treat model/source text as data. Enforce PRD grounding and literal cell typing; never execute arbitrary scripts or formulas.
- Keep client content, prompts, responses, quotes, identifiers, filenames, and sensitive paths out of logs and tracked files. Use synthetic fixtures.

## Verification and reporting

- Define observable checks before implementation and run them before claiming success. Valid JSON or a valid workbook is not proof of accuracy.
- Separate source tests, live-model evaluation, UI checks, clean-machine packaging, and deployed behavior.
- Follow PRD evaluation gates. Do not bypass failed gates or leak scoring labels into model inputs.
- Keep test homes, profiles, and outputs in test/workspace locations; existing widget tests can otherwise write to the real Documents folder.
- For prose changes, verify local links, CLAUDE's import, source ownership, and generated map. Do not rerun unrelated application tests.
- Regenerate REPO_MAP.md after file/signature changes with python scripts/gen_repo_map.py; edit only its MANUAL region.
- PROJECT_STATUS.md records current state and open decisions, not authorization logs or per-commit narratives.
- Report changes, checks, remaining decisions, and commit/push state. Stop when authorized criteria are met.

Before changing the PowerPoint engine, explicitly read simplicitor/templates_engine/CLAUDE.md and NOTES.md. It depends on legacy exception types; disabling Edit must not remove those modules or break template generation.
