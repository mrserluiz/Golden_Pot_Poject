from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path


class FileStatus(StrEnum):
    ADDED = "ADDED"
    UNCHANGED = "UNCHANGED"
    MODIFIED = "MODIFIED"
    PRESERVED = "PRESERVED"
    PROTECTED = "PROTECTED"
    ERROR = "ERROR"


@dataclass(frozen=True, slots=True)
class FileSnapshot:
    relative_path: str
    absolute_path: Path
    size: int | None
    digest: str | None
    error: str | None = None


@dataclass(frozen=True, slots=True)
class ComparisonItem:
    relative_path: str
    status: FileStatus
    base_size: int | None = None
    comparison_size: int | None = None
    base_hash: str | None = None
    comparison_hash: str | None = None
    message: str | None = None


@dataclass(slots=True)
class ComparisonReport:
    base_folder: str
    comparison_folder: str
    hash_algorithm: str
    protected_paths: list[str]
    ignored_paths: list[str]
    items: list[ComparisonItem] = field(default_factory=list)
    generated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    @property
    def summary(self) -> dict[str, int]:
        counts = {status.value: 0 for status in FileStatus}
        for item in self.items:
            counts[item.status.value] += 1
        counts["TOTAL"] = len(self.items)
        return counts

    def to_dict(self) -> dict:
        return {
            "golden_pot_version": "0.4.0",
            "generated_at": self.generated_at,
            "base_folder": self.base_folder,
            "comparison_folder": self.comparison_folder,
            "hash_algorithm": self.hash_algorithm,
            "protected_paths": self.protected_paths,
            "ignored_paths": self.ignored_paths,
            "summary": self.summary,
            "items": [
                {**asdict(item), "status": item.status.value} for item in self.items
            ],
        }
