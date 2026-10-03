from __future__ import annotations

import argparse
import sys
from contextlib import ExitStack

from . import __version__
from .comparator import compare_directories
from .config import load_config
from .merger import create_merged_folder
from .reporter import write_reports
from .source_adapter import normalized_source


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="golden-pot",
        description="Safely compare and merge folders without changing the sources.",
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
    merge = subparsers.add_parser("merge", help="Create an updated folder safely")
    merge.add_argument("--base", required=True, help="Existing texture/reference folder")
    merge.add_argument("--comparison", required=True, help="New Rainbow/comparison folder")
    merge.add_argument("--output", required=True, help="New merged texture folder")
    merge.add_argument("--reports", required=True, help="Folder for generated reports")
    merge.add_argument("--config", help="Optional JSON configuration file")
    return parser


def run_compare(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    with ExitStack() as stack:
        base = stack.enter_context(normalized_source(args.base))
        comparison = stack.enter_context(normalized_source(args.comparison))
        report = compare_directories(base, comparison, config)
    report.base_folder = str(args.base)
    report.comparison_folder = str(args.comparison)
    json_path, text_path = write_reports(report, args.output)
    summary = report.summary
    print("Golden Pot comparison completed.")
    for key in ("ADDED", "UNCHANGED", "MODIFIED", "PRESERVED", "PROTECTED", "ERROR"):
        print(f"{key}: {summary[key]}")
    print(f"JSON report: {json_path}")
    print(f"Text report: {text_path}")
    return 2 if summary["ERROR"] else 0


def run_merge(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    with ExitStack() as stack:
        base = stack.enter_context(normalized_source(args.base))
        comparison = stack.enter_context(normalized_source(args.comparison))
        report = compare_directories(base, comparison, config)
        result = create_merged_folder(report, args.output)
    report.base_folder = str(args.base)
    report.comparison_folder = str(args.comparison)
    json_path, text_path = write_reports(report, args.reports)
    print(f"Updated folder: {result.output_folder}")
    print(f"Added: {result.added_from_comparison}")
    print(f"Updated: {result.updated_from_comparison}")
    print(f"Preserved from base: {result.copied_from_base}")
    print(f"Merged mappings/registries: {result.merged_json_files}")
    print(f"Mapping/texture warnings: {len(result.warnings)}")
    print(f"Rebuilt pack: {result.rebuilt_pack}")
    print(f"JSON report: {json_path}")
    print(f"Text report: {text_path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        from .gui import main as gui_main

        return gui_main()
    try:
        return run_merge(args) if args.command == "merge" else run_compare(args)
    except (OSError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
