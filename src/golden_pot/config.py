from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath


DEFAULT_IGNORED_PATHS = [".git/", "reports/", "output/", "__pycache__/"]
DEFAULT_PROTECTED_PATHS = ["manifest.json", "textures/block/crop/"]


def normalize_rule(value: str) -> str:
    value = value.strip().replace("\\", "/").lstrip("./")
    while "//" in value:
        value = value.replace("//", "/")
    if not value:
        raise ValueError("Path rules cannot be empty")
    if ".." in PurePosixPath(value).parts:
        raise ValueError(f"Path rule cannot escape the selected folder: {value}")
    return value


@dataclass(frozen=True, slots=True)
class GoldenPotConfig:
    hash_algorithm: str = "sha256"
    protected_paths: tuple[str, ...] = field(
        default_factory=lambda: tuple(DEFAULT_PROTECTED_PATHS)
    )
    ignored_paths: tuple[str, ...] = field(
        default_factory=lambda: tuple(DEFAULT_IGNORED_PATHS)
    )

    @classmethod
    def from_dict(cls, data: dict) -> "GoldenPotConfig":
        algorithm = str(data.get("hash_algorithm", "sha256")).lower()
        if algorithm != "sha256":
            raise ValueError("Golden Pot v0.1 currently supports only SHA-256")
        protected = tuple(
            normalize_rule(str(item))
            for item in data.get("protected_paths", DEFAULT_PROTECTED_PATHS)
        )
        ignored = tuple(
            normalize_rule(str(item))
            for item in data.get("ignored_paths", DEFAULT_IGNORED_PATHS)
        )
        return cls(algorithm, protected, ignored)


def load_config(path: str | Path | None = None) -> GoldenPotConfig:
    if path is None:
        return GoldenPotConfig()
    config_path = Path(path).expanduser().resolve()
    with config_path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("Configuration root must be a JSON object")
    return GoldenPotConfig.from_dict(data)
