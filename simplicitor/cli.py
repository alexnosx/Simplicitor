# simplicitor/cli.py
# Template engine CLI. Run: python cli.py <command> [args]
# Or from repo root: python simplicitor/cli.py <command> [args]
import argparse
import sys
from pathlib import Path

# Mirror main.py: put simplicitor/ on sys.path so bare package imports work.
sys.path.insert(0, str(Path(__file__).parent))

from templates_engine.breakdown import format_inspection, inspect_pptx


def _cmd_inspect(args: argparse.Namespace) -> int:
    try:
        report = inspect_pptx(args.file)
        print(format_inspection(report))
        return 0
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


def _cmd_list_templates(args: argparse.Namespace) -> int:
    from templates_engine.config import list_templates
    from app.services.file_manipulator import ManipulationError

    try:
        templates = list_templates()
    except (ValueError, ManipulationError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if not templates:
        print("No templates found.")
        return 0

    print(f"{'Name':<30}  Source")
    print("-" * 42)
    for t in templates:
        print(f"{t['name']:<30}  {t['source']}")
    return 0


def _cmd_import(args: argparse.Namespace) -> int:
    from templates_engine.config import import_template
    from app.services.file_manipulator import ManipulationError

    try:
        result = import_template(args.file)
    except (ValueError, ManipulationError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if result["status"] == "hard_stop":
        print(result["message"], file=sys.stderr)
        return 1

    if result["status"] == "exists":
        print(
            f"Error: a template named '{result['name']}' already exists. "
            "Delete or rename it before importing again.",
            file=sys.stderr,
        )
        return 1

    print(f"Imported '{result['name']}' successfully.")
    print()
    print(result["report"])

    if result["lint_warnings"]:
        print()
        print("Manifest warnings (review before use):")
        for warning in result["lint_warnings"]:
            print(f"  - {warning}")

    return 0


def _cmd_render(args: argparse.Namespace) -> int:
    import json

    from app.services.file_manipulator import ManipulationError
    from templates_engine.config import list_templates
    from templates_engine.manifest import load_manifest
    from templates_engine.render_pptx import render
    from templates_engine.validation import format_validation_errors, validate_content

    try:
        templates = list_templates()
        match = next((t for t in templates if t["name"] == args.template), None)
        if match is None:
            raise ValueError(f"Template '{args.template}' not found.")

        manifest = load_manifest(match["manifest_path"])

        spec_path = Path(args.spec)
        try:
            spec_text = spec_path.read_text(encoding="utf-8")
        except OSError:
            raise ValueError(f"Spec file not found or not readable: {spec_path}")
        try:
            raw_json = json.loads(spec_text)
        except json.JSONDecodeError:
            raise ValueError(f"Invalid JSON in spec file: {spec_path}")

        ok, payload = validate_content(manifest, raw_json)
        if not ok:
            print(format_validation_errors(payload), file=sys.stderr)
            return 1

        result = render(manifest, payload, args.out, template_dir=match["path"])

        print(result["path"])
        for issue in result["issues"]:
            print(f"Warning: {issue}")

        return 0
    except (ValueError, ManipulationError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


def _cmd_generate(args: argparse.Namespace) -> int:
    if not args.dry_run and not args.out:
        print(
            "Error: --out is required. Use --dry-run to inspect the prompt without generating a file.",
            file=sys.stderr,
        )
        return 1

    from app.services.ollama_client import (
        OllamaConnectionError,
        OllamaGenerationError,
        OllamaTimeoutError,
    )
    from templates_engine.config import list_templates
    from templates_engine.manifest import load_manifest
    from templates_engine.prompt_builder import build_prompt
    from templates_engine import llm

    try:
        templates = list_templates()
        match = next((t for t in templates if t["name"] == args.template), None)
        if match is None:
            raise ValueError(f"Template '{args.template}' not found.")

        manifest = load_manifest(match["manifest_path"])

        source_text = None
        if args.source:
            source_path = Path(args.source)
            try:
                source_text = source_path.read_text(encoding="utf-8")
            except OSError:
                raise ValueError(f"Source file not found or not readable: {source_path}")

        messages = build_prompt(manifest, args.request, source_text)

        if args.dry_run:
            labels = [
                "SYSTEM",
                "USER (one-shot example)",
                "ASSISTANT (one-shot response)",
                "USER (request)",
            ]
            assert len(messages) == len(labels), (
                f"Expected {len(labels)} messages from build_prompt, got {len(messages)}"
            )
            for label, msg in zip(labels, messages):
                print(f"=== {label} ===")
                print(msg["content"])
                print()
            return 0

        from app.parsers.llm_response_parser import ParseError
        from app.services.file_manipulator import ManipulationError
        from templates_engine import pipeline

        llm.preflight(args.model)
        result = pipeline.run(manifest, match["path"], messages, args.model, args.out)
        print(result["path"])
        for issue in result["issues"]:
            print(f"Warning: {issue}")
        return 0

    except (ValueError, ParseError, ManipulationError,
            OllamaConnectionError, OllamaTimeoutError, OllamaGenerationError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="simplicitor",
        description="Simplicitor template engine CLI.",
    )
    sub = parser.add_subparsers(dest="command", metavar="<command>")

    inspect_p = sub.add_parser("inspect", help="Print the layout/placeholder map of a .pptx file.")
    inspect_p.add_argument("file", help="Path to the .pptx file.")

    sub.add_parser("list-templates", help="List available built-in and user templates.")

    import_p = sub.add_parser("import", help="Import a .pptx file as a user template.")
    import_p.add_argument("file", help="Path to the .pptx file to import.")

    render_p = sub.add_parser("render", help="Render a content spec using a template.")
    render_p.add_argument("--template", required=True, help="Template name.")
    render_p.add_argument("--spec", required=True, help="Path to content JSON file.")
    render_p.add_argument("--out", required=True, help="Output .pptx path.")

    generate_p = sub.add_parser("generate", help="Build and optionally send a prompt from a template.")
    generate_p.add_argument("--template", required=True, help="Template name.")
    generate_p.add_argument("--request", required=True, help="User request text.")
    generate_p.add_argument("--source", default=None, help="Optional source file path.")
    generate_p.add_argument("--model", default="llama3", help="Ollama model name (default: llama3).")
    generate_p.add_argument("--dry-run", action="store_true", dest="dry_run",
                            help="Print assembled prompt without calling the model.")
    generate_p.add_argument(
        "--out", default=None,
        help="Output .pptx path (required unless --dry-run).",
    )

    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    if args.command == "inspect":
        return _cmd_inspect(args)
    if args.command == "list-templates":
        return _cmd_list_templates(args)
    if args.command == "import":
        return _cmd_import(args)
    if args.command == "render":
        return _cmd_render(args)
    if args.command == "generate":
        return _cmd_generate(args)

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
