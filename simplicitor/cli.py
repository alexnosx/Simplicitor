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

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
