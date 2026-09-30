from __future__ import annotations

from pathlib import Path

from .config import GoldenPotConfig
from .models import ComparisonItem, ComparisonReport, FileStatus
from .scanner import matches_rule, scan_directory


def is_protected(relative_path: str, protected_paths: tuple[str, ...]) -> bool:
    return any(matches_rule(relative_path, rule) for rule in protected_paths)


def compare_directories(
    base_folder: str | Path,
    comparison_folder: str | Path,
    config: GoldenPotConfig | None = None,
) -> ComparisonReport:
    active_config = config or GoldenPotConfig()
    base_root = Path(base_folder).expanduser().resolve()
    comparison_root = Path(comparison_folder).expanduser().resolve()

    if base_root == comparison_root:
        raise ValueError("Base and comparison folders must be different")

    base_files = scan_directory(
        base_root,
        algorithm=active_config.hash_algorithm,
        ignored_paths=active_config.ignored_paths,
    )
    comparison_files = scan_directory(
        comparison_root,
        algorithm=active_config.hash_algorithm,
        ignored_paths=active_config.ignored_paths,
    )

    report = ComparisonReport(
        base_folder=str(base_root),
        comparison_folder=str(comparison_root),
        hash_algorithm=active_config.hash_algorithm,
        protected_paths=list(active_config.protected_paths),
        ignored_paths=list(active_config.ignored_paths),
    )

    for relative_path in sorted(set(base_files) | set(comparison_files), key=str.casefold):
        base = base_files.get(relative_path)
        comparison = comparison_files.get(relative_path)

        if (base and base.error) or (comparison and comparison.error):
            messages = [item.error for item in (base, comparison) if item and item.error]
            status = FileStatus.ERROR
            message = " | ".join(messages)
        elif base is None:
            status = FileStatus.ADDED
            message = None
        elif comparison is None:
            status = FileStatus.PRESERVED
            message = None
        elif base.digest == comparison.digest:
            status = FileStatus.UNCHANGED
            message = None
        elif is_protected(relative_path, active_config.protected_paths):
            status = FileStatus.PROTECTED
            message = "Contents differ, but this path is protected"
        else:
            status = FileStatus.MODIFIED
            message = None

        report.items.append(
            ComparisonItem(
                relative_path=relative_path,
                status=status,
                base_size=base.size if base else None,
                comparison_size=comparison.size if comparison else None,
                base_hash=base.digest if base else None,
                comparison_hash=comparison.digest if comparison else None,
                message=message,
            )
        )

    return report
