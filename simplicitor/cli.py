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
    except ManipulationError as exc:
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
        print(result["message"])
        return 0

    print(f"Imported '{result['name']}' successfully.")
    print()
    print(result["report"])

    if result["lint_warnings"]:
        print()
        print("Manifest warnings (review before use):")
        for warning in result["lint_warnings"]:
            print(f"  - {warning}")

    return 0


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

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
