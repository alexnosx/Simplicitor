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


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="simplicitor",
        description="Simplicitor template engine CLI.",
    )
    sub = parser.add_subparsers(dest="command", metavar="<command>")

    inspect_p = sub.add_parser("inspect", help="Print the layout/placeholder map of a .pptx file.")
    inspect_p.add_argument("file", help="Path to the .pptx file.")

    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    if args.command == "inspect":
        return _cmd_inspect(args)

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
