from __future__ import annotations

import argparse
import sys

from . import __version__
from .comparator import compare_directories
from .config import load_config
from .reporter import write_reports


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="golden-pot",
        description="Safely compare any two folders without changing them.",
    )
    parser.add_argument("--version", action="version", version=__version__)
    subparsers = parser.add_subparsers(dest="command")
    compare = subparsers.add_parser("compare", help="Compare two folders")
    compare.add_argument("--base", required=True, help="Reference/base folder")
    compare.add_argument(
        "--comparison", required=True, help="New folder to compare against the base"
    )
    compare.add_argument("--output", required=True, help="Folder for generated reports")
    compare.add_argument("--config", help="Optional JSON configuration file")
    return parser


def run_compare(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    report = compare_directories(args.base, args.comparison, config)
    json_path, text_path = write_reports(report, args.output)
    summary = report.summary
    print("Golden Pot comparison completed.")
    for key in ("ADDED", "UNCHANGED", "MODIFIED", "PRESERVED", "PROTECTED", "ERROR"):
        print(f"{key}: {summary[key]}")
    print(f"JSON report: {json_path}")
    print(f"Text report: {text_path}")
    return 2 if summary["ERROR"] else 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        from .gui import main as gui_main

        return gui_main()
    try:
        return run_compare(args)
    except (OSError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
