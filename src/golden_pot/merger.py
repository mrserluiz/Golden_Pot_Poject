from __future__ import annotations

import os
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .models import ComparisonReport, FileStatus


@dataclass(frozen=True, slots=True)
class MergeResult:
    output_folder: Path
    copied_from_base: int
    added_from_comparison: int
    updated_from_comparison: int
    protected_from_base: int


def _contains(parent: Path, child: Path) -> bool:
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def create_merged_folder(report: ComparisonReport, output_folder: str | Path) -> MergeResult:
    """Create a new pack from the base and safely overlay comparison changes."""
    base_root = Path(report.base_folder).resolve()
    comparison_root = Path(report.comparison_folder).resolve()
    output_root = Path(output_folder).expanduser().resolve()

    for source in (base_root, comparison_root):
        if output_root == source or _contains(source, output_root) or _contains(output_root, source):
            raise ValueError("Output folder must be separate from both source folders")
    if output_root.exists() and (not output_root.is_dir() or any(output_root.iterdir())):
        raise FileExistsError("Output folder already exists and is not empty")

    output_root.parent.mkdir(parents=True, exist_ok=True)
    temporary_root = Path(tempfile.mkdtemp(prefix=f".{output_root.name}-", dir=output_root.parent))
    copied_from_base = added = updated = protected = 0
    try:
        for item in report.items:
            if item.status == FileStatus.ERROR:
                raise OSError(f"Cannot merge file with scan error: {item.relative_path}")
            relative = Path(*item.relative_path.split("/"))
            target = temporary_root / relative
            if item.status in (FileStatus.UNCHANGED, FileStatus.PRESERVED, FileStatus.PROTECTED):
                source = base_root / relative
                if source.is_file():
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, target)
                    copied_from_base += 1
                    protected += item.status == FileStatus.PROTECTED
            elif item.status in (FileStatus.ADDED, FileStatus.MODIFIED):
                source = comparison_root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
                if item.status == FileStatus.ADDED:
                    added += 1
                else:
                    updated += 1
        if output_root.exists():
            output_root.rmdir()
        os.replace(temporary_root, output_root)
    except Exception:
        shutil.rmtree(temporary_root, ignore_errors=True)
        raise
    return MergeResult(output_root, copied_from_base, added, updated, protected)
