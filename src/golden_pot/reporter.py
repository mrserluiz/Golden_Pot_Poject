from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from .models import ComparisonReport, FileStatus


def report_text(report: ComparisonReport) -> str:
    summary = report.summary
    lines = [
        "GOLDEN POT — FOLDER COMPARISON REPORT",
        "=" * 43,
        f"Generated: {report.generated_at}",
        f"Base folder: {report.base_folder}",
        f"Comparison folder: {report.comparison_folder}",
        f"Hash algorithm: {report.hash_algorithm.upper()}",
        "",
        "SUMMARY",
        "-" * 43,
    ]
    for status in FileStatus:
        lines.append(f"{status.value}: {summary[status.value]}")
    lines.extend([f"TOTAL: {summary['TOTAL']}", ""])

    for status in FileStatus:
        matching = [item for item in report.items if item.status == status]
        if not matching:
            continue
        lines.extend([status.value, "-" * len(status.value)])
        for item in matching:
            details = f" — {item.message}" if item.message else ""
            lines.append(f"{item.relative_path}{details}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write_reports(
    report: ComparisonReport,
    output_folder: str | Path,
    *,
    basename: str | None = None,
) -> tuple[Path, Path]:
    output_path = Path(output_folder).expanduser().resolve()
    output_path.mkdir(parents=True, exist_ok=True)
    name = basename or f"golden-pot-report-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    json_path = output_path / f"{name}.json"
    text_path = output_path / f"{name}.txt"

    with json_path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(report.to_dict(), handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    with text_path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(report_text(report))
    return json_path, text_path
